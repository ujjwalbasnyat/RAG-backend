import hashlib


def compute_sha256(content: bytes) -> str:
    """Return SHA-256 hex digest of file bytes."""
    return hashlib.sha256(content).hexdigest()
