import uuid
from dataclasses import dataclass

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    ScoredPoint,
    VectorParams,
)
from sentence_transformers import CrossEncoder

from app.core.config import get_settings
from app.core.exceptions import VectorStoreError
from app.core.logging import logger

_settings = get_settings()

_client = AsyncQdrantClient(url=_settings.qdrant_url, api_key=_settings.qdrant_api_key or None)
_reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

VECTOR_DIM = _settings.embedding_dim


@dataclass
class RetrievedChunk:
    vector_id: str
    document_id: str
    chunk_index: int
    text: str
    filename: str
    chunking_strategy: str
    token_count: int
    score: float


async def ensure_collection() -> None:
    """Create Qdrant collection if it does not exist."""
    exists = await _client.collection_exists(_settings.qdrant_collection)
    if not exists:
        await _client.create_collection(
            collection_name=_settings.qdrant_collection,
            vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
        )
        logger.info("qdrant_collection_created", collection=_settings.qdrant_collection)


async def upsert_chunks(
    document_id: str,
    filename: str,
    chunking_strategy: str,
    chunks: list[str],
    embeddings: list[list[float]],
) -> list[str]:
    """
    Upsert chunk vectors into Qdrant with 6-field payload.
    Returns list of vector_ids in chunk order.
    Raises VectorStoreError on failure.
    """
    await ensure_collection()

    points: list[PointStruct] = []
    vector_ids: list[str] = []

    for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        vector_id = str(uuid.uuid4())
        vector_ids.append(vector_id)

        points.append(
            PointStruct(
                id=vector_id,
                vector=embedding,
                payload={
                    "document_id": document_id,
                    "chunk_index": idx,
                    "text": chunk,
                    "filename": filename,
                    "chunking_strategy": chunking_strategy,
                    "token_count": len(chunk.split()),
                },
            )
        )

    try:
        await _client.upsert(
            collection_name=_settings.qdrant_collection,
            points=points,
        )
    except Exception as exc:
        raise VectorStoreError(f"Qdrant upsert failed: {exc}") from exc

    return vector_ids


async def delete_chunks_by_document(document_id: str) -> None:
    """Delete all vectors belonging to a document; used for rollback."""
    try:
        await _client.delete(
            collection_name=_settings.qdrant_collection,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=document_id),
                    )
                ]
            ),
        )
    except Exception as exc:
        logger.error("qdrant_rollback_failed", document_id=document_id, error=str(exc))


async def search_and_rerank(
    query: str,
    query_embedding: list[float],
    top_k_retrieve: int = 10,
    top_k_rerank: int = 5,
    document_id: str | None = None,
) -> list[RetrievedChunk]:
    """
    1. Cosine similarity search -> top_k_retrieve results
    2. Cross-encoder rerank -> top_k_rerank results
    3. Deduplicate by vector_id
    4. Order by chunk_index
    """
    query_filter = None
    if document_id:
        query_filter = Filter(
            must=[
                FieldCondition(
                    key="document_id",
                    match=MatchValue(value=document_id),
                )
            ]
        )

    try:
        results: list[ScoredPoint] = await _client.search(
            collection_name=_settings.qdrant_collection,
            query_vector=query_embedding,
            limit=top_k_retrieve,
            query_filter=query_filter,
            with_payload=True,
        )
    except Exception as exc:
        raise VectorStoreError(f"Qdrant search failed: {exc}") from exc

    if not results:
        return []

    pairs = [[query, r.payload["text"]] for r in results]
    rerank_scores: list[float] = _reranker.predict(pairs).tolist()

    scored = sorted(
        zip(results, rerank_scores),
        key=lambda x: x[1],
        reverse=True,
    )[:top_k_rerank]

    # scored = [(r, r.score) for r in sorted(results, key=lambda x: x.score, reverse=True)[:top_k_rerank]]


    seen: set[str] = set()
    chunks: list[RetrievedChunk] = []

    for point, score in scored:
        vid = str(point.id)
        if vid in seen:
            continue
        seen.add(vid)
        payload = point.payload
        chunks.append(
            RetrievedChunk(
                vector_id=vid,
                document_id=payload["document_id"],
                chunk_index=payload["chunk_index"],
                text=payload["text"],
                filename=payload["filename"],
                chunking_strategy=payload["chunking_strategy"],
                token_count=payload["token_count"],
                score=score,
            )
        )

    chunks.sort(key=lambda c: c.chunk_index)
    return chunks
