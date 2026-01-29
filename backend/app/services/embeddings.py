from openai import OpenAI
from app.core.config import settings


EMBEDDING_DIM = 3072


def _pad_embedding(embedding: list[float]) -> list[float]:
    if len(embedding) >= EMBEDDING_DIM:
        return embedding[:EMBEDDING_DIM]
    return embedding + [0.0] * (EMBEDDING_DIM - len(embedding))


def embed_texts(texts: list[str], model: str | None = None) -> list[list[float]]:
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY not configured for embeddings.")
    client = OpenAI(api_key=settings.openai_api_key)
    response = client.embeddings.create(
        model=model or settings.embedding_model,
        input=texts,
    )
    return [_pad_embedding(item.embedding) for item in response.data]
