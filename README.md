# Compliance Sentinel

A document upload tool that detects sensitive/PII data, classifies risk levels, generates AI-powered compliance summaries, and enables RAG-based question answering over uploaded documents.

## Setup Instructions

### Local Development

```bash
git clone https://github.com/your-username/compliance-sentinel.git
cd compliance-sentinel
pip install -r requirements.txt
python -m spacy download en_core_web_sm
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
streamlit run app.py
```

### Docker

```bash
docker build -t compliance-sentinel .
docker run -p 8501:8501 -e GEMINI_API_KEY=your_key_here compliance-sentinel
```

### Environment Variables

| Variable | Description |
|---|---|
| `GEMINI_API_KEY` | Google Gemini API key (free tier works) |

## Architecture Overview

```
Upload ──▶ Extract ──▶ Detect PII ──▶ Score Risk ──▶ Redact
                                                        │
                              ┌──────────────────────────┤
                              ▼                          ▼
                     Embed & Store (Chroma)    Generate Summary (Gemini)
                              │                          │
                              ▼                          ▼
                     RAG Query Answer          Compliance Report
```

**Core Security Principle**: Raw PII never leaves the local process boundary. All text is redacted with `[REDACTED_*]` tags before being embedded into Chroma or sent to Gemini. The LLM only ever sees redacted text and aggregate counts.

### Why Redaction Before LLM/Vector Calls?

1. **Data minimization**: Only the minimum necessary information is shared with third-party APIs
2. **Compliance**: Aligns with GDPR/DPDPA data minimization principles
3. **No PII in embeddings**: Vector stores don't contain raw sensitive data
4. **Audit trail**: Redacted outputs are traceable and auditable

## AI/ML Approach

### Hybrid Rule-Based + LLM Design

| Layer | Technology | Why |
|---|---|---|
| **Structured PII** | Regex + Luhn/Verhoeff | Deterministic, auditable, zero false positives on formats like PAN/Aadhaar |
| **Unstructured entities** | spaCy NER | Catches names/orgs in free text that regex can't match |
| **Summarization** | Gemini 1.5 Flash | Generates actionable compliance insights from redacted content |
| **RAG generation** | Gemini + Chroma | Grounded Q&A that only answers from document context |

### Why Hybrid Beats Pure-LLM PII Detection

- **Determinism**: Regex on structured formats (PAN: `ABCDE1234F`) produces consistent, reproducible results — no hallucinated matches or missed detections
- **Audibility**: Every regex match includes exact character positions, enabling precise redaction and audit trails
- **Performance**: Regex runs in milliseconds; no API calls needed for detection
- **Cost**: Only Gemini calls for summary/RAG, not for every detection
- **LLM for what it's good at**: Natural language understanding, summarization, and grounded generation — not pattern matching on fixed formats

### Risk Scoring

Weighted scoring system:

| Category | Weight | Examples |
|---|---|---|
| High (5 pts) | Aadhaar, PAN, Credit Card, Bank Account, API Keys | Direct financial/identity risk |
| Medium (2 pts) | Phone, Employee ID | Contact/employment linkage |
| Low (1 pt) | Email, spaCy PERSON/ORG | Lower-risk identifiers |

Thresholds: 0-5 = Low, 6-20 = Medium, 21+ = High

## Challenges Faced

1. **False positives on generic 16-digit numbers**: Solved by adding Luhn checksum validation for credit cards and Verhoeff check for Aadhaar — reduces false positives on random digit sequences
2. **Scanned PDF OCR quality**: Added `pdf2image` + `pytesseract` fallback when `pypdf` extracts near-empty text; quality depends on scan resolution
3. **Chunk-boundary PII leakage**: PII split across chunk boundaries could miss detection. Mitigated by running detection on full document text before chunking, and using overlapping chunks for RAG retrieval
4. **spaCy model availability**: `en_core_web_sm` may not be installed in all environments — gracefully degrades if unavailable

## Future Improvements

- **Microsoft Presidio integration**: Production-grade PII detection with configurable recognizers
- **Per-tenant authentication**: Multi-user support with document isolation
- **PostgreSQL persistence**: Replace JSONL audit log with queryable database
- **Streaming responses**: Real-time token streaming for Gemini summaries
- **Multi-language PII patterns**: Support for non-English document formats
- **Batch processing**: Upload and scan multiple documents simultaneously
- **Custom regex patterns**: User-defined detection rules via UI

## Project Structure

```
compliance-sentinel/
├── app.py                  # Streamlit entrypoint — tabs: Upload, Summary, Chat, Audit Log
├── core/
│   ├── extractor.py        # PDF/TXT/CSV → raw text, OCR fallback for scanned PDFs
│   ├── pii_detector.py     # Regex + spaCy patterns, returns findings dict
│   ├── risk_engine.py      # Weighted scoring → Low/Medium/High
│   ├── redactor.py         # Raw text → redacted text with [REDACTED_*] tags
│   ├── summarizer.py       # Gemini call → compliance summary + remediation
│   ├── rag_engine.py       # Chunk, embed, store in Chroma, query
│   └── audit.py            # Append-only JSONL audit trail
├── data/                   # Chroma persistence + audit.jsonl
├── requirements.txt
├── Dockerfile
├── .env.example
├── .gitignore
└── README.md
```
