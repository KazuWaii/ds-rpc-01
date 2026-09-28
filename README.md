# DS RPC 01: Internal chatbot with role based access control

A RAG-based internal chatbot for a fictional company (FinSolve Technologies), with role-based access control (RBAC), guardrails, and cost monitoring. Built on top of Codebasics's [Resume Project Challenge](https://codebasics.io/challenge/codebasics-gen-ai-data-science-resume-project-challenge) starter repo.

**Live demo**: [chat UI](https://kazuwaii-ds-rpc-01-streamlit-app-bil3rc.streamlit.app/) (log in with one of the test accounts below) -- backed by the API at [ds-rpc-01-api.happydune-d141058e.eastus.azurecontainerapps.io](https://ds-rpc-01-api.happydune-d141058e.eastus.azurecontainerapps.io/docs).

## Architecture

```
User (Streamlit) -> HTTP Basic Auth -> FastAPI -> RAG pipeline:
    1. guardrails.is_out_of_scope(question)   -- reject off-topic questions before retrieval
    2. roles.get_allowed_departments(role)    -- RBAC policy
    3. vectorstore.query(question, allowed)   -- Chroma, filtered by department metadata
    4. llm.chat(messages)                     -- Ollama (local) or Groq (cloud)
    5. guardrails.redact_pii(answer)          -- mask sensitive patterns in the output
    6. monitoring.log_usage(...)              -- token/cost tracking + threshold alert
```

| Layer | File |
|---|---|
| Auth + API | `app/main.py` |
| RBAC policy | `app/core/roles.py` |
| Guardrails (out-of-scope, PII) | `app/core/guardrails.py` |
| Cost/usage tracking | `app/core/monitoring.py` |
| Document chunking | `app/services/ingest.py` |
| Embeddings + vector store | `app/services/vectorstore.py` |
| RAG orchestration | `app/services/rag.py` |
| LLM backend (Ollama/Groq) | `app/services/llm.py` |
| Chat UI | `streamlit_app.py` |

### Roles and departments

| Role | Departments accessible |
|---|---|
| `finance` | finance, general |
| `marketing` | marketing, general |
| `hr` | hr, general |
| `engineering` | engineering, general |
| `admin` (C-level) | all |
| `employee` | general only |

Test accounts (dummy in-memory DB in `app/main.py`): `Sam`/`financepass` (finance), `Bruce`/`securepass` (marketing), `Natasha`/`hrpass123` (hr), `Tony`/`password123` (engineering), `Nick`/`fury123` (admin), `Steve`/`cap123` (employee).

## Local setup

Requires Python 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

Pick an LLM backend by setting `LLM_PROVIDER` (defaults to `ollama` if unset):

- **Ollama (local, free)**: install [Ollama](https://ollama.com/download), then `ollama pull llama3.2`.
- **Groq (cloud, free tier)**: create an API key at [console.groq.com](https://console.groq.com/), then create a `.env` file at the project root:
  ```
  GROQ_API_KEY=your_key_here
  ```
  and set `LLM_PROVIDER=groq` in your environment.

Build the vector index (run whenever the files under `resources/data/` change):

```bash
uv run python scripts/build_index.py
```

Run the API:

```bash
uv run fastapi dev app/main.py --port 8000
```

Run the UI (in a separate terminal, with the API already running):

```bash
uv run streamlit run streamlit_app.py
```

### Other scripts

- `scripts/evaluate_retrieval.py` -- measures retrieval quality (Hit Rate@k, MRR) against a small hand-labeled question set.
- `scripts/explore_embeddings.py` -- hands-on demo of how cosine distance is computed, cross-checked against Chroma's own numbers.

## Deployment (Azure Container Apps)

The backend (`app/`) is deployed as a container; Streamlit isn't included in the image and is meant to be deployed separately (e.g. [Streamlit Community Cloud](https://streamlit.io/cloud), free, no Docker needed) pointed at the deployed API's URL.

**Why Groq instead of Ollama in production**: Ollama only runs locally. A container has no access to it, so the deployed image defaults to `LLM_PROVIDER=groq` (set in the `Dockerfile`).

**Why Azure Container Apps instead of App Service**: it scales to zero when idle, so a low-traffic demo project costs effectively $0/month (within Azure's monthly free grant of 180,000 vCPU-seconds / 2M requests), versus an App Service plan's fixed monthly cost even when idle.

**Why Docker Hub instead of Azure Container Registry**: ACR's cheapest tier costs ~$5/month just to exist. Since the image contains no secrets (`GROQ_API_KEY` is injected at runtime, never baked in), pushing it to a public Docker Hub repository is free and equally safe here.

### Build and push the image

```bash
docker build -t <your-dockerhub-username>/ds-rpc-01:latest .
docker login -u <your-dockerhub-username>
docker push <your-dockerhub-username>/ds-rpc-01:latest
```

### Deploy to Azure

```bash
az extension add --name containerapp --upgrade
az provider register --namespace Microsoft.App --wait
az provider register --namespace Microsoft.OperationalInsights --wait

az group create --name ds-rpc-01-rg --location eastus

az containerapp env create \
  --name ds-rpc-01-env \
  --resource-group ds-rpc-01-rg \
  --location eastus

az containerapp create \
  --name ds-rpc-01-api \
  --resource-group ds-rpc-01-rg \
  --environment ds-rpc-01-env \
  --image docker.io/<your-dockerhub-username>/ds-rpc-01:latest \
  --target-port 8000 \
  --ingress external \
  --secrets "groq-api-key=<your-groq-api-key>" \
  --env-vars "GROQ_API_KEY=secretref:groq-api-key" "LLM_PROVIDER=groq" \
  --cpu 0.5 --memory 1.0Gi \
  --min-replicas 0 --max-replicas 1
```

The command prints the app's public URL, also retrievable with:

```bash
az containerapp show --name ds-rpc-01-api --resource-group ds-rpc-01-rg \
  --query "properties.configuration.ingress.fqdn" -o tsv
```

**Security note**: this exposes the API's dummy hardcoded passwords (`app/main.py`) to the public internet. Fine for a learning project's demo; replace with real hashed credentials before using this pattern for anything real.

**Teardown**: `az group delete --name ds-rpc-01-rg` removes every resource created above in one command.

### Deploy the UI (Streamlit Community Cloud)

1. Push a `requirements.txt` to the repo (already included) -- Streamlit Community Cloud installs from this file, not from `pyproject.toml`.
2. At [share.streamlit.io](https://share.streamlit.io/), create an app from this repo, branch `main`, main file path `streamlit_app.py`.
3. In the app's Secrets, set the deployed backend's URL so the UI stops pointing at `localhost`:
   ```toml
   API_URL = "https://ds-rpc-01-api.happydune-d141058e.eastus.azurecontainerapps.io"
   ```

## Guardrails

- **Out-of-scope detection** (`guardrails.is_out_of_scope`): an LLM classifier call, prompted with few-shot examples, rejects questions unrelated to FinSolve's business before any retrieval happens.
- **PII redaction** (`guardrails.redact_pii`): regex-based masking of credit card numbers, SSN-like patterns, and phone numbers in generated answers. Emails are deliberately not redacted -- they're legitimate business data here (e.g. HR contact info).
- **Relevance threshold** (`rag.MAX_RELEVANT_DISTANCE`): retrieval results past a cosine-distance threshold are dropped, so a role with no relevant documents gets an honest "I don't have access to that" instead of an answer hallucinated from irrelevant context.

## Cost monitoring

Every LLM call logs its token usage and estimated cost to `logs/usage.jsonl` (`app/core/monitoring.py`), and prints an alert once cumulative estimated cost crosses `COST_ALERT_THRESHOLD_USD`. Pricing is configured per-provider in `PRICING_PER_MILLION_TOKENS` (Ollama is $0, local; Groq pricing should be re-checked against [console.groq.com/docs/models](https://console.groq.com/docs/models) periodically).
