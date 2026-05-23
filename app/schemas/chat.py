from uuid import UUID

from pydantic import BaseModel, Field


class ChatQueryRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=255)
    query: str = Field(..., min_length=1)
    document_id: UUID | None = None


class SourceChunk(BaseModel):
    document_id: str
    filename: str
    chunk_index: int
    score: float


class BookingStatus(BaseModel):
    name: str | None = None
    email: str | None = None
    date: str | None = None
    time: str | None = None
    complete: bool = False


class ChatQueryResponse(BaseModel):
    response: str
    intent: str
    sources: list[SourceChunk] = Field(default_factory=list)
    booking: BookingStatus | None = None
