import json
import os
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from rag.loader import load_pdf
from rag.splitter import split_documents
from rag.embeddings import get_embeddings
from rag.vectorstore import create_vector_store
from rag.retriever import get_retriever
from rag.chain import create_rag_chain, create_streaming_rag_chain

load_dotenv()

if "GOOGLE_API_KEY" not in os.environ and "GEMINI_API_KEY" in os.environ:
    os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]

app = FastAPI(title="University RAG Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# ── Multi-document store ──────────────────────────────────────────────────────
# Maps filename → (rag_chain, streaming_rag_chain)
document_stores: Dict[str, tuple] = {}
active_document: Optional[str] = None


class ChatRequest(BaseModel):
    question: str
    history: List[Dict[str, Any]] = []


class ActivateRequest(BaseModel):
    document_name: str


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "loaded_documents": list(document_stores.keys()),
        "active_document": active_document,
    }


# ── Upload ────────────────────────────────────────────────────────────────────

@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    global active_document

    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    file_path = UPLOAD_DIR / file.filename
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        documents = load_pdf(str(file_path))
        chunks = split_documents(documents)
        embeddings = get_embeddings()
        vector_store = create_vector_store(chunks, embeddings)
        retriever = get_retriever(vector_store)

        # Cache both chain types under this filename
        document_stores[file.filename] = (
            create_rag_chain(retriever),
            create_streaming_rag_chain(retriever),
        )
        active_document = file.filename

        return {
            "message": f"Successfully processed {file.filename}. Ready for chat.",
            "document_name": file.filename,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Activate (switch active document without re-uploading) ───────────────────

@app.post("/activate")
async def activate_document(req: ActivateRequest):
    global active_document

    if req.document_name not in document_stores:
        raise HTTPException(
            status_code=404,
            detail=f"Document '{req.document_name}' is not loaded. Please re-upload it.",
        )

    active_document = req.document_name
    return {"message": f"Activated '{req.document_name}'.", "document_name": req.document_name}


@app.get("/loaded-documents")
def list_loaded_documents():
    return {"documents": list(document_stores.keys()), "active": active_document}


# ── Chat (non-streaming) ──────────────────────────────────────────────────────

@app.post("/chat")
async def chat(request: ChatRequest):
    if active_document is None or active_document not in document_stores:
        raise HTTPException(status_code=400, detail="No document is active. Please upload a PDF first.")

    rag_chain, _ = document_stores[active_document]

    try:
        response = rag_chain.invoke({"input": request.question, "history": request.history})
        context = response.get("context", [])
        sources = [
            {
                "source": doc.metadata.get("source", "Unknown"),
                "page": doc.metadata.get("page", -1),
                "content": doc.page_content[:200],
            }
            for doc in context
        ]
        return {"answer": response.get("answer", ""), "sources": sources}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Chat (streaming) ──────────────────────────────────────────────────────────

@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    if active_document is None or active_document not in document_stores:
        raise HTTPException(status_code=400, detail="No document is active. Please upload a PDF first.")

    _, streaming_chain = document_stores[active_document]

    def event_generator():
        docs = None
        for token, retrieved_docs in streaming_chain.stream(
            {"input": request.question, "history": request.history}
        ):
            docs = retrieved_docs
            yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

        sources = []
        if docs:
            for doc in docs:
                sources.append({
                    "source": doc.metadata.get("source", "Unknown"),
                    "page": doc.metadata.get("page", -1),
                    "content": doc.page_content[:200],
                })
        yield f"data: {json.dumps({'type': 'done', 'sources': sources})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
