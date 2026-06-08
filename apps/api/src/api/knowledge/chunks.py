def chunk_id(source_id: str, index: int) -> str:
    """Build a chunk id that embeds its source id, so retrieval can attribute
    passages back to a source for citations."""
    return f"{source_id}:{index}"


def source_id_of(chunk_id_value: str) -> str:
    """Recover the source id from a chunk id produced by ``chunk_id``."""
    return chunk_id_value.rsplit(":", 1)[0]
