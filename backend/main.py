import json
import os
import shutil
from pathlib import Path
from typing import List, Dict, Any

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

# Global RAG state (in-memory, reset on new upload)
vector_store = None
rag_chain = None
streaming_rag_chain = None


class ChatRequest(BaseModel):
    question: str
    history: List[Dict[str, Any]] = []


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    global vector_store, rag_chain, streaming_rag_chain

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
        rag_chain = create_rag_chain(retriever)
        streaming_rag_chain = create_streaming_rag_chain(retriever)

        return {"message": f"Successfully processed {file.filename}. Ready for chat."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat")
async def chat(request: ChatRequest):
    """Non-streaming endpoint — returns a single JSON response."""
    if rag_chain is None:
        raise HTTPException(status_code=400, detail="No document uploaded yet. Please upload a PDF first.")

    try:
        response = rag_chain.invoke({"input": request.question, "history": request.history})

        answer = response.get("answer", "")
        context = response.get("context", [])

        sources = []
        for doc in context:
            source = doc.metadata.get("source", "Unknown")
            page = doc.metadata.get("page", -1)
            sources.append({"source": source, "page": page, "content": doc.page_content[:200]})

        return {"answer": answer, "sources": sources}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """Streaming endpoint — uses Server-Sent Events (SSE) to stream tokens."""
    if streaming_rag_chain is None:
        raise HTTPException(status_code=400, detail="No document uploaded yet. Please upload a PDF first.")

    def event_generator():
        docs = None
        full_text = ""

        for token, retrieved_docs in streaming_rag_chain.stream(
            {"input": request.question, "history": request.history}
        ):
            docs = retrieved_docs  # keep updating; last one is the real set
            full_text += token
            # Send each token as an SSE "token" event
            payload = json.dumps({"type": "token", "content": token})
            yield f"data: {payload}\n\n"

        # After streaming is done, send the citations as a final event
        sources = []
        if docs:
            for doc in docs:
                sources.append({
                    "source": doc.metadata.get("source", "Unknown"),
                    "page": doc.metadata.get("page", -1),
                    "content": doc.page_content[:200],
                })

        done_payload = json.dumps({"type": "done", "sources": sources})
        yield f"data: {done_payload}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
