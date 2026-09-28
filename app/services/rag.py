import ollama

from app.core.roles import get_allowed_departments
from app.services import vectorstore

OLLAMA_MODEL = "llama3.2"

MAX_RELEVANT_DISTANCE = 0.6

SYSTEM_PROMPT = (
    "You are FinSolve Technologies' internal assistant. Answer the user's question "
    "using ONLY the context provided below. If the context doesn't contain the answer, "
    "say you don't have access to that information rather than guessing. "
    "Keep answers concise."
)

def _build_prompt(question, chunks):
    context = "\n\n".join(
        f"[Source: {c['metadata']['source']} | Section: {c['metadata']['section']}]\n{c['text']}"
        for c in chunks
    )
    return f"Context:\n{context}\n\nQuestion: {question}\n\nAnswer:"

def answer_question(question, role, n_results=4):
    allowed_departments = get_allowed_departments(role)
    chunks = vectorstore.query(question, allowed_departments, n_results=n_results)
    chunks = [c for c in chunks if c["distance"] <= MAX_RELEVANT_DISTANCE]

    if not chunks:
        return {
            "answer": "I couldn't find anything relevant in the documents you have access to.",
            "sources": [],
        }

    prompt = _build_prompt(question, chunks)
    response = ollama.chat(
        model=OLLAMA_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )

    sources = sorted({c["metadata"]["source"] for c in chunks})
    return {"answer": response["message"]["content"], "sources": sources}