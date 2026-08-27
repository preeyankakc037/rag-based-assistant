from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage


# ── Conversational detection ────────────────────────────────────────────────
_GREETINGS = {
    'hey', 'hi', 'hello', 'hiya', 'sup', 'what\'s up', 'whats up',
    'thanks', 'thank you', 'ty', 'thx', 'cheers',
    'ok', 'okay', 'got it', 'sure', 'alright', 'cool', 'great', 'nice',
    'bye', 'goodbye', 'see you', 'later',
    'good morning', 'good afternoon', 'good evening',
}

def _is_conversational(question: str) -> bool:
    """Return True if the question is a casual greeting that doesn't need retrieval."""
    q = question.strip().lower().rstrip('!.,?')
    # Exact match on common greetings
    if q in _GREETINGS:
        return True
    # Very short with no document-query words
    doc_words = {'what', 'how', 'why', 'when', 'where', 'who', 'which',
                 'tell', 'explain', 'describe', 'list', 'summarize', 'find',
                 'show', 'give', 'define', 'compare', 'difference', 'example'}
    words = set(q.split())
    if len(q) < 25 and not (words & doc_words) and '?' not in question:
        return True
    return False


# ── Prompt: rewrite a follow-up question into a standalone one ──────────────
CONDENSE_QUESTION_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a helpful assistant. Given the conversation history and a follow-up question, "
        "rewrite the follow-up question to be a fully self-contained, standalone question that "
        "can be understood without the conversation history. "
        "If the question is already standalone, return it unchanged. "
        "ONLY return the rewritten question, nothing else.",
    ),
    (
        "human",
        "Conversation history:\n{history}\n\nFollow-up question: {question}\n\nStandalone question:",
    ),
])

# ── Prompt: answer using retrieved context + full history ───────────────────
ANSWER_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a helpful assistant that answers questions based on provided document context. "
        "Use the retrieved context below to answer the user's question. "
        "If the answer is not in the context, say you don't know. "
        "Format your answer clearly using markdown where helpful.\n\n"
        "Context:\n{context}\n\n"
        "Conversation so far:\n{history}",
    ),
    ("human", "{question}"),
])


def _format_history(history: list) -> str:
    """Convert list of {role, content} dicts into a readable string."""
    if not history:
        return "(none)"
    lines = []
    for msg in history:
        role = "User" if msg.get("role") == "user" else "Assistant"
        lines.append(f"{role}: {msg.get('content', '')}")
    return "\n".join(lines)


def _condense_question(llm, question: str, history: list) -> str:
    """
    If there's no history, return the question unchanged.
    Otherwise ask the LLM to rewrite it as a standalone question.
    """
    if not history:
        return question

    messages = CONDENSE_QUESTION_PROMPT.format_messages(
        history=_format_history(history),
        question=question,
    )
    response = llm.invoke(messages)
    condensed = response.content.strip()
    return condensed if condensed else question


def _retrieve_and_format(retriever, standalone_question: str):
    """Retrieve relevant document chunks for the standalone question."""
    if hasattr(retriever, "invoke"):
        docs = retriever.invoke(standalone_question)
    else:
        docs = retriever.get_relevant_documents(standalone_question)

    context_str = "\n\n".join(doc.page_content for doc in docs)
    return docs, context_str


def create_rag_chain(retriever):
    """Non-streaming chain: condense → retrieve → answer."""
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

    class ConversationalRagChain:
        def invoke(self, query_dict: dict) -> dict:
            question = query_dict["input"]
            history = query_dict.get("history", [])

            if _is_conversational(question):
                messages = [
                    SystemMessage(content="You are a friendly, helpful assistant for a university RAG system. Answer conversationally and concisely."),
                ]
                # Add history if we want
                for msg in history:
                    role = "user" if msg.get("role") == "user" else "assistant"
                    messages.append({"role": role, "content": msg.get("content", "")})
                messages.append(HumanMessage(content=question))
                
                response = llm.invoke(messages)
                return {
                    "answer": response.content,
                    "context": [],
                    "standalone_question": question,
                }

            # Step 1: rewrite follow-up into standalone question
            standalone = _condense_question(llm, question, history)

            # Step 2: retrieve with the standalone question
            docs, context_str = _retrieve_and_format(retriever, standalone)

            # Step 3: generate answer with full history + context
            messages = ANSWER_PROMPT.format_messages(
                context=context_str,
                history=_format_history(history),
                question=question,
            )
            response = llm.invoke(messages)

            return {
                "answer": response.content,
                "context": docs,
                "standalone_question": standalone,
            }

    return ConversationalRagChain()


def create_streaming_rag_chain(retriever):
    """Streaming chain: condense → retrieve → stream answer tokens."""
    condense_llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
    stream_llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", streaming=True)

    class StreamingConversationalRagChain:
        def stream(self, query_dict: dict):
            question = query_dict["input"]
            history = query_dict.get("history", [])

            if _is_conversational(question):
                messages = [
                    SystemMessage(content="You are a friendly, helpful assistant for a university RAG system. Answer conversationally and concisely."),
                ]
                for msg in history:
                    role = "user" if msg.get("role") == "user" else "assistant"
                    messages.append({"role": role, "content": msg.get("content", "")})
                messages.append(HumanMessage(content=question))
                
                for chunk in stream_llm.stream(messages):
                    yield chunk.content, []
                return

            # Step 1: condense (non-streaming — fast, single call)
            standalone = _condense_question(condense_llm, question, history)

            # Step 2: retrieve with standalone question
            docs, context_str = _retrieve_and_format(retriever, standalone)

            # Step 3: stream answer tokens
            messages = ANSWER_PROMPT.format_messages(
                context=context_str,
                history=_format_history(history),
                question=question,
            )
            for chunk in stream_llm.stream(messages):
                yield chunk.content, docs

    return StreamingConversationalRagChain()
