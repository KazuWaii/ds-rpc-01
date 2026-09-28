import json

from app.core import monitoring


def test_estimate_cost_ollama_is_always_free():
    assert monitoring.estimate_cost("ollama", prompt_tokens=1_000_000, completion_tokens=1_000_000) == 0.0


def test_estimate_cost_groq_matches_published_pricing():
    # $0.075 / 1M prompt tokens, $0.30 / 1M completion tokens (openai/gpt-oss-20b)
    cost = monitoring.estimate_cost("groq", prompt_tokens=1_000_000, completion_tokens=1_000_000)
    assert cost == 0.075 + 0.30


def test_estimate_cost_unknown_provider_defaults_to_zero():
    assert monitoring.estimate_cost("some-new-provider", 1000, 1000) == 0.0


def test_log_usage_appends_jsonl_entry(tmp_path, monkeypatch):
    log_path = tmp_path / "usage.jsonl"
    monkeypatch.setattr(monitoring, "LOG_PATH", log_path)

    entry = monitoring.log_usage("finance", "a question", "groq", prompt_tokens=100, completion_tokens=50)

    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    logged = json.loads(lines[0])
    assert logged["role"] == "finance"
    assert logged["provider"] == "groq"
    assert logged["prompt_tokens"] == 100
    assert logged["completion_tokens"] == 50
    assert logged["estimated_cost_usd"] == entry["estimated_cost_usd"]


def test_log_usage_accumulates_across_calls(tmp_path, monkeypatch):
    log_path = tmp_path / "usage.jsonl"
    monkeypatch.setattr(monitoring, "LOG_PATH", log_path)

    monitoring.log_usage("finance", "q1", "groq", 100, 50)
    monitoring.log_usage("hr", "q2", "groq", 100, 50)

    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2


def test_log_usage_prints_alert_past_threshold(tmp_path, monkeypatch, capsys):
    log_path = tmp_path / "usage.jsonl"
    monkeypatch.setattr(monitoring, "LOG_PATH", log_path)
    monkeypatch.setattr(monitoring, "COST_ALERT_THRESHOLD_USD", 0.001)

    monitoring.log_usage("finance", "expensive question", "groq", prompt_tokens=100_000, completion_tokens=50_000)

    captured = capsys.readouterr()
    assert "[ALERT]" in captured.out


def test_log_usage_no_alert_below_threshold(tmp_path, monkeypatch, capsys):
    log_path = tmp_path / "usage.jsonl"
    monkeypatch.setattr(monitoring, "LOG_PATH", log_path)
    monkeypatch.setattr(monitoring, "COST_ALERT_THRESHOLD_USD", 1000.0)

    monitoring.log_usage("finance", "cheap question", "groq", prompt_tokens=10, completion_tokens=5)

    captured = capsys.readouterr()
    assert "[ALERT]" not in captured.out
