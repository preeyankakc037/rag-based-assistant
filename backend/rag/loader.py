from langchain_community.document_loaders import PDFPlumberLoader

def load_pdf(pdf_path: str):
    """Load a PDF using PDFPlumber for better extraction of messy tables and return its pages as LangChain documents."""
    loader = PDFPlumberLoader(pdf_path)
    return loader.load()
