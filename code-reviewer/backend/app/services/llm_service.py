"""
llm_service.py
===============
Provider-agnostic Large Language Model client for generating the narrative
code review.

Design goal — "anyone can run this for free":
    The original brief in this project used Azure OpenAI, which requires a
    paid Azure subscription. To keep this project usable by anyone with a
    laptop, the default provider is **Ollama**: a free, open-source runtime
    that downloads and runs models like `qwen2.5-coder` or `codellama`
    entirely on your own machine — no API key, no cloud bill, no rate
    limits, works offline.

    For people who don't want to run a local model, two free-tier cloud
    options are wired in as drop-in alternatives (Groq, Hugging Face
    Inference API), plus a generic OpenAI-compatible option for advanced
    users. Switching providers is a single environment variable
    (`LLM_PROVIDER`) — no code changes required.

Why an abstract base class:
    Every provider has a slightly different HTTP request/response shape.
    By making them all implement the same `generate()` method, the rest of
    the app (`code_analyzer.py`) never needs to know or care which provider
    is actually running.
"""

import json
import re
from abc import ABC, abstractmethod

import httpx

from app.config import Settings


class LLMProviderError(Exception):
    """Raised when the configured LLM provider fails or is unreachable."""


class BaseLLMProvider(ABC):
    """Common interface every concrete provider must implement."""

    @abstractmethod
    async def generate(self, prompt: str, timeout_seconds: int) -> str:
        """
        Send `prompt` to the underlying model and return its raw text
        response. Implementations should raise `LLMProviderError` on any
        failure (network error, non-200 response, malformed payload).
        """
        raise NotImplementedError


class OllamaProvider(BaseLLMProvider):
    """
    Talks to a local Ollama server (https://ollama.com).

    Setup for the user (documented in README.md too):
        1. Install Ollama.
        2. Run: `ollama pull qwen2.5-coder:7b` (or any other coding model).
        3. Run: `ollama serve` (usually starts automatically).
    This provider requires no API key because the model runs on-device.
    """

    def __init__(self, base_url: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def generate(self, prompt: str, timeout_seconds: int) -> str:
        url = f"{self.base_url}/api/generate"
        payload = {"model": self.model, "prompt": prompt, "stream": False}
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                return data.get("response", "")
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            raise LLMProviderError(
                f"Ollama request failed: {exc}. Is Ollama running at {self.base_url}? "
                f"Try `ollama serve` and `ollama pull {self.model}`."
            ) from exc


class OpenAICompatibleProvider(BaseLLMProvider):
    """
    Talks to any endpoint implementing the OpenAI `/chat/completions` schema.

    This single class covers Groq, self-hosted vLLM/LM Studio, Azure OpenAI,
    and OpenAI itself — they all speak (a compatible superset of) this API.
    """

    def __init__(self, base_url: str, api_key: str, model: str, provider_label: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.provider_label = provider_label

    async def generate(self, prompt: str, timeout_seconds: int) -> str:
        if not self.api_key:
            raise LLMProviderError(
                f"{self.provider_label} is selected but no API key is configured. "
                f"Set the relevant *_API_KEY environment variable, or switch "
                f"LLM_PROVIDER back to 'ollama' to run entirely for free/offline."
            )

        url = f"{self.base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        }
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
        except (httpx.HTTPError, KeyError, json.JSONDecodeError) as exc:
            raise LLMProviderError(f"{self.provider_label} request failed: {exc}") from exc


class HuggingFaceProvider(BaseLLMProvider):
    """
    Talks to the Hugging Face free Inference API
    (https://huggingface.co/docs/api-inference).

    Free tier is rate-limited and best-effort, but requires no payment
    method — good for demos and small-scale use.
    """

    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    async def generate(self, prompt: str, timeout_seconds: int) -> str:
        if not self.api_key:
            raise LLMProviderError(
                "Hugging Face provider is selected but HF_API_KEY is not set. "
                "Create a free token at https://huggingface.co/settings/tokens, "
                "or switch LLM_PROVIDER back to 'ollama'."
            )
        url = f"https://api-inference.huggingface.co/models/{self.model}"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {"inputs": prompt, "parameters": {"max_new_tokens": 1200, "temperature": 0.2}}
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                if isinstance(data, list) and data and "generated_text" in data[0]:
                    return data[0]["generated_text"]
                return json.dumps(data)
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            raise LLMProviderError(f"Hugging Face request failed: {exc}") from exc


def get_llm_provider(settings: Settings) -> BaseLLMProvider:
    """
    Factory function: reads `settings.LLM_PROVIDER` and returns the matching
    concrete provider instance. This is the ONLY place in the codebase that
    needs to know about all providers — everything else depends only on
    `BaseLLMProvider`.
    """
    provider = settings.LLM_PROVIDER.lower()

    if provider == "ollama":
        return OllamaProvider(base_url=settings.OLLAMA_BASE_URL, model=settings.OLLAMA_MODEL)
    if provider == "groq":
        return OpenAICompatibleProvider(
            base_url=settings.GROQ_BASE_URL,
            api_key=settings.GROQ_API_KEY,
            model=settings.GROQ_MODEL,
            provider_label="Groq",
        )
    if provider == "huggingface":
        return HuggingFaceProvider(api_key=settings.HF_API_KEY, model=settings.HF_MODEL)
    if provider == "openai_compatible":
        return OpenAICompatibleProvider(
            base_url=settings.OPENAI_COMPATIBLE_BASE_URL,
            api_key=settings.OPENAI_COMPATIBLE_API_KEY,
            model=settings.OPENAI_COMPATIBLE_MODEL,
            provider_label="OpenAI-compatible endpoint",
        )

    raise LLMProviderError(
        f"Unknown LLM_PROVIDER '{settings.LLM_PROVIDER}'. "
        "Valid options: ollama, groq, huggingface, openai_compatible."
    )


def extract_json_block(text: str) -> str:
    """
    LLMs frequently wrap JSON in markdown code fences (```json ... ```) or
    add a sentence of preamble before/after the JSON object. This helper
    extracts the first plausible top-level JSON object from raw model
    output so `json.loads()` doesn't choke on surrounding text.

    Args:
        text: Raw text returned by the LLM.

    Returns:
        The best-guess JSON substring. If no braces are found, the original
        text is returned unchanged (the caller will then raise a clear
        parsing error).
    """
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        return fenced.group(1)

    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return text[first_brace : last_brace + 1]

    return text
