from fastapi import FastAPI

app = FastAPI(title="University RAG Assistant")


@app.get("/")
def root():
    return {"message": "University RAG Assistant API is running"}