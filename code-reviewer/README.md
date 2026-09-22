# AI Code Reviewer

An AI-powered web application that analyzes source code and returns
structured, actionable review feedback — bugs, security vulnerabilities,
performance issues, and best-practice violations — combining **real static
analysis tools** with a **free, open-source LLM**.

> Built to run entirely on free and open-source software. No cloud
> subscription, no API key, and no cost is required to use it.

---

## Why this is different from "just call an LLM"

Most AI code-review demos are a thin wrapper around a single prompt. This
project is closer to how real production tools (GitHub Advanced Security,
SonarQube + Copilot, etc.) actually work — **defense in depth**:

| Layer | Tool | What it catches | Reliability |
|---|---|---|---|
| Static analysis | [Bandit](https://github.com/PyCQA/bandit) | Security vulnerabilities (hardcoded secrets, SQL injection patterns, unsafe `eval`, etc.) | 100% deterministic |
| Static analysis | [Pylint](https://pylint.pycqa.org/) | Code smells, unused variables, bad naming, general quality | 100% deterministic |
| Static analysis | [Radon](https://radon.readthedocs.io/) | Cyclomatic complexity / maintainability | 100% deterministic |
| AI review | Open-source LLM (via Ollama / Groq / HF) | Logic bugs, unclear naming, architectural feedback, plain-English explanations | Probabilistic, explained in plain English |

The two layers are merged into one report with a single, transparent 0-100
quality score (a simple weighted penalty per finding — no black-box "AI
score" that nobody can explain).

## Tech stack

- **Backend:** Python, FastAPI, Pydantic v2, httpx
- **Frontend:** React 18, Vite, Monaco Editor (the VS Code editor component)
- **AI:** Pluggable LLM layer — defaults to **Ollama** (fully local & free);
  Groq and Hugging Face free tiers supported as drop-in alternatives
- **Static analysis:** Bandit, Pylint, Radon (Python today; architecture
  supports adding ESLint for JS/TS the same way)
- **Infra:** Docker, Docker Compose, Nginx (reverse proxy + static hosting)
- **Testing:** Pytest

## Architecture

```
┌─────────────┐        HTTP (JSON)        ┌──────────────┐
│   React     │ ───────────────────────▶ │   FastAPI     │
│  (Monaco    │ ◀─────────────────────── │   backend     │
│   Editor)   │      structured review    │               │
└─────────────┘                           └───────┬───────┘
                                                    │
                              ┌─────────────────────┼─────────────────────┐
                              ▼                                           ▼
                    ┌───────────────────┐                     ┌────────────────────┐
                    │  Static analysis  │                     │   LLM provider      │
                    │  Bandit / Pylint  │                     │  (Ollama / Groq /   │
                    │  / Radon          │                     │   Hugging Face)     │
                    └───────────────────┘                     └────────────────────┘
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for a deeper walkthrough
of each component and design decision.

## Quick start (Docker — recommended, one command)

Requires only [Docker](https://www.docker.com/) installed.

```bash
docker compose up --build
```

Then, in a separate terminal, pull a free open-source coding model into the
Ollama container (only needed once — the model is cached in a volume):

```bash
docker exec -it code-reviewer-ollama ollama pull qwen2.5-coder:7b
```

Open the app:

- Frontend: http://localhost
- Backend API docs (Swagger UI): http://localhost:8000/docs

That's it — the entire stack (frontend, backend, and the LLM) runs locally
on your machine for free.

> **No GPU? No problem.** Smaller models like `qwen2.5-coder:1.5b` or
> `codellama:7b-instruct-q4_0` run acceptably on CPU. Swap the model name in
> `docker-compose.yml` (`OLLAMA_MODEL`) and re-pull.

## Running without Docker (local development)

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Visit http://localhost:5173. Vite's dev server proxies `/api/*` calls to
`http://localhost:8000` automatically (see `vite.config.js`).

### Running an LLM locally without Docker

1. Install [Ollama](https://ollama.com/download).
2. `ollama pull qwen2.5-coder:7b`
3. Ollama starts its own server on `http://localhost:11434` automatically —
   no extra step needed. The backend's default `.env` already points at it.

## Using a free cloud LLM instead of a local one

If you don't want to run a model locally (e.g. a low-power laptop), switch
providers with **zero code changes** — just environment variables:

```bash
# backend/.env
LLM_PROVIDER=groq
GROQ_API_KEY=your-free-key-from-console.groq.com
GROQ_MODEL=llama-3.1-8b-instant
```

Or Hugging Face's free Inference API:

```bash
LLM_PROVIDER=huggingface
HF_API_KEY=your-free-token-from-huggingface.co
```

See `backend/.env.example` for every option, and
`backend/app/services/llm_service.py` for how the provider abstraction
works.

## Running the tests

```bash
cd backend
pip install -r requirements.txt
pytest -v
```

Tests mock the LLM provider (so they run instantly, offline, and
deterministically) while still exercising the real static-analysis tools
and the full FastAPI request/response cycle.

## API reference

Interactive, auto-generated docs are available at `/docs` (Swagger UI) and
`/redoc` once the backend is running. Key endpoint:

**`POST /api/review`**

```json
{
  "code": "def add(a, b):\n    return a + b",
  "language": "python",
  "filename": "example.py"
}
```

Returns a `CodeReviewResponse` with `summary`, `findings[]` (each with
`category`, `severity`, `explanation`, `suggestion`), `static_analysis[]`,
`overall_score`, and `model_used`. Full schema: `backend/app/models/schemas.py`.

## Project structure

```
code-reviewer/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app entrypoint
│   │   ├── config.py                # Environment-driven settings
│   │   ├── models/schemas.py        # Pydantic request/response models
│   │   ├── routers/review.py        # HTTP layer
│   │   ├── services/
│   │   │   ├── code_analyzer.py     # Orchestrator
│   │   │   ├── llm_service.py       # Pluggable LLM provider abstraction
│   │   │   ├── static_analysis.py   # Bandit / Pylint / Radon integration
│   │   │   └── language_detector.py
│   │   └── core/logging_config.py
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── api/reviewApi.js
│   │   └── components/ (CodeEditor, ReviewPanel, SeverityBadge, LanguageSelector)
│   ├── nginx.conf
│   └── Dockerfile
├── docker-compose.yml
└── docs/
    ├── ARCHITECTURE.md
    └── PITCH.md
```

## Roadmap / good next steps

- Add ESLint integration for JavaScript/TypeScript static analysis
  (same pattern as `static_analysis.py`'s Python tools).
- Persist review history per user (e.g. SQLite/Postgres) with a login.
- Streaming responses (server-sent events) so the LLM's narrative review
  appears token-by-token instead of after the full response.
- GitHub App integration: run reviews automatically on pull requests.

## License

MIT — free to use, modify, and redistribute.
