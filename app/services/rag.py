from groq import AsyncGroq

from app.core.config import get_settings
from app.core.exceptions import LLMError
from app.core.logging import logger
from app.services.chat_memory import get_history
from app.services.embedder import embed_texts
from app.services.vector_store import RetrievedChunk, search_and_rerank
from app.services.rag_prompt import RAG_SYSTEM_PROMPT

_settings = get_settings()
_client = AsyncGroq(api_key=_settings.groq_api_key)


async def answer_query(
    query: str,
    session_id: str,
    document_id: str | None = None,
) -> tuple[str, list[RetrievedChunk]]:
    
    history = await get_history(session_id)

    embeddings = await embed_texts([query])

    chunks = await search_and_rerank(
        query=query,
        query_embedding=embeddings[0],
        top_k_retrieve=_settings.top_k_retrieve,
        top_k_rerank=_settings.top_k_rerank,
        document_id=document_id,
    )

    if not chunks:
        return (
            "I could not find relevant information in the indexed documents.",
            [],
        )

    context = "\n\n".join(
        f"[{chunk.filename}#{chunk.chunk_index}]\n{chunk.text}"
        for chunk in chunks
    )

    messages: list[dict[str, str]] = [
        {"role": "system", "content": RAG_SYSTEM_PROMPT},
        *history,
        {"role": "system", "content":f"Context:\n{context}"},
        {"role": "user", "content": query}
        ]

    try:
        response = await _client.chat.completions.create(
            model=_settings.groq_chat_model,
            messages=messages,
        )
        answer = response.choices[0].message.content.strip()
        return answer, chunks
    except Exception as exc:
        logger.error("rag_llm_failed", error=str(exc))
        raise LLMError(f"LLM request failed: {exc}") from exc
