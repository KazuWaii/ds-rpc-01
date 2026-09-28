from unittest.mock import patch

from app.services import rag
from app.services.llm import ChatResult


def _sample_chunk(distance, department="finance", source="finance/doc.md", section="Section"):
    return {
        "text": "some retrieved text",
        "metadata": {"department": department, "source": source, "section": section},
        "distance": distance,
    }


def test_answer_question_blocks_out_of_scope_before_retrieval():
    with patch("app.services.rag.is_out_of_scope", return_value=True), \
         patch("app.services.rag.vectorstore.query") as mock_query:
        result = rag.answer_question("what's the weather?", role="finance")

    mock_query.assert_not_called()
    assert result["sources"] == []
    assert "FinSolve" in result["answer"]


def test_answer_question_no_relevant_chunks_returns_honest_fallback():
    with patch("app.services.rag.is_out_of_scope", return_value=False), \
         patch("app.services.rag.vectorstore.query", return_value=[]):
        result = rag.answer_question("obscure question", role="finance")

    assert result["sources"] == []
    assert "couldn't find" in result["answer"].lower()


def test_answer_question_filters_out_chunks_past_distance_threshold():
    chunks = [
        _sample_chunk(distance=0.2, source="finance/good.md"),
        _sample_chunk(distance=0.9, source="finance/bad.md"),  # past MAX_RELEVANT_DISTANCE
    ]
    fake_result = ChatResult(content="an answer", prompt_tokens=10, completion_tokens=5)

    with patch("app.services.rag.is_out_of_scope", return_value=False), \
         patch("app.services.rag.vectorstore.query", return_value=chunks), \
         patch("app.services.rag.chat", return_value=fake_result), \
         patch("app.services.rag.log_usage") as mock_log:
        result = rag.answer_question("a question", role="finance")

    assert result["sources"] == ["finance/good.md"]
    mock_log.assert_called_once()


def test_answer_question_redacts_pii_in_final_answer():
    chunks = [_sample_chunk(distance=0.1)]
    fake_result = ChatResult(
        content="Call the vendor at 555-123-4567 for details.",
        prompt_tokens=10,
        completion_tokens=5,
    )

    with patch("app.services.rag.is_out_of_scope", return_value=False), \
         patch("app.services.rag.vectorstore.query", return_value=chunks), \
         patch("app.services.rag.chat", return_value=fake_result), \
         patch("app.services.rag.log_usage"):
        result = rag.answer_question("a question", role="finance")

    assert "555-123-4567" not in result["answer"]
    assert "[REDACTED_PHONE]" in result["answer"]


def test_answer_question_logs_usage_with_correct_args():
    chunks = [_sample_chunk(distance=0.1)]
    fake_result = ChatResult(content="answer", prompt_tokens=42, completion_tokens=7)

    with patch("app.services.rag.is_out_of_scope", return_value=False), \
         patch("app.services.rag.vectorstore.query", return_value=chunks), \
         patch("app.services.rag.chat", return_value=fake_result), \
         patch("app.services.rag.log_usage") as mock_log:
        rag.answer_question("a question", role="hr")

    mock_log.assert_called_once_with("hr", "a question", rag.LLM_PROVIDER, 42, 7)
