# Compliance Sentinel

A security-first, production-ready Compliance Assistant RAG application. It scans uploaded documents (PDFs, CSVs, TXT) to identify and redact sensitive Personally Identifiable Information (PII) using a hybrid Regex + Named Entity Recognition (NER) pipeline, calculates weighted compliance risk scores, generates structured compliance reports, and enables secure, isolated RAG-based chat dialogs with memory context.

---

## 🔗 Working Prototype Deployment Links
* **Frontend UI (Vercel):** [https://compliance-assistant-rag.vercel.app](https://compliance-assistant-rag.vercel.app)
* **Backend API (Render):** [https://compliance-assistant-rag.onrender.com](https://compliance-assistant-rag.onrender.com)
* **Database (Supabase):** [https://supabase.com](https://supabase.com)

---

## 🛠️ Setup Instructions

### 1. Cloud Infrastructure Configuration (Production)
This project uses **Supabase** for database hosting, **Render** for backend API services, and **Vercel** for the Vue 3 frontend application.

#### A. Database (Supabase)
1. Register a project on [Supabase](https://supabase.com).
2. Go to **Project Settings** -> **Database** and copy the **URI Connection String** under the **Connection Pooler** section (set mode to **Transaction** for IPv4 support on Render).
3. The string format: `postgresql://postgres.[proj-id]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres`.

#### B. Backend API (Render)
1. Register a new **Web Service** on [Render](https://render.com) and link your GitHub repository.
2. Select runtime **Docker** (it will build automatically via the multi-stage `Dockerfile`).
3. Add the following **Environment Variables**:
   * `DATABASE_URL`: *(Your Supabase connection string)*
   * `GEMINI_API_KEY`: *(Your Google Gemini API Key)*
   * `JWT_SECRET_KEY`: *(A random 32-character string)*

#### C. Frontend UI (Vercel)
1. Import your repository into [Vercel](https://vercel.com).
2. Configure **Root Directory** as `frontend`.
3. Add the **Environment Variable**:
   * `VITE_API_BASE`: `https://[your-render-app-name].onrender.com/api`
4. Deploy the project.

---

### 2. Docker Compose Setup (Local Execution)
To run the entire stack (FastAPI Backend, Vue 3 Frontend, and PostgreSQL Database) inside local containers:

1. Clone and navigate to the project directory:
   ```bash
   git clone https://github.com/your-username/compliance-sentinel.git
   cd compliance-sentinel/Rag_Task
   ```
2. Create a local `.env` file from the example:
   ```bash
   copy .env.example .env
   # Edit .env and set GEMINI_API_KEY
   ```
3. Run the containerized environment:
   ```bash
   docker-compose up --build -d
   ```
4. Access the web interface at **`http://localhost:8000`** (and database externally at `localhost:5433`).

---

### 3. Local Development Setup (Manual)

#### A. Backend Setup
1. Create and activate a python virtual environment:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate   # On Windows
   # source venv/bin/activate # On macOS/Linux
   ```
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   python -m spacy download en_core_web_sm
   ```
3. Create a `.env` file in the root:
   ```env
   GEMINI_API_KEY=your-gemini-key
   DATABASE_URL=postgresql://compliance:compliance@localhost:5433/compliance_assistant
   ```
4. Apply the Alembic database migrations:
   ```bash
   alembic upgrade head
   ```
5. Run the development server:
   ```bash
   uvicorn main:app --reload --port 8000
   ```

#### B. Frontend Setup
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install Node dependencies:
   ```bash
   npm install
   ```
3. Start the dev server:
   ```bash
   cmd.exe /c npm run dev   # On Windows (avoids PowerShell Script Execution errors)
   # npm run dev            # On macOS/Linux
   ```
4. Open the development UI at **`http://localhost:5173`**.

---

## 🏗️ Architecture Overview

```
[User Browser]
       │ (Vite / Vue 3 SPA on http://localhost:5173 or Vercel)
       ▼
 [FastAPI Server] (main.py / http://localhost:8000 or Render)
   ├── Auth Router ──▶ Users, Tokens & Sessions
   └── Document Router ──▶ Scan, Summary & RAG Query
         ├── text_extractor ──▶ pypdf / pdf2image + OCR (Tesseract)
         ├── PII_detector   ──▶ Regex (Aadhaar, Credit Card, PAN, etc.) + spaCy NER (Names, Orgs)
         ├── risk_classifier ──▶ Weighted Compliance Risk Scoring Engine
         ├── text_redactor  ──▶ Replaces sensitive items with secure placeholders
         ├── summarizer     ──▶ Generates structured reports via Gemini 1.5 Flash-lite
         └── RAG_engine     ──▶ Indexes / queries redacted chunks in ChromaDB
               │
               ▼
     [Database Layers]
       ├── PostgreSQL (Supabase / local container) ──▶ Persists Users, Chats, Audits, Document Metadata
       └── Chroma Vector DB (local disk / container) ──▶ Stores Vector Embeddings (Gemini Embeddings)
```

---

## 🧠 AI/ML Approach Used

### 1. Hybrid Rule-Based + Named Entity Recognition (NER) Pipeline
* **Deterministic Structured PII:** Regular expressions combined with algorithmic checksums (`Luhn Algorithm` for credit card validation and `Verhoeff Algorithm` for Aadhaar card validation) to guarantee zero false positives.
* **Context-Driven Unstructured Entities:** `spaCy`'s English pre-trained NER model (`en_core_web_sm`) is used to locate organizations and names that don't fit standard structured patterns.

### 2. Multi-Stage RAG Pipeline with Document Redaction
* **Redaction-Only Indexing:** To prevent leakage of PII to external models or third-party vector index storages, only **fully redacted text** (placeholders replacing PII) is chunked, converted to vector embeddings (using `models/gemini-embedding-001`), and stored in **ChromaDB**.
* **Dynamic Findings Ingestion:** Original PII scan findings and user/assistant chat histories are stored securely in the PostgreSQL database. On a user query, these findings and conversation history are dynamically injected into the LLM context. This allows the model to answer compliance-related questions securely, without indexing raw PII.
* **LLM Reasoning:** Google Gemini 1.5 Flash-lite serves as the core reasoning engine, generating compliance summaries, rolling chat summaries, and context-grounded RAG query answers.

### 3. Weighted Risk Scoring Engine
Risk scores are calculated dynamically based on detected findings:
* **High Risk (5 points):** Aadhaar numbers, PAN, Credit Cards, Bank Account numbers, API keys.
* **Medium Risk (2 points):** Phone numbers, Employee IDs.
* **Low Risk (1 point):** Email addresses, Person Names, Organization Names.
* **Risk Levels:** Low (Score 0-5), Medium (6-20), High (21+).

---

## ⚡ Challenges Faced & Solutions

1. **Alembic String Interpolation Failure:**
   * *Problem:* Database URLs containing special characters (like `%2C` or `%2B` in Supabase passwords) caused Alembic configuration parsing to fail with `ValueError: invalid interpolation syntax`.
   * *Solution:* Patched [alembic/env.py](file:///d:/RAG_Task/Rag_Task/alembic/env.py) to escape percent signs (`%` to `%%`) before they are written to the database configuration dictionary.
2. **PyJWT & python-jose Namespace Conflict:**
   * *Problem:* The code in `security.py` depended on direct imports and exceptions from the `pyjwt` library (e.g. `jwt.InvalidTokenError`), but only `python-jose` was declared in requirements, causing backend startup crashes.
   * *Solution:* Explicitly added `pyjwt>=2.8` to requirements and installed it to maintain standard JWT verify/decode error handlers.
3. **Render Network Unreachability:**
   * *Problem:* Render's build and runtime containers did not support outbound IPv6 traffic, causing direct database connections on port 5432 to time out with `Network is unreachable`.
   * *Solution:* Shifted the database connection URL to Supabase's transaction pooler URL (which resolves to an IPv4 address and runs on port 6543).
4. **Vite API Host Mismatches:**
   * *Problem:* Cross-Origin Resource Sharing (CORS) preflight requests threw errors or missed routes (405 Method Not Allowed) when Vercel hosted the frontend separate from Render.
   * *Solution:* Ensured `VITE_API_BASE` ends with `/api` to correctly map the endpoint routing path prefix of the FastAPI backend router.

---

## 🔮 Future Improvements
* **Advanced PII Masking:** Integrate Microsoft Presidio to detect advanced multilingual patterns and automate anonymization.
* **Real-time Streaming:** Wire WebSockets or Server-Sent Events (SSE) into `/api/documents/{doc_id}/query` to stream response tokens dynamically.
* **Hierarchical Document Chunking:** Implement parent-child chunking schemas to optimize vector search context matching.
* **Multi-Organization Tenant Boundaries:** Restrict user accounts within specific enterprise domains to prevent accidental resource leaks.
