from app.schemas.ingestion import ChunkingStrategy


def chunk_text(
    text: str,
    strategy: ChunkingStrategy,
    chunk_size: int,
    chunk_overlap: int,
) -> list[str]:
    """
    Dispatch to the selected chunking strategy.
    Returns a list of non-empty chunk strings.
    """
    if strategy == ChunkingStrategy.fixed:
        return _fixed_size_chunks(text, chunk_size, chunk_overlap)
    return _recursive_chunks(text, chunk_size, chunk_overlap)


# Fixed-size chunking

def _fixed_size_chunks(text: str, chunk_size: int, overlap: int) -> list[str]:
    """
    Split text into chunks of `chunk_size` characters with `overlap` characters
    of overlap between consecutive chunks.
    """
    chunks: list[str] = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += chunk_size - overlap

    return chunks


# Recursive chunking

_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]


def _recursive_chunks(text: str, chunk_size: int, overlap: int) -> list[str]:
    """
    Recursively split text by trying separators from largest to smallest boundary.
    Merges small splits back up to chunk_size with overlap.
    """
    raw_splits = _split_recursive(text, chunk_size, _SEPARATORS)
    return _merge_splits(raw_splits, chunk_size, overlap)


def _split_recursive(text: str, chunk_size: int, separators: list[str]) -> list[str]:
    if len(text) <= chunk_size:
        return [text]

    separator = ""
    remaining_separators: list[str] = []

    for i, sep in enumerate(separators):
        if sep == "" or sep in text:
            separator = sep
            remaining_separators = separators[i + 1 :]
            break

    splits = text.split(separator) if separator else list(text)
    result: list[str] = []

    for split in splits:
        split = split.strip()
        if not split:
            continue
        if len(split) <= chunk_size:
            result.append(split)
        else:
            result.extend(_split_recursive(split, chunk_size, remaining_separators))

    return result


def _merge_splits(splits: list[str], chunk_size: int, overlap: int) -> list[str]:
    """
    Merge small splits into chunks up to chunk_size.
    Adds overlap by re-including tail of previous chunk.
    """
    chunks: list[str] = []
    current_parts: list[str] = []
    current_len = 0

    for split in splits:
        split_len = len(split)

        if current_len + split_len > chunk_size and current_parts:
            chunk = " ".join(current_parts).strip()
            if chunk:
                chunks.append(chunk)

            overlap_parts: list[str] = []
            overlap_len = 0
            for part in reversed(current_parts):
                if overlap_len + len(part) <= overlap:
                    overlap_parts.insert(0, part)
                    overlap_len += len(part)
                else:
                    break

            current_parts = overlap_parts
            current_len = overlap_len

        current_parts.append(split)
        current_len += split_len

    if current_parts:
        chunk = " ".join(current_parts).strip()
        if chunk:
            chunks.append(chunk)

    return chunks
