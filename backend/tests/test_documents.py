from app.services.documents import chunk_text


def test_chunk_text_splits():
    text = "A" * 2500
    chunks = list(chunk_text(text, max_chars=1000, overlap=100))
    assert len(chunks) == 3
    assert all(len(chunk) <= 1000 for chunk in chunks)
