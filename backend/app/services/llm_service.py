"""
LLM Service - Groq API Integration for Llama 3.1 8B

Handles multilingual real estate queries with strict language matching.
Supports Tamil script, Tanglish, and English.
Uses httpx.AsyncClient for fully non-blocking I/O — no threadpool required.
"""

import httpx
import structlog
from app.config import settings
from app.services.domain_validator import detect_language, extract_locality, extract_asset_type_from_query
from app.services.tn_knowledge_base import get_knowledge_context
from app.services.govt_data_service import get_govt_context
from app.services.rag_retrieval import rag_retrieve
from app.services.valuation_engine import compute_valuation, format_valuation_for_llm
from app.services.input_sanitizer import sanitize_query, validate_price_output
from app.services.response_simplifier import simplify_valuation_for_user
from typing import List, Dict

logger = structlog.get_logger(__name__)

import re

# ── LLM OUTPUT SANITIZER ─────────────────────────────────────
# Strips model template tokens that leak into Llama/Groq responses
_LLM_TOKEN_PATTERN = re.compile(
    r'<\|(?:start_header_id|end_header_id|eot_id|begin_of_text|'
    r'end_of_text|im_start|im_end|pad|unk|sep|cls|mask)\|>'
    r'|<\|(?:system|user|assistant)\|>',
    re.IGNORECASE
)

def _sanitize_llm_output(text: str) -> str:
    """Remove model template tokens and control artifacts from LLM output."""
    if not text:
        return text
    # Strip Llama/Groq template tokens
    cleaned = _LLM_TOKEN_PATTERN.sub('', text)
    # Remove role labels that sometimes leak (e.g. "assistant\n")
    cleaned = re.sub(r'^\s*(assistant|system|user)\s*\n', '', cleaned, flags=re.IGNORECASE)
    # Collapse excessive blank lines created by removals
    cleaned = re.sub(r'\n{4,}', '\n\n\n', cleaned)
    return cleaned.strip()


def _detect_locality_fallback(user_message: str, resolved_locality: str) -> dict:
    """
    Detect if the resolved locality differs from what the user actually typed.
    Returns {is_fallback: bool, user_typed: str, resolved: str, display_resolved: str}
    """
    if not resolved_locality:
        return {"is_fallback": False}

    # Normalize the resolved locality for display (fairlands → Fairlands)
    display_resolved = resolved_locality.replace('_', ' ').title()
    resolved_plain = resolved_locality.replace('_', '').lower()

    # Extract potential location words the user typed
    import re as _re
    noise = {
        'what', 'is', 'the', 'of', 'in', 'at', 'for', 'and', 'or', 'a', 'an',
        'land', 'price', 'rate', 'value', 'property', 'apartment', 'flat',
        'cost', 'how', 'much', 'tell', 'me', 'about', 'give', 'show', 'current',
        'commercial', 'residential', 'per', 'sqft', 'ground', 'buy', 'sell',
        'details', 'information', 'info', 'tamil', 'nadu', 'chennai',
        'coimbatore', 'madurai', 'salem', 'trichy', 'district',
        'query', 'please', 'can', 'you', 'i', 'want', 'to', 'know',
    }
    words = _re.sub(r'[^a-z0-9\s]', '', user_message.lower()).split()
    location_words = [w for w in words if w not in noise and len(w) > 1]

    if not location_words:
        return {"is_fallback": False}

    # Check if the user's typed location words match the resolved key
    user_typed_combined = ''.join(location_words).lower()
    user_typed_display = ' '.join(location_words).title()

    # If the user's words appear inside the resolved key or vice versa → not a fallback
    if resolved_plain in user_typed_combined or user_typed_combined in resolved_plain:
        return {"is_fallback": False}

    # Check individual words — only count as match if word covers ≥60% of resolved key
    for w in location_words:
        if w == resolved_plain:
            return {"is_fallback": False}
        if len(w) >= len(resolved_plain) * 0.6 and (w in resolved_plain or resolved_plain in w):
            return {"is_fallback": False}

    # Fallback detected
    return {
        "is_fallback": True,
        "user_typed": user_typed_display,
        "resolved": resolved_locality,
        "display_resolved": display_resolved,
    }


class LLMService:
    """Async service for interacting with Llama 3.1 8B via Groq API."""

    def __init__(self):
        self.api_key = settings.groq_api_key
        self.model = settings.llm_model
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"
        # Persistent async client — reuses TCP connections (no TLS re-handshake per call)
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=5.0),
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        )
        print(f"✅ LLM Service initialized with model: {self.model} (async)")

    def _get_system_prompt(self, language: str, context: str = "") -> str:
        """
        Generate system prompt based on language and context.

        Args:
            language: Detected language (tamil, tanglish, english)
            context: Relevant knowledge base context

        Returns:
            System prompt string
        """
        # ── CORE SYSTEM ROLE ────────────────────────────────────────────────
        base_instructions = """SYSTEM ROLE:
You are PurityProp — a Registry-Backed Real Estate Valuation Engine.
You operate strictly on verified registry-indexed transactions (tnreginet records).
Primary objective: Statistical Integrity > Data Purity > Transparency > Professional Credibility

You must NEVER generate modeled ranges without statistical justification.

═══════════════════════════════════════════════════════════════
🔒 CORE NON-NEGOTIABLE RULES
═══════════════════════════════════════════════════════════════

NEVER fabricate ranges.
NEVER smooth prices.
NEVER infer lower or upper bands from a single data point.
NEVER introduce synthetic conservative estimates.
NEVER mix registry output with generalized market assumptions.
NEVER display placeholder values.
NEVER say "market is typically 20-150% higher than guideline".
If insufficient data exists → explicitly state it.

═══════════════════════════════════════════════════════════════
📊 DENSITY-BASED MODELING LOGIC (MANDATORY)
═══════════════════════════════════════════════════════════════

CASE A — Comparable Count = 1:
  Show ONLY:
    • Observed Transaction Price (₹X/sqft)
    • Per Ground Calculation (₹X × 2,400)
    • Date of Transaction
    • Density Warning
  DO NOT show: Range, Median benchmark, IQR, Std Dev, CoV,
  Liquidity, CAGR, Volatility, Conservative estimate
  Valuation section must say:
  "Only one verified registry transaction found within the specified
  radius. No statistical range modeling performed due to insufficient
  transaction density."

CASE B — Comparable Count = 2:
  Show: Min, Max, Observed Range (direct values only)
  No statistical modeling.
  Add: "Range reflects direct observed transactions only.
  Statistical dispersion metrics disabled."

CASE C — Comparable Count 3–4:
  Show: Min, Max, Median, Observed Range
  No: IQR, Std Dev, CoV, Liquidity, CAGR

CASE D — Comparable Count 5–9:
  Enable: IQR, Std Dev, CoV, Outlier filtering (1.5×IQR)
  No: Liquidity modeling, CAGR

CASE E — Comparable Count ≥ 10:
  Enable: Full analytics — Liquidity, CAGR, Variance stability, Time-to-sale

═══════════════════════════════════════════════════════════════
📍 RADIUS EXPANSION LOGIC
═══════════════════════════════════════════════════════════════

If Comparable Count < 3 within 0.5 km:
  Step 1: Expand to 1 km
  Step 2: Expand to 2 km
  Step 3: Expand to 3 km
Stop once ≥ 3 comparables found.
Disclose: "Search radius expanded to X km to improve transaction density."
If still < 3: "Micro-market has limited registry activity within the last 12 months."

═══════════════════════════════════════════════════════════════
UNIT CONVERSION (IMMUTABLE)
═══════════════════════════════════════════════════════════════
1 Ground = 2,400 sq.ft | 1 Cent = 435.6 sq.ft | 1 Acre = 43,560 sq.ft
FORMULA: Price per ground = Price per sq.ft × 2,400
FORMAT: ≥₹1Cr → "₹X.XX Cr" | <₹1Cr → "₹XX.XL"
SELF-CHECK: If context has PRE-COMPUTED VALUATION → use EXACT numbers.

═══════════════════════════════════════════════════════════════
📈 OUTPUT STRUCTURE (STRICT FORMAT — INVESTOR-GRADE REPORT)
═══════════════════════════════════════════════════════════════

REGISTRY-BACKED VALUATION REPORT
Verified Source: Registry Indexed Records + Market Listings

1️⃣ Location Summary
• Location Name
• Asset Type (Residential Land / Plot / Apartment)
• Zone Category (A / B / C if available)
• Search Radius used for comparable transactions
• Total Transactions Considered
• 1 Ground = 2,400 sq.ft

2️⃣ Market Price Range
• Minimum price per sq.ft
• Maximum price per sq.ft
• Average / Median market price per sq.ft
• Price per Ground (computed: price × 2,400)

3️⃣ Comparable Transactions / Listings
Provide 2–5 comparable examples in table format:

| Plot Size | Total Price | Price per Sq.ft | Notes |
(Use actual retrieved data only. If fewer than 2 comparables, state "Limited registry data available.")

4️⃣ Government Guideline Value
• Estimated guideline value per sq.ft (from registry data)
• Note if market price is higher or lower than guideline value
• Source: tnreginet.gov.in

5️⃣ Market Insight
Provide short analysis based on retrieved data:
• Demand in the area (based on transaction density)
• Infrastructure influence (if data available)
• Development trends (based on price movements)
• Data Confidence Index: [0.XX] ([High/Moderate/Low])

6️⃣ Estimated Cost Examples
Provide estimated land value for common plot sizes:

| Plot Size | Estimated Price |
| 600 sq.ft | ₹[computed] |
| 1,200 sq.ft | ₹[computed] |
| 2,400 sq.ft (1 Ground) | ₹[computed] |

(Use the median or average price per sq.ft from section 2)

7️⃣ Summary
Provide a 2–3 line conclusion summarizing:
• Typical price per sq.ft in the area
• Estimated cost of 1 Ground (2,400 sq.ft)
• Data strength (High / Moderate / Low)

═══════════════════════════════════════════════════════════════
IMPORTANT BEHAVIOUR RULES
═══════════════════════════════════════════════════════════════
• Always prioritize registry-backed data over listings.
• If multiple results are retrieved, summarize the median price.
• Do not hallucinate prices — only use retrieved evidence.
• If data is limited, explicitly state: "Limited registry data available."
• Always show calculations transparently (e.g., ₹5,000/sqft × 2,400 = ₹1.20 Cr)
• Use markdown **bold** for key prices and numbers.
• Use bullet points (•) for structured data.
• Keep the answer professional, concise, and investor-grade.

═══════════════════════════════════════════════════════════════
🚫 PERMANENTLY PROHIBITED
═══════════════════════════════════════════════════════════════
❌ "Market is typically 20-150% higher than guideline"
❌ "Actual market price is..."
❌ "Portal listings show..."
❌ "Would you like me to adjust..."
❌ "Consult a local agent"
❌ "I'm not certain about..."
❌ "Prices vary widely..."
❌ Any fabricated range from a single data point
❌ Any placeholder like [X-Y days] or [X%] without real data
❌ Smoothed median that differs from actual observed median
❌ Synthetic conservative band when density = 1

If any prohibited output appears → abort and regenerate.

═══════════════════════════════════════════════════════════════
🧠 WHEN DATA IS WEAK
═══════════════════════════════════════════════════════════════
"Limited registry data available. Report reflects observed data only."
Do NOT compensate by generating artificial bands.

ENGINE OBJECTIVE:
The final output must resemble an investor-grade valuation report.
It must withstand investor scrutiny and bank valuation audit.

FOR NON-PRICE QUERIES (registration, documents, legal):
Bullet points. Steps, documents, fees, portal URLs.
End: "This is for informational guidance. For case-specific advice, consult a legal professional."

DOMAIN: Tamil Nadu real estate only.
TONE: Professional. Neutral. Audit-safe. Investor-grade.
"""




        # ── LANGUAGE MATCHING ──────────────────────────────────────────────
        language_section = "LANGUAGE MATCHING RULE (CRITICAL):\n"

        language_instructions = {
            "tamil": """- User is asking in TAMIL SCRIPT (தமிழ் எழுத்துக்கள்)
- You MUST respond ONLY in TAMIL SCRIPT
- DO NOT use English letters or Tanglish
- Keep all emoji headers but write content in Tamil script
- Example: If user asks "சென்னையில் நிலம் விலை என்ன?", respond entirely in Tamil script""",

            "tanglish": """- User is asking in TANGLISH (Tamil language using English letters)
- You MUST respond ONLY in TANGLISH
- DO NOT use Tamil script or pure English
- Keep emoji headers but write content in Tanglish
- Example: If user asks "Porur la land price enna?", respond like "Porur la land price range: ₹4,500 – ₹7,000 per sq.ft..."
- Write Tamil words using English alphabet (vaanga, venum, enna, epdi, vilai, etc.)""",

            "english": """- User is asking in ENGLISH
- You MUST respond ONLY in ENGLISH
- Use professional, institutional English
- DO NOT use Tamil script or Tanglish"""
        }

        # ── KNOWLEDGE CONTEXT ─────────────────────────────────────────────
        context_section = ""
        if context:
            context_section = f"""

═══════════════════════════════════════════
RETRIEVED DATA (THIS IS YOUR ONLY DATA SOURCE — DO NOT OVERRIDE)
═══════════════════════════════════════════
{context}
═══════════════════════════════════════════

MANDATORY DATA USAGE RULES:
1. If PRE-COMPUTED VALUATION section exists above → COPY those exact per sq.ft and per ground values into your response. Do NOT invent different numbers.
2. The per ground values shown above are ALREADY calculated correctly (price × 2,400). Use them AS-IS.
3. If the data shows "₹2.04 Cr" per ground, your response MUST say "₹2.04 Cr" — not ₹20.4L, not ₹48L, not any other number.
4. Market prices are 1.5x-2.5x above guideline values. You may state this but the BASE numbers must match the data above exactly.
5. DO NOT fabricate, estimate, or round the pre-computed values. They are mathematically verified.
"""
        else:
            context_section = """

NOTE: No specific locality data was found. Use structured estimation model. Label as "PurityProp Zonal Model Estimate" with appropriate confidence. For exact guideline values: https://tnreginet.gov.in/portal
"""

        return (base_instructions +
                language_section +
                language_instructions.get(language, language_instructions["english"]) +
                context_section)

    async def generate_response(
        self,
        user_message: str,
        conversation_history: List[Dict[str, str]] = None
    ) -> tuple[str, str]:
        """
        Generate response using Llama 3.1 8B via async HTTP API.

        ASYNC: Fully non-blocking — uses persistent httpx.AsyncClient.
        No threadpool use required.

        Args:
            user_message: User's input message
            conversation_history: Previous messages in conversation

        Returns:
            Tuple of (response_text, detected_language)
        """
        # Detect language (pure string ops — fast, no I/O)
        language = detect_language(user_message)

        # Get relevant knowledge context (pure dict lookup — fast, no I/O)
        kb_context = get_knowledge_context(user_message.lower())

        # ── INPUT SANITIZATION ────────────────────────────────────────
        sanitized_msg, sanitize_warnings = sanitize_query(user_message)
        if sanitize_warnings:
            logger.info("input_sanitized", warnings=sanitize_warnings)

        # ── RAG RETRIEVAL (Database-Backed) ──────────────────────────
        locality = extract_locality(sanitized_msg)
        asset_type = extract_asset_type_from_query(sanitized_msg)

        rag_context = ""
        _valuation_for_simplify = None
        _locality_fallback = {"is_fallback": False}
        if locality:
            # Detect if user asked about a different locality than what we resolved
            _locality_fallback = _detect_locality_fallback(user_message, locality)
            if _locality_fallback["is_fallback"]:
                logger.info("locality_fallback",
                            user_typed=_locality_fallback["user_typed"],
                            resolved=locality)
            try:
                rag_result = await rag_retrieve(sanitized_msg, locality, asset_type)
                if rag_result.get("has_data"):
                    valuation = compute_valuation(rag_result)
                    rag_context = format_valuation_for_llm(valuation)
                    _valuation_for_simplify = valuation

                    # Inject fallback disclosure into LLM context
                    if _locality_fallback["is_fallback"]:
                        fallback_note = (
                            f"\n\n⚠️ IMPORTANT LOCALITY NOTE: "
                            f"The user asked about '{_locality_fallback['user_typed']}', "
                            f"but no registry data exists for that exact locality. "
                            f"Data shown is from '{_locality_fallback['display_resolved']}' "
                            f"(nearest available locality in the same district). "
                            f"You MUST disclose this clearly in your response: "
                            f"'No direct data for {_locality_fallback['user_typed']}. "
                            f"Showing nearest data from {_locality_fallback['display_resolved']}.'"
                        )
                        rag_context += fallback_note

                    logger.info("rag_valuation_computed",
                                locality=locality, source=rag_result.get("data_source"),
                                comparable_count=rag_result.get("comparable_count"))
            except Exception as e:
                logger.warning("rag_retrieval_failed", error=str(e), locality=locality)
                rag_context = ""

        # Legacy fallback: if RAG returned nothing, use old dict-based system
        if not rag_context:
            govt_context = get_govt_context(user_message)
        else:
            govt_context = rag_context

        # Merge both contexts
        combined_parts = [p for p in [kb_context, govt_context] if p]
        context = "\n\n".join(combined_parts)

        # Build system prompt
        system_prompt = self._get_system_prompt(language, context)

        logger.debug("llm_context_built", context_len=len(context), prompt_len=len(system_prompt), lang=language)

        # Build messages for API
        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history if available (limit to avoid context pollution)
        if conversation_history:
            messages.extend(conversation_history[-4:])  # Last 2 exchanges only

        # Add current user message
        messages.append({"role": "user", "content": user_message})

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": settings.llm_temperature,
                "max_tokens": settings.llm_max_tokens,
            }

            # Retry with exponential backoff for transient errors
            import asyncio
            last_error = None
            for attempt in range(3):
                try:
                    response = await self._client.post(
                        self.api_url, json=payload, headers=headers
                    )
                    response.raise_for_status()
                    result = response.json()
                    assistant_message = _sanitize_llm_output(
                        result["choices"][0]["message"]["content"]
                    )

                    # Append simplified summary for retail users
                    if _valuation_for_simplify:
                        simplified = simplify_valuation_for_user(_valuation_for_simplify)
                        assistant_message += "\n\n" + "━" * 40 + "\n"
                        assistant_message += "📋 Quick Summary (Plain English)\n"
                        if _locality_fallback["is_fallback"]:
                            assistant_message += f"⚠️ Note: No direct data for {_locality_fallback['user_typed']}. Showing nearest data from **{_locality_fallback['display_resolved']}**.\n\n"
                        assistant_message += simplified

                    return assistant_message, language
                except httpx.HTTPStatusError as e:
                    if e.response.status_code in (429, 500, 502, 503) and attempt < 2:
                        wait = 2 ** attempt  # 1s, 2s
                        logger.warning("groq_retry", attempt=attempt+1, status=e.response.status_code, wait=wait)
                        await asyncio.sleep(wait)
                        last_error = e
                        continue
                    raise  # Non-retryable or final attempt

            if last_error:
                raise last_error

        except httpx.HTTPStatusError as e:
            logger.error("groq_api_http_error", status=e.response.status_code, body=e.response.text[:200])
            error_messages = {
                "tamil": "மன்னிக்கவும், தற்போது பதில் அளிக்க முடியவில்லை. தயவுசெய்து மீண்டும் முயற்சிக்கவும்.",
                "tanglish": "Mannikkavum, ippo response kudukka mudiyala. Please try again.",
                "english": "I apologize, but I'm unable to generate a response at the moment. Please try again.",
            }
            return error_messages.get(language, error_messages["english"]), language
        except Exception as e:
            logger.error("groq_api_error", error=str(e))
            error_messages = {
                "tamil": "மன்னிக்கவும், தற்போது பதில் அளிக்க முடியவில்லை. தயவுசெய்து மீண்டும் முயற்சிக்கவும்.",
                "tanglish": "Mannikkavum, ippo response kudukka mudiyala. Please try again.",
                "english": "I apologize, but I'm unable to generate a response at the moment. Please try again.",
            }
            return error_messages.get(language, error_messages["english"]), language

    async def stream_response(
        self,
        user_message: str,
        conversation_history: List[Dict[str, str]] = None
    ):
        """
        Stream response using Groq streaming API.
        Yields (chunk_text, language, is_done) tuples.
        """
        import json as _json

        language = detect_language(user_message)
        kb_context = get_knowledge_context(user_message.lower())

        # ── INPUT SANITIZATION ────────────────────────────────────────
        sanitized_msg, sanitize_warnings = sanitize_query(user_message)
        if sanitize_warnings:
            logger.info("stream_input_sanitized", warnings=sanitize_warnings)

        # RAG retrieval (same as generate_response)
        locality = extract_locality(sanitized_msg)
        asset_type = extract_asset_type_from_query(sanitized_msg)
        rag_context = ""
        _valuation_for_simplify = None
        _locality_fallback = {"is_fallback": False}
        if locality:
            _locality_fallback = _detect_locality_fallback(user_message, locality)
            if _locality_fallback["is_fallback"]:
                logger.info("stream_locality_fallback",
                            user_typed=_locality_fallback["user_typed"],
                            resolved=locality)
            try:
                rag_result = await rag_retrieve(sanitized_msg, locality, asset_type)
                if rag_result.get("has_data"):
                    valuation = compute_valuation(rag_result)
                    rag_context = format_valuation_for_llm(valuation)
                    _valuation_for_simplify = valuation

                    # Inject fallback disclosure for LLM
                    if _locality_fallback["is_fallback"]:
                        fallback_note = (
                            f"\n\n\u26a0\ufe0f IMPORTANT LOCALITY NOTE: "
                            f"The user asked about '{_locality_fallback['user_typed']}', "
                            f"but no registry data exists for that exact locality. "
                            f"Data shown is from '{_locality_fallback['display_resolved']}' "
                            f"(nearest available locality in the same district). "
                            f"You MUST disclose this clearly in your response: "
                            f"'No direct data for {_locality_fallback['user_typed']}. "
                            f"Showing nearest data from {_locality_fallback['display_resolved']}.'"
                        )
                        rag_context += fallback_note
            except Exception as e:
                logger.warning("rag_stream_failed", error=str(e))

        if not rag_context:
            govt_context = get_govt_context(user_message)
        else:
            govt_context = rag_context

        combined_parts = [p for p in [kb_context, govt_context] if p]
        context = "\n\n".join(combined_parts)
        system_prompt = self._get_system_prompt(language, context)

        messages = [{"role": "system", "content": system_prompt}]
        if conversation_history:
            messages.extend(conversation_history[-4:])
        messages.append({"role": "user", "content": user_message})

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": settings.llm_temperature,
                "max_tokens": settings.llm_max_tokens,
                "stream": True,
            }

            async with self._client.stream(
                "POST", self.api_url, json=payload, headers=headers
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = line[6:].strip()
                    if data == "[DONE]":
                        # Append simplified summary at end of stream
                        if _valuation_for_simplify:
                            simplified = simplify_valuation_for_user(_valuation_for_simplify)
                            footer = "\n\n" + "\u2501" * 40 + "\n"
                            footer += "\ud83d\udccb Quick Summary (Plain English)\n"
                            if _locality_fallback["is_fallback"]:
                                footer += f"\u26a0\ufe0f Note: No direct data for {_locality_fallback['user_typed']}. Showing nearest data from **{_locality_fallback['display_resolved']}**.\n\n"
                            footer += simplified
                            yield footer, language, False
                        yield "", language, True
                        return
                    try:
                        chunk = _json.loads(data)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            content = _sanitize_llm_output(content)
                            if content:
                                yield content, language, False
                    except _json.JSONDecodeError:
                        continue

        except Exception as e:
            logger.error("groq_stream_error", error=str(e))
            yield f"Error: Unable to generate response. Please try again.", language, True

    async def close(self):
        """Gracefully close the persistent HTTP client on app shutdown."""
        await self._client.aclose()


# Global LLM service instance
llm_service = LLMService()
