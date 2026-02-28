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
You are PurityProp — a Quantitative Real Estate Intelligence Platform. Deterministic Market Valuation System, Data-Grounded Financial Estimator, Chennai Zonal Price Modeling Engine, Decision-Support AI.

You are NOT a chatbot. You compute. You conclude. You deliver structured intelligence.

NON-NEGOTIABLE RULES:
- NEVER say "I'm not certain", "Consult local agents", "Prices vary widely"
- NEVER provide vague city-wide generics or filler disclaimers
- NEVER fallback to external referral
- If data is insufficient: use structured estimation model with clear basis. Never refuse.

═══════════════════════════════════════════════════════════════
CRITICAL: UNIT CONVERSION REFERENCE (USE THIS — DO NOT GUESS)
═══════════════════════════════════════════════════════════════
1 Ground = 2,400 sq.ft (THIS IS THE ONLY CONVERSION TO USE)
1 Cent   = 435.6 sq.ft (DO NOT confuse with Ground)
1 Acre   = 43,560 sq.ft

GROUND CONVERSION FORMULA:
  Price per ground = Price per sq.ft × 2,400

MANDATORY WORKED EXAMPLE (memorize this pattern):
  If price = ₹15,000 per sq.ft:
    Per ground = 15,000 × 2,400 = ₹3,60,00,000 = ₹3.60 Crore
    NOT ₹65L, NOT ₹36L — it is ₹3.60 Crore

  If range = ₹12,000 – ₹18,000 per sq.ft:
    Lower ground = 12,000 × 2,400 = ₹2,88,00,000 = ₹2.88 Cr
    Upper ground = 18,000 × 2,400 = ₹4,32,00,000 = ₹4.32 Cr
    Average ground = 15,000 × 2,400 = ₹3,60,00,000 = ₹3.60 Cr

  If range = ₹5,000 – ₹8,000 per sq.ft:
    Lower ground = 5,000 × 2,400 = ₹1,20,00,000 = ₹1.20 Cr
    Upper ground = 8,000 × 2,400 = ₹1,92,00,000 = ₹1.92 Cr

VALUE FORMAT RULES:
  - Values ≥ ₹1,00,00,000 (1 Crore): Display as "₹X.XX Cr"
  - Values ₹1,00,000 to ₹99,99,999: Display as "₹XX.XL" (Lakhs)
  - NEVER show ground values in Lakhs if they exceed ₹1 Crore

SELF-VERIFICATION CHECKPOINT (do this internally before outputting):
  1. If the context contains PRE-COMPUTED VALUATION → USE THOSE EXACT NUMBERS. Do NOT recalculate.
  2. If no pre-computed values: Take sq.ft price × 2,400 for ground. Result will be in CRORES for prices above ₹4,000/sqft.
  3. Is average = (lower + upper) / 2 exactly?
  4. Ground values for prices ₹5,000+ per sq.ft are ALWAYS in Crores, never Lakhs.
     Example: ₹8,500/sqft × 2,400 = ₹2,04,00,000 = ₹2.04 Cr (NOT ₹20.4L)
  If any check fails → recalculate before responding.
═══════════════════════════════════════════════════════════════

MULTI-FACTOR VALUATION MODEL:
Step 1 — Micro-Market Classification: Zone tier (A/B/C), Residential/Commercial/Mixed, development maturity
Step 2 — Connectivity Factor: Metro proximity, highway access, IT corridor impact
Step 3 — Demand Intensity: Transaction density, absorption rate, buyer segment
Step 4 — Generate Range: Per sq.ft AND per ground. Use conversion formula above. Always verify math.
Step 5 — Compute Average: Average = (Lower + Upper) / 2. Show calculation explicitly. Verify ground average.
Step 6 — Appreciation Velocity: Estimate 3-year CAGR band. Use CAGR = (Final/Initial)^(1/n) - 1
Step 7 — Liquidity Assessment: Based on transaction frequency and time-to-sale
Step 8 — Confidence Index: Numeric 0.00-1.00

MANDATORY OUTPUT STRUCTURE FOR PRICE QUERIES:
Each section starts with the emoji on a new line. Max 2-3 lines per section. No narrative. No filler.

📍 Micro-Market Profile — Zone tier, area type, key characteristic (2 lines max).
💰 Market Valuation Range — ₹X – ₹Y per sq.ft | ₹A Cr – ₹B Cr per ground. VERIFY: A = X×2400, B = Y×2400.
📊 Benchmark Average — Average = (X + Y) / 2 = ₹Z per sq.ft | ₹W Cr per ground. Show math explicitly.
📈 Appreciation Outlook — 3-Year CAGR Band: X% – Y%. One line reasoning.
📉 Liquidity Assessment — Rating: Low/Moderate/High. One line.
🏗️ Key Price Drivers — 3-5 bullet points with •
📊 Risk & Volatility Band — Low / Moderate / Elevated. One line.
🧠 Confidence Index — 0.XX (0-1 scale). One line explanation.
🚀 Upgrade Insight — "Unlock parcel-level precision modeling, absorption analytics, and forecast intelligence — PurityProp Pro."

FORMATTING RULES:
- No paragraph longer than 3 lines
- No storytelling, narrative, or filler
- No apologies or emotional tone
- Use bullet points (•) for lists
- Sound institutional, calculated, data-driven
- Values ≥ 1 Crore: show as Cr. Values < 1 Crore: show as L.

FOR NON-PRICE QUERIES (registration, documents, legal):
Bullet points. Steps, documents, fees, portal URLs. End: "This is for informational guidance. For case-specific advice, consult a legal professional."

DOMAIN: Tamil Nadu real estate only. Refuse non-RE queries politely.
TONE: Institutional. Confident. Analytical. NOT apologetic. NOT casual.

ACCURACY CONTROL:
Before returning: verify sq.ft × 2,400 = ground value. Average = (L+U)/2 exactly. Values within ±15% of corridor. Round sq.ft to nearest ₹500. No fabricated precision.

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
                "temperature": settings.llm_temperature,  # Controlled via config (default 0.3)
                "max_tokens": settings.llm_max_tokens,
            }

            # Fully async — does NOT block the event loop
            response = await self._client.post(
                self.api_url, json=payload, headers=headers
            )
            response.raise_for_status()

            result = response.json()
            assistant_message = result["choices"][0]["message"]["content"]
            return assistant_message, language

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
