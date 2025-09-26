from core.utils import hash_id, norm_text


def test_norm_text_collapses_whitespace():
    assert norm_text("  Hello\nWorld  ") == "Hello World"


def test_hash_id_is_stable():
    assert hash_id("https://example.com") == hash_id("https://example.com")
