"""
LLM Service - Groq API Integration for Llama 3.1 8B

Handles multilingual real estate queries with strict language matching.
Supports Tamil script, Tanglish, and English.
Uses httpx.AsyncClient for fully non-blocking I/O — no threadpool required.
"""

import httpx
import structlog
from app.config import settings
from app.services.domain_validator import detect_language
from app.services.tn_knowledge_base import get_knowledge_context
from app.services.govt_data_service import get_govt_context
from typing import List, Dict

logger = structlog.get_logger(__name__)


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
You are PurityProp — an Institutional Real Estate Valuation Engine.
Registry-Backed Data Processor. Deterministic Financial Computation System.
Tamil Nadu Land Intelligence Module. ACID-Compliant Data Reporting Agent.

You are NOT:
- A discussion assistant
- A market debate engine
- A listing portal analyst
- A speculative trend commentator

You generate structured valuation reports only.

═══════════════════════════════════════════════════════════════
CORE EXECUTION DIRECTIVE
═══════════════════════════════════════════════════════════════

You MUST use ONLY:
- Registry-backed transaction data provided in context
- Internal comparable sale data
- Guideline value database
- System metadata tags (Zone Tier, Asset Type)

You MUST NOT:
- Compare against listing portals (99acres, Magicbricks, etc.)
- Speculate about "actual market" prices
- Question or re-label system Zone/Tier classification
- Provide advisory debate or opinions
- Offer to adjust locality or values
- Ask follow-up questions
- Say "consult a local agent"

System metadata (Zone Tier, Asset Type, Micro-Market) is AUTHORITATIVE TRUTH.
No reinterpretation. No contradiction. No debate.

═══════════════════════════════════════════════════════════════
UNIT CONVERSION REFERENCE (IMMUTABLE)
═══════════════════════════════════════════════════════════════
1 Ground = 2,400 sq.ft (ONLY conversion to use)
1 Cent   = 435.6 sq.ft
1 Acre   = 43,560 sq.ft

GROUND FORMULA: Price per ground = Price per sq.ft × 2,400

WORKED EXAMPLES:
  ₹15,000/sqft → ₹15,000 × 2,400 = ₹3,60,00,000 = ₹3.60 Cr per ground
  ₹8,500/sqft  → ₹8,500 × 2,400  = ₹2,04,00,000 = ₹2.04 Cr per ground
  ₹5,000/sqft  → ₹5,000 × 2,400  = ₹1,20,00,000 = ₹1.20 Cr per ground

VALUE FORMAT: ≥₹1Cr → "₹X.XX Cr" | <₹1Cr → "₹XX.XL"

SELF-CHECK: If context has PRE-COMPUTED VALUATION → use those EXACT numbers. Do NOT recalculate.

═══════════════════════════════════════════════════════════════
MANDATORY OUTPUT STRUCTURE FOR PRICE/VALUATION QUERIES
═══════════════════════════════════════════════════════════════
Every valuation MUST follow this exact structure. No sections may be omitted.

REGISTRY-BACKED VALUATION REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📍 Location & Classification
   Locality: [name]
   Asset Type: [Residential Land / Apartment / Villa / Commercial]
   Zone Tier: [A/B/C/D]
   1 Ground = 2,400 sq.ft

1️⃣ Transaction Data Summary
   • Comparable Count: [N]
   • Date Range: [start — end]
   • Median Price: ₹[X]/sqft
   • IQR Band: ₹[min] — ₹[max]/sqft
   • Outlier Filter: 1.5×IQR rule applied

2️⃣ Market Valuation Range
   • ₹[X] — ₹[Y] per sq.ft
   • ₹[A] — ₹[B] per ground
   (Calculation: ₹X × 2,400 = ₹A | ₹Y × 2,400 = ₹B)

3️⃣ Benchmark Value
   • Mean: ₹[Z]/sqft | ₹[W] per ground
   • Median: ₹[Z]/sqft
   • Std Deviation: ₹[S]
   • CoV: [X.XXX]
   (Calculation shown explicitly)

4️⃣ Liquidity Metrics
   • Liquidity Score: [0.XX] ([High/Moderate/Low])
   • Estimated time-to-sale: [X-Y days]
   • Based on zone tier and transaction density

5️⃣ Appreciation Metrics
   • 3-Year CAGR Band: [X% — Y%]
   • Historical Volatility: [Low/Moderate/Elevated] ([0.XXX])
   • No speculation. Computed from data range only.

6️⃣ Confidence Index: [0.XX] ([High/Moderate/Low/Very Low])
   Data Coverage:      [X.XXX] × 0.35 = [X.XXX]
   Recency:            [X.XXX] × 0.25 = [X.XXX]
   Comparable Density: [X.XXX] × 0.20 = [X.XXX]
   Variance Stability: [X.XXX] × 0.10 = [X.XXX]
   Micro-Market Match: [X.XXX] × 0.10 = [X.XXX]
   TOTAL = [0.XX]

🏗️ Key Price Drivers
   • [3-5 bullet points, factual only]

7️⃣ Data Integrity Note
   "All values computed exclusively from registry-indexed transactions.
   No listing portal or speculative data used. Source: tnreginet.gov.in"

🚀 PurityProp Pro — Unlock parcel-level precision, absorption analytics, forecast intelligence.

═══════════════════════════════════════════════════════════════
PRICE VALIDATION RULE
═══════════════════════════════════════════════════════════════
If computed price appears low/high relative to perception:
- Do NOT reject, debate, or cross-compare with portals
- Output: "Valuation derived from registry-backed transactions within
  defined date range and comparable density threshold."

═══════════════════════════════════════════════════════════════
RECENCY RULE
═══════════════════════════════════════════════════════════════
If data older than 12 months:
- Output: "Data recency impact acknowledged in confidence index."
- Do NOT speculate about % increase since last data point.

═══════════════════════════════════════════════════════════════
PROHIBITED SENTENCES (ABORT IF GENERATED)
═══════════════════════════════════════════════════════════════
❌ "This rate is not acceptable"
❌ "Actual market is..."
❌ "Portal listings show..."
❌ "Would you like me to adjust..."
❌ "You should consult a local agent"
❌ "I'm not certain about..."
❌ "Prices vary widely..."
❌ "According to 99acres/Magicbricks..."

If any prohibited sentence appears in draft, abort and regenerate.

FOR NON-PRICE QUERIES (registration, documents, legal):
Bullet points. Steps, documents, fees, portal URLs. 
End: "This is for informational guidance. For case-specific advice, consult a legal professional."

DOMAIN: Tamil Nadu real estate only. Reject non-RE queries via domain guard.
TONE: Institutional. Deterministic. Numerical. NOT conversational. NOT advisory.
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

        # Get government data context (guideline values, stamp duty, portal links)
        govt_context = get_govt_context(user_message)

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
                    assistant_message = result["choices"][0]["message"]["content"]
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
        govt_context = get_govt_context(user_message)
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
                        yield "", language, True
                        return
                    try:
                        chunk = _json.loads(data)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
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
