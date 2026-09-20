from app.core.logger import get_logger

logger = get_logger(__name__)

CHUNK_SIZE = 500      # characters per chunk
CHUNK_OVERLAP = 50    # overlap between chunks


def split_text(text: str) -> list[str]:
    """
    Split text into overlapping chunks.
    
    Why overlap?
    If a sentence spans two chunks, overlap ensures
    neither chunk loses important context.
    
    Example with chunk_size=20, overlap=5:
    Text:   "The cat sat on the mat in the room"
    Chunk1: "The cat sat on the"
    Chunk2: "on the mat in the"
    Chunk3: "in the room"
    """
    if not text or not text.strip():
        logger.warning("Empty text received for chunking")
        return []

    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = start + CHUNK_SIZE

        # if not at end of text, try to break at a space
        if end < text_length:
            space_index = text.rfind(" ", start, end)
            if space_index > start:
                end = space_index

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        # move forward but keep some overlap
        start = end - CHUNK_OVERLAP

    logger.info(f"Split text into {len(chunks)} chunks")
    return chunks