import google.generativeai as genai
from app.core.config import settings

_gemini_configured = False

def configure_gemini():
    global _gemini_configured
    if not _gemini_configured:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        _gemini_configured = True

def get_embedding(text: str, is_query: bool = False) -> list[float]:
    configure_gemini()
    # Use different task_type for queries vs documents
    task_type = "retrieval_query" if is_query else "retrieval_document"
    result = genai.embed_content(
        model=settings.GEMINI_EMBEDDING_MODEL,
        content=text,
        task_type=task_type
    )
    return result['embedding']

def get_batch_embeddings(texts: list[str]) -> list[list[float]]:
    configure_gemini()
    # Gemini API supports batch embedding, but for simplicity and error handling we might loop or use batch if supported well.
    # embed_content supports a list of content.
    result = genai.embed_content(
        model=settings.GEMINI_EMBEDDING_MODEL,
        content=texts,
        task_type="retrieval_document"
    )
    return result['embedding']
