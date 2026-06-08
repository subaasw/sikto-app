from api.knowledge.chunks import chunk_id, source_id_of


def test_chunk_id_embeds_source():
    assert chunk_id("src-1", 3) == "src-1:3"


def test_source_id_round_trips():
    assert source_id_of(chunk_id("src-1", 0)) == "src-1"


def test_source_id_of_uuid_like():
    assert source_id_of("a1b2c3-uuid:7") == "a1b2c3-uuid"


def test_source_id_of_without_index():
    assert source_id_of("plain") == "plain"
