# Compliance Sentinel

A security-first compliance assistant that detects sensitive/PII data, classifies risk levels, generates AI-powered compliance summaries, and enables secure RAG-based question answering over uploaded documents.

---

## Setup Instructions

### 1. Docker Compose (Recommended for Production/Validation)
This runs the entire stack (FastAPI Backend, Vue 3 Frontend, and PostgreSQL Database) in containers:

1. Clone the repository and navigate to the project directory:
   ```bash
   git clone https://github.com/your-username/compliance-sentinel.git
   cd compliance-sentinel/Rag_Task
   ```
2. Copy the `.env.example` file to `.env` and fill in your Google Gemini API Key:
   ```bash
   copy .env.example .env
   # Edit .env and set GEMINI_API_KEY
   ```
3. Start the application:
   ```bash
   docker compose up --build
   ```
4. Access the application at **`http://localhost:8000`**.

---

### 2. Local Development Setup

#### Backend Setup:
1. Navigate to the backend directory:
   ```bash
   cd Rag_Task
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate   # On Windows
   # source venv/bin/activate # On macOS/Linux
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   python -m spacy download en_core_web_sm
   ```
4. Set up your environment variables in `.env`:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   DATABASE_URL=postgresql://compliance:compliance@localhost:5432/compliance_assistant
   ```
5. Apply database migrations:
   ```bash
   alembic upgrade head
   ```
6. Start the backend server:
   ```bash
   uvicorn main:app --reload --port 8000
   ```

#### Frontend Setup:
1. Open a new terminal and navigate to the `frontend` folder:
   ```bash
   cd Rag_Task/frontend
   ```
2. Install Node dependencies:
   ```bash
   npm install
   ```
3. Start the frontend dev server:
   ```bash
   npm run dev
   ```
4. Open your browser to the URL output by Vite (usually **`http://localhost:5173`**).

---

## Architecture Overview

```
Upload ──▶ Extract Text ──▶ Detect PII ──▶ Risk Scoring ──▶ Redacted Text ──▶ Auto-Index (ChromaDB)
                                                                 │
                                                                 └─────▶ AI Summary (Gemini)
                                                                 │
                                                                 └─────▶ RAG Q&A (Gemini + Findings)
```

### Components:
* **Frontend**: Vue 3 SPA built with Vite and designed with custom dark-mode aesthetics, custom micro-animations, and interactive dashboards.
* **Backend**: FastAPI web server serving REST endpoints, managing database queries, and serving the compiled frontend bundle in production mode.
* **Database**: PostgreSQL (tracks Users, scanned Documents, Chat history, and Audit logs).
* **Vector DB**: ChromaDB (stores vector embeddings of redacted chunks).
* **LLM**: Google Gemini 1.5 Flash (used for summary generation and answering context-grounded queries).

---

## Core Security & Compliance Safeguards

### 1. Zero PII Leakage in Vector DB
To avoid exposing sensitive information to external APIs or vector indexes, ChromaDB **only indexes the redacted document text** (where sensitive values are masked with placeholders like `[REDACTED_Email]`).

### 2. Contextual Query Enhancement
When users ask questions about the document, the original PII findings (securely stored in your local PostgreSQL database) are dynamically injected into the LLM context. This allows the assistant to answer compliance questions (e.g. *"What sensitive data exists?"* or *"How many emails?"*) while keeping the permanent vector index completely redacted and compliant.

### 3. Automatic Ingestion
Documents are automatically chunked, embedded, and indexed into ChromaDB immediately upon uploading/scanning, ensuring no redundancy or manual indexing steps are required.

---

## AI/ML Approach

### Hybrid Rule-Based + LLM Design

| Layer | Technology | Why |
|---|---|---|
| **Structured PII** | Regex + Luhn/Verhoeff Check | Deterministic, zero false positives on standard ID patterns (Aadhaar, PAN, CC, Bank, IFSC) |
| **Unstructured entities** | spaCy NER | Extracts names and organizations in free-flowing text that regex cannot catch |
| **Summarization** | Gemini 1.5 Flash | Generates compliance/security reports from compliance scans |
| **RAG generation** | Gemini + ChromaDB | Answers questions securely using context-grounded RAG |

### Risk Scoring Model:
* **High Risk (5 pts)**: Aadhaar, PAN, Credit Card, Bank Account, API Keys (Immediate threat of identity/financial theft).
* **Medium Risk (2 pts)**: Phone Number, Employee ID.
* **Low Risk (1 pt)**: Email Address, Named Entities (PERSON/ORG).

**Risk Level Evaluation**: 
* **Low**: Score 0–5
* **Medium**: Score 6–20
* **High**: Score 21+

---

## Challenges Faced & Solutions

1. **Database Consistency on Faulty Schema Creations**: Identified duplicate index definitions (`ix_refresh_tokens_token_hash`) causing SQLAlchemy's `create_all()` to crash on clean databases. Resolved by removing index definitions in table arguments that were already handled by `index=True` configuration on the column attributes.
2. **False Positives on ID Numbers**: Generic 12 or 16-digit patterns trigger matches easily. Resolved by implementing Verhoeff check validation for Aadhaar numbers and Luhn algorithm checks for Credit Cards to verify checking digits.
3. **Chunk Boundary Truncation**: Text chunking can split a sensitive item across boundaries. Mitigated by scanning the complete, continuous text for PII *before* breaking it down into chunks for ChromaDB.

---

## Future Improvements

* **Microsoft Presidio Integration**: Extend raw PII detection using a production-ready framework.
* **Multi-tenant Document Isolation**: Encrypt and isolate data between separate user organization profiles.
* **Streaming Responses**: Stream response tokens in real-time to the chat screen for a smoother user experience.
* **Custom PII Rules**: Allow users to add custom regex patterns or blacklist terms via the dashboard settings.
