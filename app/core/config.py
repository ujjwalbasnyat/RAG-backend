from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    app_name: str = Field(default="rag_backend", validation_alias="APP_NAME")
    environment: str = Field(default="local", validation_alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    database_url: str = Field(
        default="postgresql+asyncpg://raguser:ragpassword@localhost:5432/rag_db",
        validation_alias="DATABASE_URL",
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        validation_alias="REDIS_URL",
    )
    qdrant_url: str = Field(
        default="http://localhost:6333",
        validation_alias="QDRANT_URL",
    )
    qdrant_collection: str = Field(
        default="rag_chunks",
        validation_alias="QDRANT_COLLECTION",
    )

    groq_api_key: str = Field(default="", validation_alias="GROQ_API_KEY")
    groq_chat_model: str = Field(
        default="llama-3.1-70b-versatile",
        validation_alias="GROQ_CHAT_MODEL",
    )
    embedding_model_name: str = Field(
        default="all-MiniLM-L6-v2",
        validation_alias="EMBEDDING_MODEL_NAME",
    )
    embedding_dim: int = Field(
        default=384,
        ge=64,
        le=4096,
        validation_alias="EMBEDDING_DIM",
    )

    chunk_size_default: int = Field(
        default=512,
        ge=64,
        le=2048,
        validation_alias="CHUNK_SIZE_DEFAULT",
    )
    chunk_overlap_default: int = Field(
        default=64,
        ge=0,
        validation_alias="CHUNK_OVERLAP_DEFAULT",
    )

    top_k_retrieve: int = Field(
        default=10,
        ge=1,
        le=50,
        validation_alias="TOP_K_RETRIEVE",
    )
    top_k_rerank: int = Field(
        default=5,
        ge=1,
        le=20,
        validation_alias="TOP_K_RERANK",
    )

    chat_memory_limit: int = Field(
        default=10,
        ge=1,
        le=50,
        validation_alias="CHAT_MEMORY_LIMIT",
    )
    chat_memory_ttl: int = Field(
        default=3600,
        ge=60,
        validation_alias="CHAT_MEMORY_TTL",
    )
    booking_ttl: int = Field(
        default=3600,
        ge=60,
        validation_alias="BOOKING_TTL",
    )

    request_timeout_s: int = Field(
        default=60,
        ge=1,
        le=300,
        validation_alias="REQUEST_TIMEOUT_S",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
