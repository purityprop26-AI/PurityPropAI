# 🏠 PurityProp AI — Model Training Report
## Tamil Nadu Real Estate AI Assistant
### Production-Level Step-by-Step Implementation Guide

---

## 📋 Table of Contents

1. [Project Architecture Analysis](#1-project-architecture-analysis)
2. [Current AI Pipeline Overview](#2-current-ai-pipeline-overview)
3. [Phase 1: Data Collection & Preparation](#3-phase-1-data-collection--preparation)
4. [Phase 2: Knowledge Base Enhancement (RAG)](#4-phase-2-knowledge-base-enhancement-rag)
5. [Phase 3: Fine-Tuning the LLM](#5-phase-3-fine-tuning-the-llm)
6. [Phase 4: Domain Validator ML Upgrade](#6-phase-4-domain-validator-ml-upgrade)
7. [Phase 5: Evaluation & Testing](#7-phase-5-evaluation--testing)
8. [Phase 6: Production Deployment](#8-phase-6-production-deployment)
9. [Phase 7: Monitoring & Continuous Improvement](#9-phase-7-monitoring--continuous-improvement)
10. [Hardware & Cost Estimates](#10-hardware--cost-estimates)
11. [Complete File Structure](#11-complete-file-structure)
12. [Timeline & Milestones](#12-timeline--milestones)

---

## 1. Project Architecture Analysis

### Current Stack
| Component       | Technology                        |
|----------------|-----------------------------------|
| **Backend**    | FastAPI (Python)                  |
| **LLM Engine** | Llama 3.1 8B via Groq API        |
| **Database**   | MongoDB (Motor + Odmantic ODM)   |
| **Frontend**   | React 18 + Vite                  |
| **Auth**       | JWT (python-jose + passlib)      |
| **Deployment** | Render (Backend) + Vercel (Frontend) |

### Current AI Components
| File                      | Role                                       |
|--------------------------|---------------------------------------------|
| `llm_service.py`         | Groq API calls, prompt engineering, response generation |
| `domain_validator.py`    | Keyword-based query classification (real estate vs. non-real estate) |
| `tn_knowledge_base.py`   | Static dictionary of TN real estate knowledge |

### What "Training" Means for This Project

Your project uses **Llama 3.1 8B** via the **Groq API** — a pre-trained foundation model. There is **no custom model training from scratch**. Instead, "training" involves:

1. **Fine-Tuning** — Adapting Llama 3.1 on domain-specific real estate data
2. **RAG (Retrieval-Augmented Generation)** — Feeding relevant knowledge at inference time
3. **Prompt Engineering** — Crafting system prompts for accurate, domain-restricted responses
4. **Domain Classifier Training** — Upgrading keyword matching → ML-based intent classifier

---

## 2. Current AI Pipeline Overview

```
User Query
    │
    ▼
┌─────────────────────┐
│  Domain Validator    │ → Keyword matching (is_real_estate_query)
│  domain_validator.py │ → Language detection (detect_language)
└────────┬────────────┘
         │ Valid query
         ▼
┌─────────────────────┐
│  Knowledge Base      │ → Static dict lookup (get_knowledge_context)
│  tn_knowledge_base.py│ → Returns relevant TN real estate facts
└────────┬────────────┘
         │ Context injected
         ▼
┌─────────────────────┐
│  LLM Service         │ → System prompt + context + history → Groq API
│  llm_service.py      │ → Llama 3.1 8B generates response
└────────┬────────────┘
         │
         ▼
    AI Response (Tamil / Tanglish / English)
```

---

## 3. Phase 1: Data Collection & Preparation

### Step 1.1: Identify Data Sources

| Source | Type | Purpose |
|--------|------|---------|
| TNRERA (rera.tn.gov.in) | Government data | Project registrations, developer info |
| Tamil Nadu Registration Dept | Legal data | Stamp duty rates, document requirements |
| DTCP / CMDA notifications | Regulatory data | Layout approvals, zoning rules |
| Real estate Q&A forums | User queries | Common questions people ask |
| Legal case databases | Case law | Property dispute patterns |
| Bank websites (SBI, HDFC, etc.) | Financial data | Loan eligibility, interest rates |

### Step 1.2: Create Training Dataset

```python
# scripts/data_collection/create_dataset.py

import json

def create_training_pairs():
    """
    Create instruction-response pairs for fine-tuning.
    Target: 5,000-10,000 high-quality pairs.
    """
    dataset = []

    # Category 1: Property Registration
    dataset.append({
        "instruction": "What is the process for property registration in Tamil Nadu?",
        "input": "",
        "output": (
            "The property registration process in Tamil Nadu involves these steps:\n\n"
            "1. **Document Verification** — Verify title deed, EC (last 13-30 years), "
            "tax receipts\n"
            "2. **Sale Agreement** — Draft on ₹100 stamp paper with terms\n"
            "3. **Stamp Duty Payment** — 7% of property value (5% for women)\n"
            "4. **Registration Fee** — 1% of property value (max ₹1 lakh)\n"
            "5. **Sub-Registrar Visit** — Both buyer and seller with 2 witnesses\n"
            "6. **Biometric Verification** — Fingerprint and photo capture\n"
            "7. **Document Submission** — All originals + copies\n"
            "8. **Mutation** — Apply for property tax name change\n\n"
            "⚠️ This is informational guidance only, not legal advice."
        ),
        "language": "english",
        "category": "registration"
    })

    # Category 2: Tamil Script Q&A
    dataset.append({
        "instruction": "சென்னையில் வீடு வாங்க என்ன ஆவணங்கள் தேவை?",
        "input": "",
        "output": (
            "சென்னையில் வீடு வாங்க கீழ்கண்ட ஆவணங்கள் தேவை:\n\n"
            "**வாங்குபவர்:**\n"
            "• PAN கார்டு\n• ஆதார் கார்டு\n• முகவரி ஆதாரம்\n"
            "• பாஸ்போர்ட் சைஸ் புகைப்படங்கள்\n\n"
            "**விற்பவர்:**\n"
            "• அசல் விற்பனை ஆவணம்\n• EC (கடந்த 13-30 ஆண்டுகள்)\n"
            "• சொத்து வரி ரசீது\n\n"
            "⚠️ இது தகவல் வழிகாட்டுதல் மட்டுமே."
        ),
        "language": "tamil",
        "category": "documents"
    })

    # Category 3: Tanglish Q&A
    dataset.append({
        "instruction": "Chennai la veedu vaanga enna documents venum?",
        "input": "",
        "output": (
            "Chennai la veedu vaanga indha documents venum:\n\n"
            "**Buyer ku:**\n"
            "• PAN Card\n• Aadhaar Card\n• Address Proof\n"
            "• Passport size photos\n\n"
            "**Seller kitta irukka veanda docs:**\n"
            "• Original Sale Deed\n• EC (kadandha 13-30 varusham)\n"
            "• Property Tax Receipt\n\n"
            "⚠️ Idhu informational guidance mattum, legal advice illa."
        ),
        "language": "tanglish",
        "category": "documents"
    })

    return dataset
```

### Step 1.3: Data Preprocessing Pipeline

```python
# scripts/data_collection/preprocess.py

import re
import json
from typing import List, Dict

class DataPreprocessor:
    """Clean and format training data."""

    def __init__(self):
        self.min_output_length = 50
        self.max_output_length = 2000

    def clean_text(self, text: str) -> str:
        """Remove noise, normalize whitespace."""
        text = re.sub(r'\s+', ' ', text).strip()
        text = re.sub(r'[^\w\s\u0B80-\u0BFF.,!?₹%\-•\n:()]', '', text)
        return text

    def validate_pair(self, pair: Dict) -> bool:
        """Validate a training pair meets quality standards."""
        if not pair.get("instruction") or not pair.get("output"):
            return False
        if len(pair["output"]) < self.min_output_length:
            return False
        if pair.get("language") not in ["english", "tamil", "tanglish"]:
            return False
        return True

    def format_for_finetuning(self, pairs: List[Dict]) -> List[Dict]:
        """Convert to Alpaca/ChatML format for fine-tuning."""
        formatted = []
        for pair in pairs:
            if not self.validate_pair(pair):
                continue
            formatted.append({
                "messages": [
                    {"role": "system", "content": "You are a Tamil Nadu Real Estate AI Assistant."},
                    {"role": "user", "content": pair["instruction"]},
                    {"role": "assistant", "content": self.clean_text(pair["output"])}
                ]
            })
        return formatted

    def split_dataset(self, data: List[Dict], train_ratio=0.85, val_ratio=0.10):
        """Split into train/val/test sets."""
        import random
        random.shuffle(data)
        n = len(data)
        train_end = int(n * train_ratio)
        val_end = int(n * (train_ratio + val_ratio))
        return {
            "train": data[:train_end],
            "val": data[train_end:val_end],
            "test": data[val_end:]
        }
```

**Target Dataset Size:**
| Language | Pairs | Category Coverage |
|----------|-------|-------------------|
| English  | 3,000 | Registration, Documents, Loans, Legal, REDs |
| Tamil    | 2,000 | Same categories in Tamil script |
| Tanglish | 2,000 | Same categories in Tanglish |
| **Total**| **7,000** | — |

---

## 4. Phase 2: Knowledge Base Enhancement (RAG)

### Step 2.1: Install Vector Database

```bash
# Add to requirements.txt
pip install chromadb==0.4.22 sentence-transformers==2.3.1 langchain==0.1.4
```

### Step 2.2: Create Vector Store Service

```python
# backend/app/services/vector_store.py

import chromadb
from sentence_transformers import SentenceTransformer
from typing import List, Dict

class VectorStoreService:
    """RAG-based knowledge retrieval using ChromaDB."""

    def __init__(self):
        self.client = chromadb.PersistentClient(path="./chroma_db")
        self.collection = self.client.get_or_create_collection(
            name="tn_real_estate",
            metadata={"hnsw:space": "cosine"}
        )
        # Multilingual model for Tamil + English
        self.embedder = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
        print("✅ Vector Store initialized")

    def add_documents(self, documents: List[Dict]):
        """Index documents into ChromaDB."""
        texts = [doc["content"] for doc in documents]
        embeddings = self.embedder.encode(texts).tolist()
        ids = [doc["id"] for doc in documents]
        metadatas = [{"category": doc.get("category", "general"),
                      "language": doc.get("language", "english")}
                     for doc in documents]

        self.collection.add(
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
            ids=ids
        )

    def search(self, query: str, n_results: int = 3, language: str = None) -> List[str]:
        """Retrieve relevant documents for a query."""
        query_embedding = self.embedder.encode([query]).tolist()
        where_filter = {"language": language} if language else None

        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=n_results,
            where=where_filter
        )
        return results["documents"][0] if results["documents"] else []

vector_store = VectorStoreService()
```

### Step 2.3: Populate the Vector Store

```python
# scripts/populate_vector_store.py

from app.services.vector_store import vector_store
from app.services.tn_knowledge_base import TN_KNOWLEDGE_BASE
import json

def populate():
    """Convert static knowledge base → vector embeddings."""
    documents = []
    doc_id = 0

    # Flatten nested knowledge base into documents
    for category, content in TN_KNOWLEDGE_BASE.items():
        if isinstance(content, dict):
            for sub_key, sub_value in content.items():
                doc_id += 1
                text = f"{category} - {sub_key}: {json.dumps(sub_value, ensure_ascii=False)}"
                documents.append({
                    "id": f"kb_{doc_id}",
                    "content": text,
                    "category": category,
                    "language": "english"
                })
        elif isinstance(content, list):
            doc_id += 1
            text = f"{category}: " + " | ".join(content)
            documents.append({
                "id": f"kb_{doc_id}",
                "content": text,
                "category": category,
                "language": "english"
            })

    vector_store.add_documents(documents)
    print(f"✅ Indexed {len(documents)} documents into ChromaDB")

if __name__ == "__main__":
    populate()
```

### Step 2.4: Update LLM Service to Use RAG

```python
# In llm_service.py — update generate_response():

from app.services.vector_store import vector_store

# Replace static knowledge lookup:
# OLD: context = get_knowledge_context(user_message.lower())
# NEW:
rag_results = vector_store.search(user_message, n_results=3, language=language)
context = "\n\n".join(rag_results) if rag_results else ""
```

---

## 5. Phase 3: Fine-Tuning the LLM

### Option A: Fine-Tune via Groq Partner (Recommended for Production)

Groq supports fine-tuned models. Use their partner platforms:

```bash
# Step 1: Export dataset in JSONL format
python scripts/export_training_data.py --format jsonl --output training_data.jsonl

# Step 2: Upload to fine-tuning platform (Together AI / Anyscale)
# Together AI example:
pip install together
together files upload training_data.jsonl
together fine-tuning create \
  --training-file file-xxxxx \
  --model meta-llama/Meta-Llama-3.1-8B-Instruct \
  --n-epochs 3 \
  --learning-rate 1e-5 \
  --batch-size 4

# Step 3: Update config.py with fine-tuned model ID
# llm_model = "your-org/tn-real-estate-llama-3.1-8b-ft"
```

### Option B: Local Fine-Tuning with QLoRA (Budget-Friendly)

```python
# scripts/finetune/train_qlora.py

from transformers import (
    AutoModelForCausalLM, AutoTokenizer,
    TrainingArguments, BitsAndBytesConfig
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import SFTTrainer
from datasets import load_dataset
import torch

def finetune():
    # 1. Quantization Config (4-bit for RTX 3050 / 4GB VRAM)
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )

    # 2. Load Base Model
    model_name = "meta-llama/Meta-Llama-3.1-8B-Instruct"
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
    )
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    tokenizer.pad_token = tokenizer.eos_token

    # 3. LoRA Configuration
    lora_config = LoraConfig(
        r=16,                    # Rank
        lora_alpha=32,           # Alpha scaling
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )

    model = prepare_model_for_kbit_training(model)
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    # Expected: ~0.5% of total params are trainable

    # 4. Load Dataset
    dataset = load_dataset("json", data_files={
        "train": "data/train.jsonl",
        "validation": "data/val.jsonl"
    })

    # 5. Training Arguments
    training_args = TrainingArguments(
        output_dir="./models/tn-realestate-llama",
        num_train_epochs=3,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        learning_rate=2e-4,
        weight_decay=0.01,
        warmup_steps=100,
        logging_steps=25,
        save_steps=500,
        eval_strategy="steps",
        eval_steps=250,
        fp16=True,
        optim="paged_adamw_32bit",
        lr_scheduler_type="cosine",
        report_to="none",
    )

    # 6. Train
    trainer = SFTTrainer(
        model=model,
        train_dataset=dataset["train"],
        eval_dataset=dataset["validation"],
        args=training_args,
        tokenizer=tokenizer,
        max_seq_length=1024,
    )

    trainer.train()

    # 7. Save
    trainer.model.save_pretrained("./models/tn-realestate-llama-final")
    tokenizer.save_pretrained("./models/tn-realestate-llama-final")
    print("✅ Fine-tuning complete!")

if __name__ == "__main__":
    finetune()
```

### Fine-Tuning Hyperparameters Summary

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Epochs | 3 | Prevents overfitting on small dataset |
| Learning Rate | 2e-4 | Standard for QLoRA |
| Batch Size | 2 (×4 grad accum = 8 effective) | Fits in 4-8GB VRAM |
| LoRA Rank (r) | 16 | Good balance of quality vs. compute |
| LoRA Alpha | 32 | 2× rank is standard |
| Max Seq Length | 1024 | Matches current `llm_max_tokens` |
| Quantization | 4-bit NF4 | Enables training on consumer GPUs |

---

## 6. Phase 4: Domain Validator ML Upgrade

### Step 4.1: Replace Keyword Matching with ML Classifier

```python
# scripts/train_classifier/train_intent_classifier.py

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import cross_val_score
import joblib
import json

def train_domain_classifier():
    """Train a TF-IDF + Logistic Regression classifier."""

    # Load labeled data
    with open("data/domain_labels.json") as f:
        data = json.load(f)

    texts = [item["text"] for item in data]
    labels = [item["is_real_estate"] for item in data]

    # Build pipeline
    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(
            max_features=5000,
            ngram_range=(1, 3),
            analyzer="char_wb",   # Character n-grams for Tamil support
            sublinear_tf=True
        )),
        ("clf", LogisticRegression(
            C=1.0,
            max_iter=1000,
            class_weight="balanced"
        ))
    ])

    # Cross-validate
    scores = cross_val_score(pipeline, texts, labels, cv=5, scoring="f1")
    print(f"F1 Score: {scores.mean():.4f} (+/- {scores.std():.4f})")

    # Train on full data
    pipeline.fit(texts, labels)

    # Save model
    joblib.dump(pipeline, "models/domain_classifier.joblib")
    print("✅ Domain classifier saved!")

if __name__ == "__main__":
    train_domain_classifier()
```

### Step 4.2: Update Domain Validator

```python
# Updated backend/app/services/domain_validator.py (add ML fallback)

import joblib
import os

# Load ML classifier if available
_classifier = None
_classifier_path = os.path.join(os.path.dirname(__file__), "../../models/domain_classifier.joblib")
if os.path.exists(_classifier_path):
    _classifier = joblib.load(_classifier_path)
    print("✅ ML Domain Classifier loaded")

def is_real_estate_query(query: str):
    # Try ML classifier first
    if _classifier is not None:
        prediction = _classifier.predict([query])[0]
        confidence = max(_classifier.predict_proba([query])[0])
        if confidence > 0.85:
            return (bool(prediction), "ML classifier")

    # Fallback to keyword matching (existing logic)
    # ... existing keyword-based code ...
```

---

## 7. Phase 5: Evaluation & Testing

### Step 5.1: Create Evaluation Dataset

```python
# scripts/evaluate/eval_dataset.py

EVAL_CASES = [
    # True Positives (should accept)
    {"query": "How to register property in Chennai?", "expected": True, "lang": "english"},
    {"query": "சென்னையில் stamp duty எவ்வளவு?", "expected": True, "lang": "tamil"},
    {"query": "Veedu vaanga loan eligibility enna?", "expected": True, "lang": "tanglish"},

    # True Negatives (should reject)
    {"query": "Write me a poem about love", "expected": False, "lang": "english"},
    {"query": "What is the weather today?", "expected": False, "lang": "english"},
    {"query": "Cinema ticket booking epdi?", "expected": False, "lang": "tanglish"},

    # Edge Cases
    {"query": "Is investing in gold better than property?", "expected": True, "lang": "english"},
    {"query": "How to convert agricultural land?", "expected": True, "lang": "english"},
]
```

### Step 5.2: Automated Evaluation Script

```python
# scripts/evaluate/run_eval.py

import json
from app.services.domain_validator import is_real_estate_query, detect_language
from app.services.llm_service import llm_service

def evaluate_system():
    results = {"domain_accuracy": 0, "language_accuracy": 0, "response_quality": []}
    total = len(EVAL_CASES)

    for case in EVAL_CASES:
        # Test domain validator
        is_valid, _ = is_real_estate_query(case["query"])
        if is_valid == case["expected"]:
            results["domain_accuracy"] += 1

        # Test language detection
        detected = detect_language(case["query"])
        if detected == case["lang"]:
            results["language_accuracy"] += 1

    results["domain_accuracy"] = results["domain_accuracy"] / total * 100
    results["language_accuracy"] = results["language_accuracy"] / total * 100

    print(f"Domain Accuracy:   {results['domain_accuracy']:.1f}%")
    print(f"Language Accuracy: {results['language_accuracy']:.1f}%")
    return results
```

### Key Metrics to Track

| Metric | Target | Measurement |
|--------|--------|-------------|
| Domain Classification F1 | > 95% | Precision + Recall on eval set |
| Language Detection Accuracy | > 98% | Correct language identification |
| Response Relevance | > 90% | Human evaluation (1-5 scale) |
| Response Factual Accuracy | > 95% | Verified against TN govt sources |
| Latency (P95) | < 3 seconds | End-to-end response time |
| Hallucination Rate | < 5% | Fabricated facts / total responses |

---

## 8. Phase 6: Production Deployment

### Step 6.1: Updated Backend Architecture

```
backend/
├── app/
│   ├── services/
│   │   ├── domain_validator.py   ← ML classifier + keyword fallback
│   │   ├── llm_service.py        ← RAG-enhanced + fine-tuned model
│   │   ├── tn_knowledge_base.py  ← Static fallback
│   │   └── vector_store.py       ← NEW: ChromaDB RAG service
│   ├── config.py
│   ├── database.py
│   ├── models.py
│   ├── routes.py
│   └── schemas.py
├── models/                        ← NEW: Trained model artifacts
│   ├── domain_classifier.joblib
│   └── tn-realestate-llama-final/ (if self-hosted)
├── chroma_db/                     ← NEW: Vector store data
├── data/                          ← NEW: Training datasets
│   ├── train.jsonl
│   ├── val.jsonl
│   ├── test.jsonl
│   └── domain_labels.json
├── scripts/                       ← NEW: Training scripts
│   ├── data_collection/
│   ├── finetune/
│   ├── evaluate/
│   └── populate_vector_store.py
└── requirements.txt               ← Updated with ML deps
```

### Step 6.2: Updated Requirements

```txt
# Add to requirements.txt
chromadb==0.4.22
sentence-transformers==2.3.1
scikit-learn==1.4.0
joblib==1.3.2
torch==2.1.2             # Only for local fine-tuning
transformers==4.37.2     # Only for local fine-tuning
peft==0.7.1              # Only for local fine-tuning
trl==0.7.10              # Only for local fine-tuning
bitsandbytes==0.42.0     # Only for local fine-tuning
```

### Step 6.3: Production Deployment Checklist

```bash
# 1. Train domain classifier
python scripts/train_classifier/train_intent_classifier.py

# 2. Populate vector store
python scripts/populate_vector_store.py

# 3. Fine-tune model (if using Option B)
python scripts/finetune/train_qlora.py

# 4. Run evaluation
python scripts/evaluate/run_eval.py

# 5. Deploy to Render
git add .
git commit -m "feat: ML-enhanced AI pipeline with RAG + fine-tuned model"
git push origin main
```

---

## 9. Phase 7: Monitoring & Continuous Improvement

### Step 7.1: Add Logging & Feedback Collection

```python
# backend/app/services/monitoring.py

import json
from datetime import datetime

class AIMonitor:
    """Track model performance in production."""

    def log_interaction(self, query, response, language, latency_ms, user_feedback=None):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "query": query,
            "response_length": len(response),
            "language": language,
            "latency_ms": latency_ms,
            "feedback": user_feedback  # thumbs up/down from UI
        }
        # Store in MongoDB for analysis
        return log_entry

    def get_metrics(self, days=7):
        """Aggregate performance metrics."""
        # Query MongoDB for recent interactions
        # Calculate: avg latency, feedback scores, language distribution
        pass
```

### Continuous Improvement Cycle

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Collect     │────▶│  Analyze     │────▶│  Retrain    │
│  User Logs   │     │  Failures    │     │  Model      │
└──────────────┘     └──────────────┘     └──────┬──────┘
       ▲                                         │
       └─────────────────────────────────────────┘
                   Deploy & Monitor
```

**Monthly Improvement Tasks:**
1. Review low-rated responses → Add to training data
2. Identify new real estate terms → Update domain classifier
3. Check for regulatory changes → Update knowledge base
4. A/B test prompt variations → Optimize system prompt

---

## 10. Hardware & Cost Estimates

### Option A: Cloud Fine-Tuning (Recommended)

| Service | Cost | What You Get |
|---------|------|--------------|
| Together AI Fine-Tuning | ~$5-15 per run | Fine-tuned Llama 3.1 8B hosted |
| Groq API (Inference) | ~$0.05/1M tokens | Ultra-fast inference, current setup |
| Render (Backend) | Free-$25/month | Current deployment |
| MongoDB Atlas | Free-$10/month | Current database |
| **Total Monthly** | **~$35-50/month** | — |

### Option B: Local Fine-Tuning

| Hardware | Minimum | Recommended |
|----------|---------|-------------|
| GPU VRAM | 4GB (RTX 3050) | 8GB+ (RTX 3060/4060) |
| RAM | 16GB | 32GB |
| Storage | 50GB free | 100GB SSD |
| Training Time | ~8-12 hours | ~3-5 hours |

---

## 11. Complete File Structure

```
Real Estate/
├── backend/
│   ├── app/
│   │   ├── services/
│   │   │   ├── domain_validator.py    # ML + keyword hybrid classifier
│   │   │   ├── llm_service.py         # RAG-enhanced LLM service
│   │   │   ├── tn_knowledge_base.py   # Static knowledge fallback
│   │   │   ├── vector_store.py        # ★ NEW: ChromaDB RAG service
│   │   │   └── monitoring.py          # ★ NEW: AI monitoring service
│   │   ├── config.py / database.py / models.py / routes.py / schemas.py
│   ├── models/                        # ★ NEW: Trained artifacts
│   │   ├── domain_classifier.joblib
│   │   └── tn-realestate-llama-final/
│   ├── chroma_db/                     # ★ NEW: Vector embeddings
│   ├── data/                          # ★ NEW: Training datasets
│   │   ├── train.jsonl / val.jsonl / test.jsonl
│   │   └── domain_labels.json
│   ├── scripts/                       # ★ NEW: Training pipeline
│   │   ├── data_collection/create_dataset.py
│   │   ├── data_collection/preprocess.py
│   │   ├── finetune/train_qlora.py
│   │   ├── train_classifier/train_intent_classifier.py
│   │   ├── evaluate/run_eval.py
│   │   └── populate_vector_store.py
│   ├── requirements.txt / main.py / .env
├── frontend/ (unchanged)
├── MODEL_TRAINING_REPORT.md           # ★ THIS FILE
└── README.md
```

---

## 12. Timeline & Milestones

| Week | Phase | Deliverable | Status |
|------|-------|-------------|--------|
| Week 1-2 | Data Collection | 7,000+ Q&A pairs across 3 languages | 🔲 |
| Week 3 | RAG Setup | ChromaDB + vector store + multilingual embeddings | 🔲 |
| Week 4 | Domain Classifier | ML-based intent classifier (F1 > 95%) | 🔲 |
| Week 5-6 | Fine-Tuning | QLoRA fine-tuned Llama 3.1 8B | 🔲 |
| Week 7 | Evaluation | Full test suite + metrics dashboard | 🔲 |
| Week 8 | Production Deploy | Deployed + monitoring active | 🔲 |
| Ongoing | Improvement | Monthly retraining cycle | 🔲 |

---

## 🎯 Summary: What to Train & Why

| Component | Training Method | Why |
|-----------|----------------|-----|
| **Domain Classifier** | TF-IDF + Logistic Regression | Replace brittle keyword matching with ML |
| **Knowledge Retrieval** | RAG with ChromaDB | Dynamic, semantic search instead of static dict |
| **LLM (Llama 3.1 8B)** | QLoRA Fine-Tuning | Teach TN-specific knowledge + language patterns |
| **Language Detector** | Existing regex (keep) | Already effective for Tamil/Tanglish/English |
| **System Prompts** | Iterative prompt engineering | Continuous optimization based on user feedback |

---

> **Note:** This project does NOT train a model from scratch. It leverages a pre-trained Llama 3.1 8B foundation model and enhances it through fine-tuning, RAG, and ML classification for production-grade performance in the Tamil Nadu real estate domain.

---

*Generated: February 23, 2026*
*Project: PurityProp AI — Tamil Nadu Real Estate AI Assistant*
