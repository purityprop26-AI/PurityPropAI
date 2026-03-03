"""
Domain Validator Service — v2 (Precision Rewrite)

Decision Tree:
  1. Contains TN locality name? → ACCEPT (real estate intent implied)
  2. Contains RE keyword? → ACCEPT
  3. Matches RE regex pattern? → ACCEPT
  4. Contains STRONG non-RE indicator (word-boundary)? → REJECT
  5. DEFAULT → ACCEPT with low-confidence flag (let LLM handle)

Changes from v1:
  - Locality-first acceptance gate (eliminates over-rejection)
  - Word-boundary matching (prevents "game" matching "engagement")
  - Removed 'code', 'history' from blocklist (false rejects)
  - Default-accept instead of default-reject
"""

import re
from typing import Tuple


# Real estate keywords (English, Tamil, Tanglish)
REAL_ESTATE_KEYWORDS = [
    # Property types
    'property', 'house', 'home', 'land', 'plot', 'apartment', 'flat', 'villa',
    'real estate', 'buy', 'sell', 'purchase', 'sale', 'registration', 'document',
    'loan', 'mortgage', 'bank loan', 'emi', 'stamp duty', 'registration fee',
    'tnrera', 'rera', 'dtcp', 'cmda', 'sub-registrar', 'patta', 'chitta',
    'encumbrance', 'title deed', 'sale deed', 'builder', 'developer',
    'construction', 'building', 'residential', 'commercial', 'investment',
    'bhk', '1bhk', '2bhk', '3bhk', '4bhk',

    # Measurement units
    'cent', 'cents', 'square feet', 'sqft', 'sq ft', 'sq.ft', 'square foot',
    'acre', 'acres', 'ground', 'grounds', 'gunta', 'guntas', 'ankanam',
    'square meter', 'sqm', 'sq m', 'square yard', 'sq yd',

    # Price and valuation
    'price', 'rate', 'cost', 'value', 'worth', 'budget', 'valuation',
    'guideline value', 'market value', 'circle rate',

    # Tamil (English script - Tanglish)
    'veedu', 'vidu', 'nilam', 'manaiyadi', 'kudiyiruppu',
    'vaanga', 'vanga', 'vikka', 'vaangu', 'vilai', 'vilay',
    'pathivu', 'pativu', 'aavanam', 'avanam', 'kadan', 'vatti',

    # Tamil script
    'வீடு', 'நிலம்', 'மனையடி', 'குடியிருப்பு', 'வாங்க', 'விற்க',
    'பதிவு', 'ஆவணம்', 'ஆவணங்கள்', 'கடன்', 'வங்கி', 'முத்திரை',
    'சென்ட்', 'ஏக்கர்', 'சதுர அடி'
]

# Strong non-RE indicators — requires WORD BOUNDARY match
# Removed: 'code' (conflicts with "pin code"), 'history' (conflicts with "price history")
# Removed: 'game' (conflicts with "cricket ground"), 'science' (conflicts with "data science in RE")
NON_REAL_ESTATE_INDICATORS = [
    'poem', 'story', 'joke', 'recipe', 'weather forecast',
    'movie', 'song', 'cricket', 'football', 'programming',
    'python', 'javascript', 'math problem',
    'kavithai', 'kathai', 'comedy', 'cinema', 'padam'
]

# Real estate question patterns
REAL_ESTATE_PATTERNS = [
    r'(how|what|where|when|which|why).*(buy|purchase|sell|register)',
    r'(documents?|papers?).*(need|require|necessary)',
    r'(process|procedure|steps).*(buy|sell|register)',
    r'(loan|finance|bank).*(property|house|home)',
    r'(stamp duty|registration fee|charges)',
    r'(tnrera|rera|dtcp|cmda)',
    r'(per|price|rate).*(sqft|sq\.?ft|square|ground|cent|acre)',
    r'(land|plot|flat|apartment|villa).*(price|rate|cost|value)',
    r'\b\d+\s*(bhk|BHK)\b',
]

MAX_QUERY_LENGTH = 1000


def is_real_estate_query(query: str) -> Tuple[bool, str]:
    """
    Determine if a query is related to real estate.

    Uses a 5-gate decision tree: Locality → Keyword → Pattern → Blocklist → Default-Accept.
    """
    if not query:
        return False, "Empty query"

    if len(query) > MAX_QUERY_LENGTH:
        return False, "Query too long"

    query_lower = query.lower().strip()

    if len(query_lower) < 3:
        return False, "Query too short"

    # ── GATE 1: TN locality name → always accept ─────────────────────
    # If user mentions a Tamil Nadu locality, they want real estate info.
    try:
        from app.services.govt_data_service import LOCALITY_KEYWORDS
        for keyword in LOCALITY_KEYWORDS:
            if keyword in query_lower:
                return True, f"Tamil Nadu locality detected: {keyword}"
    except ImportError:
        pass  # Fallback if govt_data_service not available

    # ── GATE 2: Real estate keyword → accept ─────────────────────────
    for keyword in REAL_ESTATE_KEYWORDS:
        if keyword.lower() in query_lower:
            return True, "Real estate keyword found"

    # ── GATE 3: RE regex pattern → accept ────────────────────────────
    for pattern in REAL_ESTATE_PATTERNS:
        if re.search(pattern, query_lower):
            return True, "Real estate pattern matched"

    # ── GATE 4: Strong non-RE indicator (word-boundary) → reject ─────
    # Only reject if NONE of Gates 1-3 triggered
    for indicator in NON_REAL_ESTATE_INDICATORS:
        if re.search(rf'\b{re.escape(indicator)}\b', query_lower):
            return False, f"Non-real estate topic detected: {indicator}"

    # ── GATE 5: Default → accept ─────────────────────────────────────
    # Let LLM guardrails handle edge cases. Better UX than false rejection.
    return True, "Ambiguous query — forwarding to LLM for domain check"


def get_rejection_message(language: str = "english") -> str:
    """Get rejection message in the appropriate language."""
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
    """Detect language: 'tamil', 'tanglish', or 'english'."""
    # Check for Tamil script (Unicode range)
    tamil_chars = re.findall(r'[\u0B80-\u0BFF]', text)
    if len(tamil_chars) > 3:
        return "tamil"

    # Tanglish detection with word boundaries
    tanglish_patterns = [
        r'\b(veedu|vidu)\b', r'\b(vaanga|vanga)\b',
        r'\b(enna|yenna)\b', r'\b(epdi|eppadi|yeppadi)\b',
        r'\b(venum|vendum)\b', r'\b(panna|pannu)\b',
        r'\b(irukku|iruku)\b', r'\b(sollu|sollunga)\b',
        r'\b(kudukka|kudu)\b', r'\b(nalla|nalladhu)\b',
        r'\b(illa|illai)\b', r'\b(aana|ana)\b',
        r'\b(naan|nan)\b', r'\b(nee|neenga)\b',
        r'\b(avaru|avar)\b',
    ]

    text_lower = text.lower()
    tanglish_matches = sum(1 for p in tanglish_patterns if re.search(p, text_lower))

    if tanglish_matches >= 2:
        return "tanglish"

    # Tanglish suffix patterns
    tanglish_suffix_patterns = [
        r'\w+\s+la\b', r'\w+\s+ku\b',
        r'\w+\s+oda\b', r'\w+\s+ah\b',
    ]
    tanglish_matches += sum(1 for p in tanglish_suffix_patterns if re.search(p, text_lower))

    if tanglish_matches >= 1:
        return "tanglish"

    return "english"


def extract_locality(query: str) -> str:
    """
    Extract locality name from user query.
    Returns the database-normalized locality name (e.g., 'anna_nagar').
    Returns empty string if no locality found.

    Strategy:
    1. Try LOCALITY_KEYWORDS dict (80 Chennai localities) — exact match
    2. Fall back to smart text normalization — converts multi-word place names
       to DB format (e.g., 'RS Puram' → 'rs_puram', 'Ellis Nagar' → 'ellis_nagar')
    """
    query_lower = query.lower().strip()

    # Strategy 1: LOCALITY_KEYWORDS dict (fast, exact)
    try:
        from app.services.govt_data_service import LOCALITY_KEYWORDS
        sorted_keywords = sorted(LOCALITY_KEYWORDS.keys(), key=len, reverse=True)
        for keyword in sorted_keywords:
            if keyword in query_lower:
                _district, locality_key = LOCALITY_KEYWORDS[keyword]
                return locality_key
    except ImportError:
        pass

    # Strategy 2: Smart text normalization for PDF-imported localities
    # Remove common noise words and extract location-like phrases
    noise_words = {
        'what', 'is', 'the', 'of', 'in', 'at', 'for', 'and', 'or', 'a', 'an',
        'land', 'price', 'rate', 'value', 'property', 'apartment', 'flat', 'villa',
        'cost', 'how', 'much', 'tell', 'me', 'about', 'give', 'show', 'current',
        'average', 'market', 'commercial', 'residential', 'per', 'sqft', 'ground',
        'buy', 'sell', 'purchase', 'rent', 'investment', 'query', 'please', 'can',
        'you', 'i', 'want', 'to', 'know', 'details', 'information', 'info',
        'chennai', 'coimbatore', 'madurai', 'salem', 'trichy', 'vellore', 'erode',
        'tiruppur', 'tirunelveli', 'karur', 'kancheepuram', 'puducherry',
        'tamil', 'nadu', 'tn', 'district', 'area', 'zone', 'near', 'nearby',
    }

    # Extract potential locality words (everything that's not noise)
    words = re.sub(r'[^a-z0-9\s]', '', query_lower).split()
    location_words = [w for w in words if w not in noise_words and len(w) > 1]

    if not location_words:
        return ""

    # Try multi-word combinations (longest first)
    # "rs puram" → "rs_puram", "db road" → "db_road"
    for length in range(min(4, len(location_words)), 0, -1):
        for i in range(len(location_words) - length + 1):
            candidate = '_'.join(location_words[i:i+length])
            if len(candidate) > 2:
                return candidate

    return ""


def extract_asset_type_from_query(query: str) -> str:
    """
    Extract asset type from user query.
    Returns: 'land', 'apartment', 'villa', or 'commercial'.
    Defaults to 'land' if not detected.
    """
    query_lower = query.lower()
    if any(w in query_lower for w in ['apartment', 'flat', 'flats', 'apartments', 'bhk']):
        return 'apartment'
    if any(w in query_lower for w in ['villa', 'villas', 'independent house', 'bungalow']):
        return 'villa'
    if any(w in query_lower for w in ['commercial', 'office', 'shop', 'showroom', 'warehouse']):
        return 'commercial'
    return 'land'
