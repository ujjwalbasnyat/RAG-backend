import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import DocumentParseError, UnsupportedFileTypeError, VectorStoreError
from app.core.logging import logger
from app.db.session import get_db
from app.models.sql import Document, DocumentChunk
from app.schemas.ingestion import ChunkingStrategy, IngestionRequest, IngestionResponse
from app.services.chunker import chunk_text
from app.services.embedder import embed_texts
from app.services.parser import extract_text
from app.services.vector_store import delete_chunks_by_document, upsert_chunks
from app.utils.hashing import compute_sha256

router = APIRouter()
_settings = get_settings()


@router.post("/documents/ingest", response_model=IngestionResponse)
async def ingest_document(
    file: UploadFile = File(...),
    chunking_strategy: ChunkingStrategy = Form(...),
    chunk_size: int | None = Form(None),
    chunk_overlap: int | None = Form(None),
    session: AsyncSession = Depends(get_db),
) -> IngestionResponse:
    request = IngestionRequest(
        chunking_strategy=chunking_strategy,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file content")

    file_hash = compute_sha256(content)
    existing = await session.execute(
        select(Document).where(Document.file_hash == file_hash)
    )
    existing_doc = existing.scalar_one_or_none()
    if existing_doc:
        last_chunk = await session.execute(
            select(DocumentChunk.text_preview)
            .where(DocumentChunk.document_id == existing_doc.id)
            .order_by(DocumentChunk.chunk_index.desc())
            .limit(1)
        )
        last_chunk_preview = last_chunk.scalar_one_or_none() or ""
        return IngestionResponse(
            document_id=existing_doc.id,
            filename=existing_doc.filename,
            chunk_count=existing_doc.chunk_count,
            status="duplicate",
            chunking_strategy=existing_doc.chunking_strategy,
            last_chunk=last_chunk_preview,
        )

    effective_chunk_size = request.chunk_size or _settings.chunk_size_default
    effective_chunk_overlap = (
        request.chunk_overlap
        if request.chunk_overlap is not None
        else _settings.chunk_overlap_default
    )
    if effective_chunk_overlap >= effective_chunk_size // 2:
        raise HTTPException(
            status_code=400,
            detail="chunk_overlap must be less than chunk_size // 2",
        )

    document_id = uuid.uuid4()
    file_ext = file.filename.rsplit(".", 1)[-1].lower()

    try:
        text = extract_text(file.filename, content)
        chunks = chunk_text(
            text=text,
            strategy=request.chunking_strategy,
            chunk_size=effective_chunk_size,
            chunk_overlap=effective_chunk_overlap,
        )
        if not chunks:
            raise DocumentParseError("No text chunks were produced.")

        embeddings = await embed_texts(chunks)
        vector_ids = await upsert_chunks(
            document_id=str(document_id),
            filename=file.filename,
            chunking_strategy=request.chunking_strategy.value,
            chunks=chunks,
            embeddings=embeddings,
        )
    except UnsupportedFileTypeError as exc:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {exc}") from exc
    
    except DocumentParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    
    except VectorStoreError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    
    except Exception as exc:
        logger.error("ingestion_failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Ingestion failed") from exc

    document = Document(
        id=document_id,
        filename=file.filename,
        file_type=file_ext,
        file_hash=file_hash,
        chunking_strategy=request.chunking_strategy.value,
        chunk_size=effective_chunk_size,
        chunk_overlap=effective_chunk_overlap,
        chunk_count=len(chunks),
        status="ready",
    )

    try:
        session.add(document)
        for idx, vector_id in enumerate(vector_ids):
            chunk = chunks[idx]
            session.add(
                DocumentChunk(
                    document_id=document_id,
                    chunk_index=idx,
                    vector_id=vector_id,
                    text_preview=chunk[:200],
                    token_count=len(chunk.split()),
                )
            )
        await session.commit()
    except Exception as exc:
        await session.rollback()
        await delete_chunks_by_document(str(document_id))
        logger.error("ingestion_db_failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to persist ingestion") from exc

    return IngestionResponse(
        document_id=document_id,
        filename=file.filename,
        chunk_count=len(chunks),
        status="ready",
        chunking_strategy=request.chunking_strategy.value,
        last_chunk=chunks[-1][:200],
    )
