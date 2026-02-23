"""
LLM Service - Groq API Integration for Llama 3.1 8B

Handles multilingual real estate queries with strict language matching.
Supports Tamil script, Tanglish, and English.
Uses direct HTTP API calls to avoid SDK compatibility issues.
"""

import httpx
from app.config import settings
from app.services.domain_validator import detect_language
from app.services.tn_knowledge_base import get_knowledge_context
from typing import List, Dict


class LLMService:
    """Service for interacting with Llama 3.1 8B via Groq API."""
    
    def __init__(self):
        self.api_key = settings.groq_api_key
        self.model = settings.llm_model
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"
        print(f"✅ LLM Service initialized with model: {self.model}")
        
    def _get_system_prompt(self, language: str, context: str = "") -> str:
        """
        Generate system prompt based on language and context.
        
        Args:
            language: Detected language (tamil, tanglish, english)
            context: Relevant knowledge base context
            
        Returns:
            System prompt string
        """
        base_instructions = """You are PurityProp AI — a Tamil Nadu Real Estate AI Assistant. You MUST follow these rules STRICTLY:

DOMAIN RESTRICTION:
- Answer ONLY real estate-related questions about Tamil Nadu, India
- Topics: property buying/selling, registration, documents, bank loans, legal compliance
- If asked about non-real estate topics, politely refuse and redirect

ANTI-HALLUCINATION RULES (CRITICAL — FOLLOW EXACTLY):
1. ONLY use information from the RELEVANT KNOWLEDGE section provided below
2. If the answer is NOT in the provided knowledge, say: "I don't have specific information about that. Please consult your local Sub-Registrar office or a legal professional."
3. NEVER invent or guess numbers, dates, percentages, or legal procedures
4. NEVER make up government office names, website URLs, or phone numbers
5. If unsure about any fact, clearly say "I'm not certain about this specific detail"
6. Use phrases like "According to Tamil Nadu regulations" ONLY when the fact is in the provided knowledge
7. DO NOT extrapolate or assume — stick strictly to what is provided

LANGUAGE MATCHING RULE (CRITICAL):
"""
        
        language_instructions = {
            "tamil": """- User is asking in TAMIL SCRIPT (தமிழ் எழுத்துக்கள்)
- You MUST respond ONLY in TAMIL SCRIPT
- DO NOT use English letters or Tanglish
- Example: If user asks "சென்னையில் வீடு வாங்க என்ன ஆவணங்கள் தேவை?", respond entirely in Tamil script""",
            
            "tanglish": """- User is asking in TANGLISH (Tamil language using English letters)
- You MUST respond ONLY in TANGLISH
- DO NOT use Tamil script or pure English
- Example: If user asks "Chennai la veedu vaanga enna documents venum?", respond like "Chennai la veedu vaanga indha documents venum: Sale deed, EC, patta..."
- Write Tamil words using English alphabet (vaanga, venum, enna, epdi, etc.)""",
            
            "english": """- User is asking in ENGLISH
- You MUST respond ONLY in ENGLISH
- Use professional, clear English language
- DO NOT use Tamil script or Tanglish
- Example: If user asks "What documents are needed to buy a house in Chennai?", respond in proper English"""
        }
        
        response_structure = """

RESPONSE STRUCTURE:
1. Answer ONLY from the RELEVANT KNOWLEDGE provided below
2. Step-by-step process (if applicable and present in knowledge)
3. Required documents (if applicable and present in knowledge)
4. Risks and red flags (if applicable and present in knowledge)
5. If the user's question is not covered in the knowledge, honestly say so

LEGAL CAUTION:
- Always add disclaimer: "This is informational guidance only, not legal advice"
- Suggest consulting legal professionals for specific cases
- NEVER predict property prices or guarantee investment returns
- NEVER make up legal section numbers or act numbers

TAMIL NADU CONTEXT:
- Default to Chennai/Tamil Nadu laws and procedures
- Reference authorities: TNRERA, DTCP, CMDA, Sub-Registrar — ONLY when relevant
- Reference Tamil Nadu Registration Department procedures
"""
        
        context_section = ""
        if context:
            context_section = f"""

RELEVANT KNOWLEDGE (USE ONLY THIS TO ANSWER — DO NOT ADD INFORMATION NOT PRESENT HERE):
{context}

REMINDER: If the user's question cannot be fully answered from the above knowledge, say "I don't have complete information on this topic. Please consult a legal professional or your local Sub-Registrar office for accurate details."
"""
        else:
            context_section = """

NOTE: No specific knowledge was found for this query. Provide a general response based on common Tamil Nadu real estate practices, but clearly state: "For specific and accurate details, please consult your local Sub-Registrar office or a legal professional."
"""
        
        return (base_instructions + 
                language_instructions.get(language, language_instructions["english"]) +
                response_structure + 
                context_section)
    
    def generate_response(
        self, 
        user_message: str, 
        conversation_history: List[Dict[str, str]] = None
    ) -> tuple[str, str]:
        """
        Generate response using Llama 3.1 8B via direct HTTP API.
        
        Args:
            user_message: User's input message
            conversation_history: Previous messages in conversation
            
        Returns:
            Tuple of (response_text, detected_language)
        """
        # Detect language
        language = detect_language(user_message)
        
        # Get relevant knowledge context
        context = get_knowledge_context(user_message.lower())
        
        # Build system prompt
        system_prompt = self._get_system_prompt(language, context)
        
        # Build messages for API
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history if available
        if conversation_history:
            messages.extend(conversation_history[-6:])  # Last 3 exchanges
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        try:
            # Call Groq API directly using httpx
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": settings.llm_temperature,
                "max_tokens": settings.llm_max_tokens,
            }
            
            with httpx.Client(timeout=30.0) as client:
                response = client.post(self.api_url, json=payload, headers=headers)
                response.raise_for_status()
                
            result = response.json()
            assistant_message = result["choices"][0]["message"]["content"]
            return assistant_message, language
            
        except httpx.HTTPStatusError as e:
            print(f"❌ HTTP Error calling Groq API: {e.response.status_code} - {e.response.text}")
            error_messages = {
                "tamil": "மன்னிக்கவும், தற்போது பதில் அளிக்க முடியவில்லை. தயவுசெய்து மீண்டும் முயற்சிக்கவும்.",
                "tanglish": "Mannikkavum, ippo response kudukka mudiyala. Please try again.",
                "english": "I apologize, but I'm unable to generate a response at the moment. Please try again."
            }
            return error_messages.get(language, error_messages["english"]), language
        except Exception as e:
            print(f"❌ Error calling Groq API: {e}")
            error_messages = {
                "tamil": "மன்னிக்கவும், தற்போது பதில் அளிக்க முடியவில்லை. தயவுசெய்து மீண்டும் முயற்சிக்கவும்.",
                "tanglish": "Mannikkavum, ippo response kudukka mudiyala. Please try again.",
                "english": "I apologize, but I'm unable to generate a response at the moment. Please try again."
            }
            return error_messages.get(language, error_messages["english"]), language


# Global LLM service instance
llm_service = LLMService()
