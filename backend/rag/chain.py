from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

def create_rag_chain(retriever):
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
    
    system_prompt = (
        "You are an assistant for question-answering tasks. "
        "Use the following pieces of retrieved context to answer the question. "
        "If you don't know the answer, say that you don't know. "
        "Use three sentences maximum and keep the answer concise.\n\n"
        "Chat History:\n{history_str}\n\n"
        "Context:\n{context}"
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
    ])
    
    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    class CustomRagChain:
        def invoke(self, query_dict):
            query = query_dict["input"]
            history = query_dict.get("history", [])
            
            # Format history for the prompt
            history_str = ""
            for msg in history:
                role = "User" if msg.get("role") == "user" else "Assistant"
                history_str += f"{role}: {msg.get('content', '')}\n"
                
            if hasattr(retriever, "invoke"):
                docs = retriever.invoke(query)
            else:
                docs = retriever.get_relevant_documents(query)
                
            context_str = format_docs(docs)
            messages = prompt.format_messages(context=context_str, history_str=history_str, input=query)
            
            response = llm.invoke(messages)
            
            return {
                "answer": response.content,
                "context": docs
            }
            
    return CustomRagChain()
