def get_retriever(vector_store, k=4):
    """Get a retriever from the vector store."""
    return vector_store.as_retriever(search_kwargs={"k": k})
