import re
import ollama

OLLAMA_MODEL = "llama3.2"

_SCOPE_SYSTEM_PROMPT = (
    "You are a strict classifier for FinSolve Technologies' internal assistant. "
    "Determine whether the user's question is about FinSolve's internal business "
    "(finance, HR, marketing, engineering, company policies, expenses, employees) "
    "or something unrelated (general knowledge, personal requests, coding help, etc.). "
    "Business questions don't need to explicitly say \"FinSolve\" to be in scope.\n\n"
    "Examples:\n"
    "Q: What is the capital of France? -> OUTOFSCOPE\n"
    "Q: Write me a poem about the ocean. -> OUTOFSCOPE\n"
    "Q: What drove the increase in vendor expenses in 2024? -> INSCOPE\n"
    "Q: What is the reimbursement policy for travel? -> INSCOPE\n"
    "Q: What's 2 + 2? -> OUTOFSCOPE\n\n"
    "Respond with exactly one word: INSCOPE or OUTOFSCOPE."
)

# Protection against PII (Personally Identifiable Information) in text data
_PII_PATTERNS = {
    "credit_card": re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "phone": re.compile(r"\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b"),
}


def contains_pii(text):
    return any(pattern.search(text) for pattern in _PII_PATTERNS.values())


def redact_pii(text):
    redacted = text
    for label, pattern in _PII_PATTERNS.items():
        redacted = pattern.sub(f"[REDACTED_{label.upper()}]", redacted)
    return redacted

def is_out_of_scope(question):
    response = ollama.chat(
        model=OLLAMA_MODEL,
        messages=[
            {"role": "system", "content": _SCOPE_SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ],
    )
    verdict = response["message"]["content"].strip().upper()
    return "OUTOFSCOPE" in verdict