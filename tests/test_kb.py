from app.kb import KnowledgeBase


def test_add_and_query(tmp_path):
    kb = KnowledgeBase(storage_path=str(tmp_path / "kb.json"))
    chunks = kb.add_text("Shipping takes 3-5 business days.", source="faq.txt")

    assert chunks == 1
    result = kb.query("How long is shipping?")

    assert result
    assert "3-5 business days" in result[0]["content"]


def test_context_for_empty_kb(tmp_path):
    kb = KnowledgeBase(storage_path=str(tmp_path / "kb.json"))
    assert kb.context_for("hello") == ""
