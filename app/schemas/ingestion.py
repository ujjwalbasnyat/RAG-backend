from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class ChunkingStrategy(str, Enum):
    fixed = "fixed"
    recursive = "recursive"


class IngestionRequest(BaseModel):
    chunking_strategy: ChunkingStrategy
    chunk_size: int | None = Field(default=None, ge=64, le=2048)
    chunk_overlap: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_overlap(self) -> "IngestionRequest":
        if self.chunk_size is not None and self.chunk_overlap is not None:
            if self.chunk_overlap >= self.chunk_size // 2:
                raise ValueError("chunk_overlap must be less than chunk_size // 2")
        return self


class IngestionResponse(BaseModel):
    document_id: UUID
    filename: str
    chunk_count: int
    status: str
    chunking_strategy: str
    last_chunk: str
