from api.storage import LocalStorage


def test_put_get_exists(tmp_path):
    store = LocalStorage(str(tmp_path))
    ref = store.put("audio/clip1.bin", b"hello")
    assert store.exists(ref)
    assert store.get(ref) == b"hello"


def test_missing_returns_not_exists(tmp_path):
    store = LocalStorage(str(tmp_path))
    assert store.exists("audio/nope.bin") is False
