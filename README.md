# University RAG-Based Assistant

A Retrieval-Augmented Generation (RAG) based assistant for answering queries related to university guidelines, documents, and data.

## Project Structure

- `frontend/`: The React-based user interface.
- `backend/`: The FastAPI backend handling the API, embeddings, and RAG logic.
- `data/` and `backend/uploads/`: Directories intended for storing documents to be ingested into the RAG system.

## Setup Instructions

### Backend
1. Navigate to the `backend/` directory.
2. Create and activate a virtual environment.
3. Install dependencies: `pip install -r requirements.txt`.
4. Copy `.env.example` to `.env` (if applicable) and add your environment variables (e.g., API keys).
5. Run the server: `uvicorn main:app --reload`.

### Frontend
1. Navigate to the `frontend/` directory.
2. Install dependencies: `npm install`.
3. Run the development server: `npm run dev` or `npm start`.

## Usage
- Upload documents via the frontend interface (sample provided in `backend/uploads`).
- Use the chat interface to ask questions about the uploaded content.
