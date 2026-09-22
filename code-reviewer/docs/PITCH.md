# Judge-facing pitch notes

Use this as a script/cheat-sheet when presenting.

## 30-second elevator pitch

"AI Code Reviewer is a full-stack web app that reviews source code the way
a senior engineer would — combining deterministic, open-source static
analysis (Bandit, Pylint, Radon) with an open-source LLM to catch bugs,
security issues, performance problems, and style violations. Unlike most
AI-review demos, it runs 100% free and offline using Ollama, so anyone —
students, hobbyists, small teams — can use it without a cloud subscription
or API key."

## What to demo, in order

1. **Paste genuinely buggy code** (see `examples/` ideas below) and click
   "Review Code" — show the score, the categorized findings, and that
   Bandit/Pylint/Radon chips appear alongside LLM findings.
2. **Open `/docs`** (Swagger UI) to show the auto-generated, fully
   documented REST API — proves production-grade API design, not a script.
3. **Show `docker-compose up --build`** running the entire stack (frontend +
   backend + local LLM) with one command — proves it's genuinely
   deployable, not just "runs on my machine."
4. **Show the `.env.example`** and mention Groq/Hugging Face fallback —
   proves the architecture isn't locked to one vendor.
5. **Open `llm_service.py`** briefly to show the abstract base class /
   factory pattern — this is the single best "impress a technical judge"
   moment: it demonstrates real software-engineering maturity, not just
   "call an API."

## Suggested demo snippets

**Security issue (Bandit will catch this):**
```python
import subprocess

def run_command(user_input):
    subprocess.call(user_input, shell=True)
```

**Logic bug (LLM should catch this, Bandit won't):**
```python
def calculate_average(numbers):
    total = 0
    for n in numbers:
        total = total + n
    return total / len(numbers)  # crashes on empty list
```

**High complexity (Radon will flag this):**
A deeply nested function with many branching `if`/`elif` statements.

## Anticipated judge questions & answers

- **"Why not just use ChatGPT directly?"** — A raw chat UI gives
  unstructured prose and no deterministic guarantees. This app returns
  structured, machine-readable JSON (category, severity, line number,
  suggestion) suitable for CI/CD integration, and backs it with
  static-analysis tools that can't hallucinate.

- **"How does it scale / handle cost?"** — Because the default provider is
  a self-hosted open-source model, there is no per-request API cost. For
  teams needing more throughput, the same code works unchanged against
  Groq's fast free tier or a self-hosted vLLM cluster — just an env var.

- **"Is it secure?"** — Code is analyzed in an isolated temporary file,
  never executed (`eval`/`exec` are never used), subprocess calls have
  timeouts, and the container runs as a non-root user.

- **"What's the accuracy of the score?"** — The score is an intentionally
  transparent, explainable heuristic (fixed penalty per finding by
  severity), not a second black-box AI call — every point lost is traceable
  to a specific finding.
