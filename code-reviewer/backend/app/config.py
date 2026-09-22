"""
config.py
=========
Centralised application configuration.

Why this file exists:
    Hard-coding URLs, model names, or API keys inside business logic makes an
    app impossible to run on someone else's machine. Every value that could
    change between environments (your laptop, a judge's laptop, a cloud VM)
    lives here and is read from environment variables (or a `.env` file)
    using `pydantic-settings`. This is the standard production pattern used
    by real FastAPI services.

How provider selection works:
    LLM_PROVIDER decides which backend does the "thinking" for the code
    review. All options are free / open-source friendly:

    - "ollama"      (default) -> runs a fully local, open-source LLM
                                  (e.g. CodeLlama, Qwen2.5-Coder, Llama 3.1)
                                  via Ollama. No API key, no internet, no
                                  cost. This is what makes the project
                                  "usable by everyone".
    - "groq"        -> Groq's free-tier cloud API. Very fast, generous free
                                  quota, OpenAI-compatible.
    - "huggingface"           -> Hugging Face's free Inference API.
    - "openai_compatible"     -> any self-hosted or third-party endpoint that
                                  speaks the OpenAI chat-completions schema
                                  (LM Studio, vLLM, Azure OpenAI, OpenAI
                                  itself, etc.). Kept for flexibility, but it
                                  is NOT required to run the project.

    Swapping providers never requires touching business logic — see
    `app/services/llm_service.py`.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Strongly-typed application settings.

    Every attribute below can be overridden by setting an environment
    variable of the same name (case-insensitive), or by adding it to a
    `.env` file in the backend/ directory. See `.env.example` for the
    full list with sensible defaults.
    """

    # ---- General app metadata -------------------------------------------------
    APP_NAME: str = "AI Code Reviewer"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"  # "development" | "production"

    # ---- CORS -------------------------------------------------------------
    # Comma-separated list of origins allowed to call this API from a browser.
    # In production, restrict this to your real frontend domain(s).
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # ---- LLM provider selection --------------------------------------------
    LLM_PROVIDER: str = "ollama"  # "ollama" | "groq" | "huggingface" | "openai_compatible"

    # Ollama (local, free, open-source) — https://ollama.com
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5-coder:7b"

    # Groq (free-tier cloud, OpenAI-compatible) — https://console.groq.com
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.1-8b-instant"
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"

    # Hugging Face free Inference API — https://huggingface.co/inference-api
    HF_API_KEY: str = ""
    HF_MODEL: str = "bigcode/starcoder2-15b"

    # Generic OpenAI-compatible endpoint (self-hosted vLLM, LM Studio, or
    # Azure OpenAI if a judge/user genuinely wants to plug it in).
    OPENAI_COMPATIBLE_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_COMPATIBLE_API_KEY: str = ""
    OPENAI_COMPATIBLE_MODEL: str = "gpt-4o-mini"

    # ---- Request limits -----------------------------------------------------
    MAX_CODE_LENGTH_CHARS: int = 20_000  # guard against huge/abusive payloads
    LLM_REQUEST_TIMEOUT_SECONDS: int = 60

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    """
    Return a cached Settings instance.

    `lru_cache` ensures the .env file / environment is only parsed once per
    process, and every part of the app that calls `get_settings()` shares
    the exact same configuration object.
    """
    return Settings()
