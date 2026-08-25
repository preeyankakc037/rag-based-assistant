# University RAG-Based Assistant

A retrieval-augmented generation (RAG) assistant for helping university students navigate academic regulations, assessment requirements, progression rules, and related policies.

The project uses **React** for the frontend and **FastAPI** for the backend. The RAG pipeline is designed to retrieve relevant passages from university regulations before generating an answer, with a focus on **accuracy, source citations, conversational context, and transparent refusal when the answer is not supported by the source material**.

> **Current status:** Project scaffolding and React frontend are set up. The RAG ingestion, retrieval, citation, streaming, and conversational features are being implemented incrementally.

---

## 🎯 Project Goal

Build a practical university policy assistant that allows a student to ask questions such as:

- What are the requirements for progressing to the next stage?
- What happens if a stage is incomplete?
- What are the rules for assessment components?
- How are module grades calculated?
- What are the requirements for completing a programme?
- What happens when an assessment component is failed?

The assistant should answer from the indexed regulations rather than relying on general model knowledge.

---

## 📚 Knowledge Source

The initial RAG knowledge base uses:

**University College Dublin — Academic Regulations 2025–2026**

- Document type: University academic regulations
- Document length: 84 pages
- Version: 2.2
- Approved by Academic Council: 30 April 2025
- Academic Council Executive Committee: 28 May 2025

The regulations cover areas including governance, university awards, academic calendar and programme structures, assessment/grading/feedback, module completion and remediation, programme progression and completion, research degrees, professional doctorates, and MD regulations.

> The source PDF is intentionally kept out of Git version control. See `.gitignore` for the local data policy.

---

## 🏗️ Architecture

```text
┌───────────────────────────────┐
│          React Frontend       │
│                               │
│  Chat UI • PDF Upload • Chat  │
└───────────────┬───────────────┘
                │ HTTP / JSON
                ▼
┌───────────────────────────────┐
│          FastAPI Backend      │
│                               │
│  API • Upload • RAG Services  │
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│          RAG Pipeline         │
│                               │
│ PDF → Extraction → Chunking   │
│       → Embeddings            │
│       → Vector Search         │
│       → Relevant Context      │
│       → LLM Response          │
└───────────────────────────────┘
```

### Planned technology stack

| Layer | Technology |
|---|---|
| Frontend | React + Vite |
| Backend | FastAPI + Uvicorn |
| RAG orchestration | LangChain |
| LLM | Google Gemini |
| Vector store | FAISS |
| PDF extraction | PyPDFLoader, with improved extraction for complex PDFs |
| Configuration | Python `python-dotenv` |

---

## 🚀 Assignment Implementation

The implementation is being developed against the six assignment levels.

### Level 1 — Bring Your Own PDF

The application will accept a PDF through the web interface and ingest it without requiring the user to edit a filename in the source code.

**Target behaviour:**

```text
Upload PDF
    ↓
Extract text
    ↓
Split into chunks
    ↓
Create embeddings
    ↓
Store vectors
    ↓
Retrieve relevant chunks
    ↓
Generate grounded answer
```

The assistant should respond that it does not know when the requested information is not supported by the document.

### Level 2 — Handle Messy PDFs

The selected regulations contain structured material, including tables such as grade scales. The project will compare basic PDF extraction with a stronger extraction approach and test retrieval against information that appears in tables or other non-trivial page layouts.

### Level 3 — Streaming

Responses will be streamed from the backend to the frontend so that users see the answer progressively instead of waiting for the complete response.

### Level 4 — Citations

Retrieved chunks will retain source metadata so answers can include the originating document and relevant page number(s).

Example:

```text
Sources
- Academic Regulations 2025–2026, p. 32
```

### Level 5 — Conversational RAG

Conversation history will be used to resolve follow-up questions and implicit references.

Example:

```text
User: What are the requirements for progressing to the next stage?
Assistant: ...

User: What happens if I do not meet them?
Assistant: ...
```

### Level 6 — Ship It as a Real App

The notebook implementation is being converted into a proper application with:

- React frontend
- FastAPI backend
- API-based RAG interaction
- Browser-based chat interface

---

## 📁 Project Structure

```text
university-rag-based-assistant/
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   └── rag/
│   │       └── pipeline.py
│   ├── requirements.txt
│   └── venv/
│
├── frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── package-lock.json
│
├── data/
│   └── .gitkeep
│
├── .gitignore
└── README.md
```

> Local virtual environments, generated vector stores, secrets, and PDF files are excluded from Git.

---

## ⚙️ Local Development Setup

### 1. Clone the repository

```bash
git clone <repository-url>
cd university-rag-based-assistant
```

### 2. Backend setup

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Create `backend/.env`:

```env
GEMINI_API_KEY=your_api_key_here
```

Run FastAPI:

```powershell
uvicorn app.main:app --reload
```

API documentation will be available at:

```text
http://127.0.0.1:8000/docs
```

### 3. Frontend setup

Open a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

The Vite development server will provide the local React application URL shown in the terminal.

---

## 🔐 Environment Variables

Secrets must never be committed to the repository.

```env
GEMINI_API_KEY=your_api_key_here
```

The `.gitignore` file excludes `.env` files from version control.

---

## 🔌 Planned API

### `POST /ask`

Accepts a user question and returns a grounded answer generated from retrieved document context.

Planned response fields:

```json
{
  "answer": "...",
  "sources": [
    {
      "document": "Academic Regulations 2025-2026.pdf",
      "page": 32
    }
  ]
}
```

### Document ingestion

The backend will also expose an upload/ingestion route so the PDF can be supplied through the application rather than hard-coded in the source code.

---

## 🧪 Evaluation & Testing

Testing will focus on retrieval quality rather than UI complexity.

### In-document questions

Questions whose answers are explicitly contained in the regulations should return grounded answers.

### Out-of-scope questions

Questions unrelated to the source should trigger an appropriate uncertainty response rather than hallucinated policy.

### Table retrieval

Structured information such as grade-scale tables will be used to evaluate extraction and retrieval quality.

### Follow-up questions

The assistant will be tested on pronouns and implicit references to verify conversational retrieval.

### Source validation

Every grounded response should expose the document and page metadata associated with the retrieved context.

---

## 🧭 Development Approach

The repository is intentionally developed through small, meaningful Git commits so that each commit represents a real implementation milestone.

Example progression:

```text
Set up React frontend and project structure
        ↓
Implement PDF ingestion
        ↓
Implement chunking and metadata
        ↓
Add embeddings and FAISS retrieval
        ↓
Implement RAG question answering
        ↓
Handle out-of-scope questions
        ↓
Improve extraction for tables
        ↓
Implement streaming
        ↓
Add citations
        ↓
Implement conversational history
        ↓
Expose RAG through FastAPI
        ↓
Connect React frontend
        ↓
Testing and documentation
```

---

## ⚠️ Responsible Use

This application is an educational RAG project and **is not a replacement for official university advice or policy interpretation**.

Users should verify important decisions against the latest official university regulations and relevant programme-specific documentation. The assistant should surface its source pages so that users can inspect the underlying regulation directly.

---

## 📌 Why RAG?

University regulations are often lengthy, highly structured, and difficult to navigate through keyword search alone. RAG is useful here because the assistant can retrieve the most relevant passages before generating an answer, reducing the need for the model to rely on unsupported general knowledge and making the response traceable to the source document.

The initial regulations document explicitly covers assessment, grading, progression, completion, and graduation, making it a practical domain for evaluating retrieval quality. 

---

## 👨‍💻 Project Status

**In development**

The current milestone is the transition from project setup to the first end-to-end PDF ingestion and retrieval implementation.

---

## 📄 Source Document

University College Dublin. *Academic Regulations 2025–2026*. Version 2.2.
