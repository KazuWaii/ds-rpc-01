from unittest.mock import MagicMock, patch

from app.services import llm


def test_chat_ollama_path(monkeypatch):
    monkeypatch.setattr(llm, "LLM_PROVIDER", "ollama")
    fake_response = {
        "message": {"content": "hello from ollama"},
        "prompt_eval_count": 12,
        "eval_count": 3,
    }
    with patch("app.services.llm.ollama.chat", return_value=fake_response) as mock_chat:
        result = llm.chat([{"role": "user", "content": "hi"}])

    mock_chat.assert_called_once()
    assert result.content == "hello from ollama"
    assert result.prompt_tokens == 12
    assert result.completion_tokens == 3


def test_chat_ollama_path_defaults_missing_token_counts_to_zero(monkeypatch):
    monkeypatch.setattr(llm, "LLM_PROVIDER", "ollama")
    fake_response = {"message": {"content": "hi"}}  # no token count fields at all
    with patch("app.services.llm.ollama.chat", return_value=fake_response):
        result = llm.chat([{"role": "user", "content": "hi"}])

    assert result.prompt_tokens == 0
    assert result.completion_tokens == 0


def test_chat_groq_path(monkeypatch):
    monkeypatch.setattr(llm, "LLM_PROVIDER", "groq")

    fake_response = MagicMock()
    fake_response.choices[0].message.content = "hello from groq"
    fake_response.usage.prompt_tokens = 20
    fake_response.usage.completion_tokens = 5

    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = fake_response
    monkeypatch.setattr(llm, "_groq_client", fake_client)

    result = llm.chat([{"role": "user", "content": "hi"}])

    fake_client.chat.completions.create.assert_called_once_with(
        model=llm.GROQ_MODEL, messages=[{"role": "user", "content": "hi"}]
    )
    assert result.content == "hello from groq"
    assert result.prompt_tokens == 20
    assert result.completion_tokens == 5
