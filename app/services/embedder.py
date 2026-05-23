import asyncio

from sentence_transformers import SentenceTransformer

from app.core.config import get_settings

_settings = get_settings()
_model = SentenceTransformer(_settings.embedding_model_name)

_BATCH_SIZE = 128


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Embed a list of texts in batches using a local model.
    Returns list of embedding vectors in the same order as input.
    """
    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), _BATCH_SIZE):
        batch = texts[i : i + _BATCH_SIZE]
        embeddings = await asyncio.to_thread(
            _model.encode,
            batch,
            batch_size=32,
            normalize_embeddings=True,
        )
        all_embeddings.extend([e.tolist() for e in embeddings])

    return all_embeddings
