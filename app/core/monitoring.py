import json
import time
from pathlib import Path

LOG_PATH = Path(__file__).resolve().parents[2] / "logs" / "usage.jsonl"
LOG_PATH.parent.mkdir(exist_ok=True)

# USD per 1M tokens. Ollama runs locally, so it's free. Groq pricing for
# openai/gpt-oss-20b, from console.groq.com/docs/models -- re-check that
# page periodically, prices change.
PRICING_PER_MILLION_TOKENS = {
    "groq": {"prompt": 0.075, "completion": 0.30},
    "ollama": {"prompt": 0.0, "completion": 0.0},
}

# Deliberately low for a learning project, so you actually see the alert
# fire during testing. Raise it to something realistic for real usage.
COST_ALERT_THRESHOLD_USD = 0.01


def estimate_cost(provider, prompt_tokens, completion_tokens):
    pricing = PRICING_PER_MILLION_TOKENS.get(provider, {"prompt": 0.0, "completion": 0.0})
    return (prompt_tokens * pricing["prompt"] + completion_tokens * pricing["completion"]) / 1_000_000


def log_usage(role, question, provider, prompt_tokens, completion_tokens):
    cost = estimate_cost(provider, prompt_tokens, completion_tokens)
    entry = {
        "timestamp": time.time(),
        "role": role,
        "question": question,
        "provider": provider,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "estimated_cost_usd": cost,
    }

    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

    with open(LOG_PATH, encoding="utf-8") as f:
        total_cost = sum(json.loads(line)["estimated_cost_usd"] for line in f)

    if total_cost >= COST_ALERT_THRESHOLD_USD:
        print(f"[ALERT] Cumulative estimated cost reached ${total_cost:.4f} (threshold: ${COST_ALERT_THRESHOLD_USD})")

    return entry