"""
Domain Validator Service

Ensures that only real estate-related queries are processed.
Rejects non-real estate questions politely.
"""

import re
from typing import Tuple


# Real estate keywords (English, Tamil, Tanglish)
REAL_ESTATE_KEYWORDS = [
    # English - Property types
    'property', 'house', 'home', 'land', 'plot', 'apartment', 'flat', 'villa',
    'real estate', 'buy', 'sell', 'purchase', 'sale', 'registration', 'document',
    'loan', 'mortgage', 'bank loan', 'emi', 'stamp duty', 'registration fee',
    'tnrera', 'rera', 'dtcp', 'cmda', 'sub-registrar', 'patta', 'chitta',
    'encumbrance', 'title deed', 'sale deed', 'builder', 'developer',
    'construction', 'building', 'residential', 'commercial', 'investment',
    
    # Measurement units (very important!)
    'cent', 'cents', 'square feet', 'sqft', 'sq ft', 'sq.ft', 'square foot',
    'acre', 'acres', 'ground', 'grounds', 'gunta', 'guntas', 'ankanam',
    'square meter', 'sqm', 'sq m', 'square yard', 'sq yd',
    
    # Location and area terms
    'area', 'location', 'locality', 'neighborhood', 'near', 'nearby',
    'price', 'rate', 'cost', 'value', 'worth', 'budget',
    'chennai', 'coimbatore', 'madurai', 'salem', 'trichy', 'tirupur',
    'erode', 'vellore', 'thoothukudi', 'dindigul', 'thanjavur',
    'nagar', 'puram', 'colony', 'street', 'road', 'avenue',
    
    # Tamil (in English script - Tanglish)
    'veedu', 'vidu', 'nilam', 'manaiyadi', 'kudiyiruppu', 'apartment',
    'vaanga', 'vanga', 'vikka', 'vaangu', 'vilai', 'vilay',
    'pathivu', 'pativu', 'aavanam', 'avanam', 'kadan', 'vatti',
    'stamp duty', 'registration', 'documents', 'papers',
    
    # Tamil script keywords (for detection)
    'வீடு', 'நிலம்', 'மனையடி', 'குடியிருப்பு', 'வாங்க', 'விற்க',
    'பதிவு', 'ஆவணம்', 'ஆவணங்கள்', 'கடன்', 'வங்கி', 'முத்திரை',
    'சென்ட்', 'ஏக்கர்', 'சதுர அடி'
]

# Non-real estate indicators
NON_REAL_ESTATE_INDICATORS = [
    'poem', 'story', 'joke', 'recipe', 'weather', 'movie', 'song',
    'game', 'sport', 'cricket', 'football', 'code', 'programming',
    'python', 'javascript', 'math', 'science', 'history',
    'kavithai', 'kathai', 'comedy', 'cinema', 'padam'
]


# Maximum allowed query length to prevent Regex DoS
MAX_QUERY_LENGTH = 1000

def is_real_estate_query(query: str) -> Tuple[bool, str]:
    """
    Determine if a query is related to real estate.
    
    Args:
        query: User's input query
        
    Returns:
        Tuple of (is_valid, reason)
    """
    if not query:
        return False, "Empty query"

    # 1. Length Check (DoS Protection)
    if len(query) > MAX_QUERY_LENGTH:
        return False, "Query too long"
        
    query_lower = query.lower().strip()
    
    # Check if query is too short
    if len(query_lower) < 3:
        return False, "Query too short"
    
    # Check for non-real estate indicators first
    for indicator in NON_REAL_ESTATE_INDICATORS:
        if indicator in query_lower:
            return False, f"Non-real estate topic detected: {indicator}"
    
    # Check for real estate keywords
    for keyword in REAL_ESTATE_KEYWORDS:
        if keyword.lower() in query_lower:
            return True, "Real estate keyword found"
    
    # Check for common real estate question patterns
    real_estate_patterns = [
        r'(how|what|where|when|which|why).*(buy|purchase|sell|register)',
        r'(documents?|papers?).*(need|require|necessary)',
        r'(process|procedure|steps).*(buy|sell|register)',
        r'(loan|finance|bank).*(property|house|home)',
        r'(stamp duty|registration fee|charges)',
        r'(tnrera|rera|dtcp|cmda)',
    ]
    
    for pattern in real_estate_patterns:
        if re.search(pattern, query_lower):
            return True, "Real estate pattern matched"
    
    # If no clear indicators, it's ambiguous - reject to be safe
    return False, "No clear real estate context"


def get_rejection_message(language: str = "english") -> str:
    """
    Get appropriate rejection message based on detected language.
    
    Args:
        language: Detected language (english, tamil, tanglish)
        
    Returns:
        Rejection message in appropriate language
    """
    messages = {
        "english": (
            "I apologize, but I can only answer questions related to real estate in Tamil Nadu. "
            "I'm here to help with:\n"
            "• Property buying and selling\n"
            "• Registration processes\n"
            "• Required documents\n"
            "• Bank loans for property\n"
            "• Legal compliance and regulations\n\n"
            "Please ask a real estate-related question, and I'll be happy to help!"
        ),
        "tamil": (
            "மன்னிக்கவும், நான் தமிழ்நாட்டில் ரியல் எஸ்டேட் தொடர்பான கேள்விகளுக்கு மட்டுமே பதிலளிக்க முடியும். "
            "நான் உதவக்கூடிய விஷயங்கள்:\n"
            "• சொத்து வாங்குதல் மற்றும் விற்பனை\n"
            "• பதிவு செயல்முறைகள்\n"
            "• தேவையான ஆவணங்கள்\n"
            "• சொத்துக்கான வங்கி கடன்\n"
            "• சட்ட இணக்கம் மற்றும் விதிமுறைகள்\n\n"
            "தயவுசெய்து ரியல் எஸ்டேட் தொடர்பான கேள்வி கேளுங்கள், நான் மகிழ்ச்சியுடன் உதவுவேன்!"
        ),
        "tanglish": (
            "Mannikkavum, naan Tamil Nadu la real estate related questions ku mattum than answer panna mudiyum. "
            "Naan help panna koodiya vishayangal:\n"
            "• Property vaanguradu and vikkurathu\n"
            "• Registration process\n"
            "• Thevaiyana documents\n"
            "• Property ku bank loan\n"
            "• Legal compliance and rules\n\n"
            "Please real estate related question kelunga, naan help pandren!"
        )
    }
    
    return messages.get(language, messages["english"])


def detect_language(text: str) -> str:
    """
    Detect language from text with improved accuracy.
    
    Args:
        text: Input text
        
    Returns:
        Language code: 'tamil', 'tanglish', or 'english'
    """
    # Check for Tamil script (Unicode range for Tamil)
    tamil_chars = re.findall(r'[\u0B80-\u0BFF]', text)
    if len(tamil_chars) > 3:
        return "tamil"
    
    # Improved Tanglish detection using word boundaries
    # These are common Tamil words written in English that are unlikely to appear in pure English
    tanglish_patterns = [
        r'\b(veedu|vidu)\b',  # house
        r'\b(vaanga|vanga)\b',  # buy
        r'\b(enna|yenna)\b',  # what
        r'\b(epdi|eppadi|yeppadi)\b',  # how
        r'\b(venum|vendum)\b',  # need/want
        r'\b(panna|pannu)\b',  # do/make
        r'\b(irukku|iruku)\b',  # is/are
        r'\b(sollu|sollunga)\b',  # tell/say
        r'\b(kudukka|kudu)\b',  # give
        r'\b(nalla|nalladhu)\b',  # good
        r'\b(illa|illai)\b',  # no/not
        r'\b(aana|ana)\b',  # but
        r'\b(naan|nan)\b',  # I
        r'\b(nee|neenga)\b',  # you
        r'\b(avaru|avar)\b',  # he/she/they
    ]
    
    # Check for Tanglish patterns with word boundaries
    text_lower = text.lower()
    tanglish_matches = 0
    for pattern in tanglish_patterns:
        if re.search(pattern, text_lower):
            tanglish_matches += 1
    
    # If we find 2 or more Tanglish words, it's likely Tanglish
    if tanglish_matches >= 2:
        return "tanglish"
    
    # Check for common Tanglish suffixes (Chennai la, bank ku, etc.)
    # Only match if preceded by a word character
    tanglish_suffix_patterns = [
        r'\w+\s+la\b',  # Chennai la, bank la
        r'\w+\s+ku\b',  # veedu ku, property ku
        r'\w+\s+oda\b',  # avar oda, naan oda
        r'\w+\s+ah\b',  # nalla ah, romba ah
    ]
    
    for pattern in tanglish_suffix_patterns:
        if re.search(pattern, text_lower):
            tanglish_matches += 1
    
    # If we have at least 1 strong Tanglish indicator, classify as Tanglish
    if tanglish_matches >= 1:
        return "tanglish"
    
    # Default to English for pure English queries
    return "english"
