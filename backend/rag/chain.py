from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate


def _build_prompt_and_docs(retriever, query_dict):
    """Shared helper that retrieves docs and formats the messages."""
    query = query_dict["input"]
    history = query_dict.get("history", [])

    # Format conversation history for the system prompt
    history_str = ""
    for msg in history:
        role = "User" if msg.get("role") == "user" else "Assistant"
        history_str += f"{role}: {msg.get('content', '')}\n"

    # Retrieve relevant document chunks
    if hasattr(retriever, "invoke"):
        docs = retriever.invoke(query)
    else:
        docs = retriever.get_relevant_documents(query)

    context_str = "\n\n".join(doc.page_content for doc in docs)

    system_prompt = (
        "You are an assistant for question-answering tasks. "
        "Use the following pieces of retrieved context to answer the question. "
        "If you don't know the answer, say that you don't know. "
        "Keep the answer concise and helpful.\n\n"
        "Chat History:\n{history_str}\n\n"
        "Context:\n{context}"
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
    ])

    messages = prompt.format_messages(
        context=context_str,
        history_str=history_str,
        input=query,
    )

    return messages, docs


def create_rag_chain(retriever):
    """Returns an object with .invoke() for a one-shot answer."""
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

    class CustomRagChain:
        def invoke(self, query_dict):
            messages, docs = _build_prompt_and_docs(retriever, query_dict)
            response = llm.invoke(messages)
            return {
                "answer": response.content,
                "context": docs,
            }

    return CustomRagChain()


def create_streaming_rag_chain(retriever):
    """Returns an object with .stream() that yields text tokens."""
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", streaming=True)

    class StreamingRagChain:
        def stream(self, query_dict):
            messages, docs = _build_prompt_and_docs(retriever, query_dict)
            # Yield each token chunk as it arrives
            for chunk in llm.stream(messages):
                yield chunk.content, docs

    return StreamingRagChain()
