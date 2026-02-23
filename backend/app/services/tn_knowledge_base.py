"""
Tamil Nadu Real Estate Knowledge Base

Contains comprehensive information about real estate processes,
regulations, and requirements specific to Tamil Nadu, India.
"""

TN_KNOWLEDGE_BASE = {
    "property_registration": {
        "process": [
            "1. Document Verification - Verify all property documents including title deed, encumbrance certificate (EC), tax receipts",
            "2. Sale Agreement - Draft and execute sale agreement on stamp paper",
            "3. Payment - Pay stamp duty and registration fees",
            "4. Sub-Registrar Office - Visit the jurisdictional Sub-Registrar office",
            "5. Biometric Verification - Both parties undergo biometric verification",
            "6. Document Submission - Submit all required documents",
            "7. Registration - Complete registration process and receive registered sale deed",
            "8. Mutation - Apply for property tax mutation with local body"
        ],
        "timeline": "Typically 1-2 weeks after document preparation",
        "authorities": ["Sub-Registrar Office", "Tamil Nadu Registration Department"]
    },
    
    "required_documents": {
        "buyer": [
            "PAN Card",
            "Aadhaar Card",
            "Address Proof",
            "Passport-size photographs",
            "Bank account details (for loan cases)"
        ],
        "seller": [
            "Original Sale Deed / Title Deed",
            "Encumbrance Certificate (EC) for last 13-30 years",
            "Property Tax Receipts (last 3 years)",
            "Approved Building Plan (for constructed properties)",
            "Completion Certificate (if applicable)",
            "NOC from Society/Apartment (if applicable)",
            "PAN Card and Aadhaar Card"
        ],
        "property": [
            "Parent Document (previous sale deed)",
            "Patta and Chitta (land ownership records)",
            "Survey Number details",
            "Layout Approval from DTCP/CMDA (for plots)",
            "Occupancy Certificate (for buildings)"
        ]
    },
    
    "authorities": {
        "TNRERA": {
            "name": "Tamil Nadu Real Estate Regulatory Authority",
            "role": "Regulates real estate projects and protects buyer interests",
            "website": "https://rera.tn.gov.in",
            "mandate": "All projects above 500 sq.m or 8 apartments must be registered"
        },
        "DTCP": {
            "name": "Directorate of Town and Country Planning",
            "role": "Approves layout plans and ensures planned development",
            "jurisdiction": "Areas outside Chennai Corporation limits"
        },
        "CMDA": {
            "name": "Chennai Metropolitan Development Authority",
            "role": "Planning authority for Chennai Metropolitan Area",
            "jurisdiction": "Chennai and surrounding areas"
        },
        "Sub_Registrar": {
            "name": "Sub-Registrar Office",
            "role": "Property registration and document verification",
            "location": "Based on property location jurisdiction"
        }
    },
    
    "stamp_duty_registration": {
        "stamp_duty": "7% of property value (for properties above ₹50 lakhs in urban areas)",
        "registration_fee": "1% of property value (maximum ₹1 lakh)",
        "women_benefit": "2% discount on stamp duty for properties registered in women's names",
        "calculation": "Based on guideline value or transaction value, whichever is higher"
    },
    
    "measurement_units": {
        "cent": {
            "definition": "A cent is a common land measurement unit in South India, especially Tamil Nadu",
            "conversion": "1 cent = 435.6 square feet = 40.47 square meters",
            "usage": "Commonly used for residential plots and small land parcels",
            "example": "A standard residential plot might be 3-5 cents (1,300-2,200 sq ft)"
        },
        "ground": {
            "definition": "Ground is another traditional measurement unit used in Tamil Nadu",
            "conversion": "1 ground = 2,400 square feet = 222.97 square meters",
            "relation": "1 ground = approximately 5.5 cents"
        },
        "acre": {
            "definition": "Acre is used for larger land parcels",
            "conversion": "1 acre = 43,560 square feet = 4,047 square meters = 100 cents",
            "usage": "Used for agricultural land and large plots"
        },
        "gunta": {
            "definition": "Gunta (also called guntha) is used in some parts of Tamil Nadu",
            "conversion": "1 gunta = 1,089 square feet = 101.17 square meters",
            "relation": "40 guntas = 1 acre"
        },
        "common_conversions": [
            "1 cent = 435.6 sq ft",
            "1 ground = 2,400 sq ft = 5.5 cents",
            "1 acre = 100 cents = 43,560 sq ft",
            "1 gunta = 1,089 sq ft = 2.5 cents"
        ]
    },
    
    "red_flags": [
        "Property without clear title or disputed ownership",
        "Encumbrance Certificate showing pending loans or legal cases",
        "Unapproved layouts by DTCP/CMDA",
        "Properties in prohibited areas (poramboke land, water bodies)",
        "Missing or fake completion certificates",
        "Developer not registered with TNRERA (for new projects)",
        "Significant difference between guideline value and asking price",
        "Seller unwilling to provide complete documentation",
        "Properties with pending property tax dues",
        "Land use conversion not approved (agricultural to residential)"
    ],
    
    "bank_loan": {
        "eligibility": [
            "Age: 21-65 years (varies by bank)",
            "Income: Stable monthly income (salaried/self-employed)",
            "Credit Score: Minimum 750 recommended",
            "Employment: Minimum 2-3 years work experience"
        ],
        "documents": [
            "Loan application form",
            "Identity and address proof",
            "Income proof (salary slips, ITR, bank statements)",
            "Property documents for verification",
            "Processing fee payment proof"
        ],
        "process": [
            "1. Loan application and eligibility check",
            "2. Property document verification by bank",
            "3. Property valuation by bank-approved valuers",
            "4. Legal verification of title",
            "5. Loan sanction letter",
            "6. Disbursement after registration"
        ],
        "loan_to_value": "Usually 75-90% of property value",
        "tenure": "Up to 30 years"
    },
    
    "chennai_specific": {
        "zones": ["North Chennai", "Central Chennai", "South Chennai", "West Chennai"],
        "planning_authority": "CMDA (Chennai Metropolitan Development Authority)",
        "property_tax": "Collected by Greater Chennai Corporation",
        "water_connection": "Chennai Metro Water (CMWSSB)",
        "electricity": "Tangedco (Tamil Nadu Generation and Distribution Corporation)"
    },
    
    "land_conversion": {
        "what": "Converting agricultural land to residential/commercial use in Tamil Nadu",
        "when_needed": [
            "Building a house on agricultural land",
            "Selling agricultural land for non-agricultural purposes",
            "Setting up commercial establishment on farm land"
        ],
        "process": [
            "1. Apply to District Collector's office with required documents",
            "2. Revenue department inspects the land",
            "3. Get NOC from Agricultural department",
            "4. Pay conversion fees (varies by district, typically Rs.1-5 per sq.ft)",
            "5. Receive conversion order from District Collector",
            "6. Update Patta and Chitta records at Taluk office",
            "7. Get revised Patta reflecting new land classification"
        ],
        "required_documents": [
            "Original Patta and Chitta",
            "Encumbrance Certificate",
            "FMB (Field Measurement Book) sketch",
            "Tax receipts",
            "Aadhaar and PAN card",
            "Application form with reason for conversion"
        ],
        "timeline": "1-3 months depending on district",
        "restrictions": [
            "Wetlands and water body adjacent lands may be restricted",
            "Agricultural zone lands may not allow conversion",
            "Check local master plan for permitted land use",
            "Some areas have automatic deemed conversion under GO 93"
        ]
    },
    
    "legal_disputes": {
        "common_types": [
            "Title disputes - Multiple people claiming ownership",
            "Boundary disputes - Disagreement on property boundaries",
            "Encroachment - Unauthorized occupation of land",
            "Partition suits - Family property division disputes",
            "Specific performance - Enforcing sale agreements",
            "Tenant eviction - Disputes with tenants"
        ],
        "resolution_options": [
            "Mediation through Lok Adalat (free, faster resolution)",
            "Civil court litigation (can take 5-15 years)",
            "Revenue court for land record disputes",
            "Consumer court for builder-buyer disputes",
            "TNRERA for registered project complaints"
        ],
        "prevention_tips": [
            "Always get EC for 30 years before buying",
            "Hire an independent lawyer for title verification",
            "Verify Patta and Chitta match",
            "Check for pending litigation on the property",
            "Get legal opinion certificate from a qualified advocate"
        ]
    },
    
    "nri_property": {
        "can_buy": [
            "Residential property - Yes, without RBI permission",
            "Commercial property - Yes, without RBI permission",
            "Agricultural land - NO, NRIs cannot buy agricultural land",
            "Plantation property - NO, NRIs cannot buy plantation land",
            "Farm house - NO, NRIs cannot buy farm houses"
        ],
        "process": [
            "1. Can use NRE/NRO/FCNR account for payment",
            "2. Power of Attorney (PoA) can be used if NRI cannot be present",
            "3. PoA must be notarized at Indian Embassy/Consulate abroad",
            "4. Same registration process at Sub-Registrar office",
            "5. Stamp duty and registration fees are the same as residents",
            "6. TDS of 20% applicable on sale (can claim refund via ITR)"
        ],
        "documents_extra": [
            "Valid Indian Passport",
            "OCI/PIO card (if applicable)",
            "NRE/NRO bank account statement",
            "Power of Attorney (if not present in India)"
        ]
    },
    
    "government_schemes": {
        "pmay": {
            "name": "Pradhan Mantri Awas Yojana (PMAY)",
            "benefit": "Interest subsidy of 3-6.5% on home loans",
            "eligibility": "Annual household income up to Rs.18 lakh",
            "categories": [
                "EWS (up to Rs.3 lakh income) - Rs.6.5 lakh subsidy",
                "LIG (Rs.3-6 lakh income) - Rs.6.5 lakh subsidy",
                "MIG-I (Rs.6-12 lakh income) - Rs.4 lakh subsidy",
                "MIG-II (Rs.12-18 lakh income) - Rs.3 lakh subsidy"
            ]
        },
        "tn_housing_board": {
            "name": "Tamil Nadu Housing Board (TNHB)",
            "role": "Provides affordable housing in Tamil Nadu",
            "how_to_apply": "Apply online at tnhb.tn.gov.in during announcement periods",
            "locations": "Projects across Chennai, Coimbatore, Madurai, Trichy, Salem"
        }
    },
    
    "property_tax": {
        "chennai": {
            "authority": "Greater Chennai Corporation (GCC)",
            "payment": "Half-yearly (April-September, October-March)",
            "online_payment": "chennaicorporation.gov.in",
            "penalty": "2% per month for late payment"
        },
        "calculation": "Based on Annual Rental Value (ARV) method in Tamil Nadu",
        "exemptions": [
            "Properties used for charitable purposes",
            "Government buildings",
            "Places of worship"
        ],
        "importance": [
            "Tax receipts required for property registration",
            "Pending tax dues can block property sale",
            "Name mutation in tax records is essential after buying property"
        ]
    },
    
    "online_services": {
        "tnreginet": {
            "url": "tnreginet.gov.in",
            "services": ["EC application", "Guideline value check", "Document search", "Appointment booking"]
        },
        "tn_eservices": {
            "url": "eservices.tn.gov.in",
            "services": ["Patta application", "Chitta view", "FMB sketch", "Revenue records"]
        },
        "rera_tn": {
            "url": "rera.tn.gov.in",
            "services": ["Project search", "Developer verification", "Complaint filing"]
        }
    }
}


def get_knowledge_context(query_lower: str) -> str:
    """
    Get relevant knowledge base context based on query keywords.
    
    Args:
        query_lower: Lowercase user query
        
    Returns:
        Relevant context string
    """
    context_parts = []
    
    # Check for registration-related queries
    if any(word in query_lower for word in ['register', 'registration', 'sub-registrar', 'பதிவு', 'pathivu']):
        context_parts.append("PROPERTY REGISTRATION PROCESS:\n" + 
                           "\n".join(TN_KNOWLEDGE_BASE['property_registration']['process']))
    
    # Check for document-related queries
    if any(word in query_lower for word in ['document', 'documents', 'papers', 'ஆவணம்', 'ஆவணங்கள்', 'avanam', 'aavanam']):
        docs = TN_KNOWLEDGE_BASE['required_documents']
        context_parts.append(f"REQUIRED DOCUMENTS:\nBuyer: {', '.join(docs['buyer'])}\n" +
                           f"Seller: {', '.join(docs['seller'])}\n" +
                           f"Property: {', '.join(docs['property'])}")
    
    # Check for loan-related queries
    if any(word in query_lower for word in ['loan', 'bank', 'finance', 'emi', 'கடன்', 'வங்கி', 'kadan', 'vatti']):
        loan = TN_KNOWLEDGE_BASE['bank_loan']
        context_parts.append(f"BANK LOAN INFORMATION:\nEligibility: {', '.join(loan['eligibility'])}\n" +
                           f"Process: {', '.join(loan['process'])}\n" +
                           f"Loan-to-Value: {loan['loan_to_value']}\n" +
                           f"Max Tenure: {loan['tenure']}")
    
    # Check for stamp duty queries
    if any(word in query_lower for word in ['stamp', 'duty', 'fee', 'charges', 'cost', 'முத்திரை', 'evvalavu', 'kattanam']):
        stamp = TN_KNOWLEDGE_BASE['stamp_duty_registration']
        context_parts.append(f"STAMP DUTY & REGISTRATION:\n" +
                           f"Stamp Duty: {stamp['stamp_duty']}\n" +
                           f"Registration Fee: {stamp['registration_fee']}\n" +
                           f"Women Benefit: {stamp['women_benefit']}\n" +
                           f"Calculation: {stamp['calculation']}")
    
    # Check for measurement unit queries
    if any(word in query_lower for word in ['cent', 'cents', 'ground', 'acre', 'gunta', 'sqft', 'square feet', 'measurement', 'size', 'area', 'convert']):
        units = TN_KNOWLEDGE_BASE['measurement_units']
        context_parts.append(f"LAND MEASUREMENT UNITS IN TAMIL NADU:\n" +
                           f"Cent: {units['cent']['conversion']} - {units['cent']['usage']}\n" +
                           f"Ground: {units['ground']['conversion']} - {units['ground']['relation']}\n" +
                           f"Acre: {units['acre']['conversion']}\n" +
                           f"Gunta: {units['gunta']['conversion']}\n" +
                           f"Common conversions: {', '.join(units['common_conversions'])}")
    
    # Check for authority-related queries
    if any(word in query_lower for word in ['tnrera', 'rera', 'dtcp', 'cmda', 'authority', 'regulator']):
        auth = TN_KNOWLEDGE_BASE['authorities']
        context_parts.append(f"KEY AUTHORITIES:\n" +
                           f"TNRERA: {auth['TNRERA']['name']} - {auth['TNRERA']['role']}. {auth['TNRERA']['mandate']}\n" +
                           f"DTCP: {auth['DTCP']['name']} - {auth['DTCP']['role']}. Jurisdiction: {auth['DTCP']['jurisdiction']}\n" +
                           f"CMDA: {auth['CMDA']['name']} - {auth['CMDA']['role']}. Jurisdiction: {auth['CMDA']['jurisdiction']}")
    
    # Check for red flag queries
    if any(word in query_lower for word in ['red flag', 'warning', 'risk', 'fraud', 'scam', 'careful', 'danger', 'avoid']):
        context_parts.append("RED FLAGS WHEN BUYING PROPERTY:\n" + 
                           "\n".join(f"• {flag}" for flag in TN_KNOWLEDGE_BASE['red_flags']))
    
    # Check for land conversion queries
    if any(word in query_lower for word in ['conversion', 'convert', 'agricultural', 'farm land', 'nilam', 'maatram']):
        conv = TN_KNOWLEDGE_BASE['land_conversion']
        context_parts.append(f"LAND CONVERSION IN TAMIL NADU:\n" +
                           f"What: {conv['what']}\n" +
                           f"Process:\n" + "\n".join(conv['process']) + "\n" +
                           f"Required Documents: {', '.join(conv['required_documents'])}\n" +
                           f"Timeline: {conv['timeline']}\n" +
                           f"Restrictions: {', '.join(conv['restrictions'])}")
    
    # Check for legal dispute queries
    if any(word in query_lower for word in ['dispute', 'legal', 'court', 'case', 'litigation', 'problem', 'issue', 'fight']):
        legal = TN_KNOWLEDGE_BASE['legal_disputes']
        context_parts.append(f"PROPERTY LEGAL DISPUTES:\n" +
                           f"Common Types:\n" + "\n".join(f"• {t}" for t in legal['common_types']) + "\n" +
                           f"Resolution Options:\n" + "\n".join(f"• {r}" for r in legal['resolution_options']) + "\n" +
                           f"Prevention Tips:\n" + "\n".join(f"• {p}" for p in legal['prevention_tips']))
    
    # Check for NRI queries
    if any(word in query_lower for word in ['nri', 'nre', 'nro', 'abroad', 'overseas', 'foreign', 'poa', 'power of attorney']):
        nri = TN_KNOWLEDGE_BASE['nri_property']
        context_parts.append(f"NRI PROPERTY BUYING IN TAMIL NADU:\n" +
                           f"What NRIs Can Buy:\n" + "\n".join(f"• {c}" for c in nri['can_buy']) + "\n" +
                           f"Process:\n" + "\n".join(nri['process']) + "\n" +
                           f"Extra Documents: {', '.join(nri['documents_extra'])}")
    
    # Check for government scheme queries
    if any(word in query_lower for word in ['scheme', 'pmay', 'subsidy', 'government', 'affordable', 'housing board', 'tnhb', 'thittam']):
        schemes = TN_KNOWLEDGE_BASE['government_schemes']
        pmay = schemes['pmay']
        tnhb = schemes['tn_housing_board']
        context_parts.append(f"GOVERNMENT HOUSING SCHEMES:\n" +
                           f"PMAY: {pmay['name']} - {pmay['benefit']}\n" +
                           f"Eligibility: {pmay['eligibility']}\n" +
                           f"Categories: {', '.join(pmay['categories'])}\n" +
                           f"TNHB: {tnhb['name']} - {tnhb['role']}\n" +
                           f"How to Apply: {tnhb['how_to_apply']}")
    
    # Check for property tax queries
    if any(word in query_lower for word in ['tax', 'property tax', 'vari', 'corporation']):
        tax = TN_KNOWLEDGE_BASE['property_tax']
        context_parts.append(f"PROPERTY TAX IN TAMIL NADU:\n" +
                           f"Chennai: Authority - {tax['chennai']['authority']}, Payment - {tax['chennai']['payment']}\n" +
                           f"Online: {tax['chennai']['online_payment']}\n" +
                           f"Penalty: {tax['chennai']['penalty']}\n" +
                           f"Calculation: {tax['calculation']}\n" +
                           f"Important: {', '.join(tax['importance'])}")
    
    # Check for online services queries
    if any(word in query_lower for word in ['online', 'website', 'apply online', 'internet', 'portal', 'app']):
        services = TN_KNOWLEDGE_BASE['online_services']
        context_parts.append(f"ONLINE SERVICES:\n" +
                           f"TNReginet ({services['tnreginet']['url']}): {', '.join(services['tnreginet']['services'])}\n" +
                           f"TN eServices ({services['tn_eservices']['url']}): {', '.join(services['tn_eservices']['services'])}\n" +
                           f"TNRERA ({services['rera_tn']['url']}): {', '.join(services['rera_tn']['services'])}")
    
    # Check for patta/chitta queries
    if any(word in query_lower for word in ['patta', 'chitta', 'பட்டா', 'சிட்டா', 'land record']):
        context_parts.append("PATTA AND CHITTA:\n" +
                           "Patta: Official document establishing land ownership, issued by Revenue Department. Contains owner name, survey number, land area.\n" +
                           "Chitta: Land classification record maintained by Revenue Department. Shows land type (wet/dry/residential/commercial).\n" +
                           "Both should match for valid property transaction.\n" +
                           "How to get: Visit Taluk office or apply online at eservices.tn.gov.in\n" +
                           "Processing time: 7-15 working days")
    
    # Check for EC queries
    if any(word in query_lower for word in ['encumbrance', ' ec ', 'ec?', 'பாரச்', 'barachh']):
        context_parts.append("ENCUMBRANCE CERTIFICATE (EC):\n" +
                           "What: Certificate proving property is free from legal/monetary liabilities.\n" +
                           "Shows complete transaction history of the property.\n" +
                           "Issued by Sub-Registrar office.\n" +
                           "How to get: Apply at Sub-Registrar office or online at tnreginet.gov.in\n" +
                           "Fee: Rs.100-500 depending on period\n" +
                           "Recommended period: 13-30 years\n" +
                           "Form 15: Shows encumbrances exist | Form 16: Nil encumbrance (clean)\n" +
                           "Processing time: 3-7 working days")
    
    # Check for guideline value queries
    if any(word in query_lower for word in ['guideline', 'guide value', 'circle rate', 'market value', 'valuation']):
        context_parts.append("GUIDELINE VALUE:\n" +
                           "What: Minimum property value set by TN Registration Department.\n" +
                           "Used as base for stamp duty and registration fee calculation.\n" +
                           "Rule: Cannot register below guideline value.\n" +
                           "If actual price is higher, stamp duty calculated on actual price.\n" +
                           "Check online: tnreginet.gov.in (select district, taluk, village, survey number)\n" +
                           "Updated periodically by government based on market conditions.")
    
    return "\n\n".join(context_parts) if context_parts else ""

