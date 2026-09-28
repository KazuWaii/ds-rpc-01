# Container image for the FastAPI backend (RAG + RBAC + guardrails).
# Streamlit isn't included here -- it's simplest to deploy separately
# (e.g. Streamlit Community Cloud, which is free and needs no Docker at
# all) pointed at this backend's public URL.

FROM python:3.12-slim

WORKDIR /app

# uv is the same package manager used locally (pyproject.toml/uv.lock).
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Dependencies in their own layer: this only re-runs when pyproject.toml
# or uv.lock actually change, not on every code edit.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY app/ app/
COPY resources/data/ resources/data/
COPY scripts/ scripts/

# Pre-download the embedding model and pre-build the vector index at
# build time, so the container starts ready to serve immediately instead
# of doing this work (and needing network access to Hugging Face) on the
# first incoming request.
RUN uv run python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
RUN uv run python scripts/build_index.py

# Ollama isn't reachable from inside this container -- Groq is the cloud
# LLM backend. GROQ_API_KEY must be supplied at run time (Azure App
# Settings, `docker run -e`, etc.), never baked into the image.
ENV LLM_PROVIDER=groq

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
