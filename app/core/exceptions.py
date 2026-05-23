class AppError(Exception):
    """Base application error."""


class DocumentParseError(AppError):
    """Raised when a document cannot be parsed."""


class UnsupportedFileTypeError(AppError):
    """Raised when the file extension is not supported."""


class VectorStoreError(AppError):
    """Raised when vector store operations fail."""


class EmbeddingError(AppError):
    """Raised when embedding generation fails."""


class LLMError(AppError):
    """Raised when LLM requests fail."""


class BookingError(AppError):
    """Raised when booking flow encounters an error."""
