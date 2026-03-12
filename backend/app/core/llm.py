"""DataPilot — LLM Client"""
import logging
from abc import ABC, abstractmethod
import anthropic
import httpx
from openai import OpenAI
from app.config import settings

logger = logging.getLogger(__name__)


def _extract_anthropic_usage(usage) -> dict:
    """Convert Anthropic usage object to our standard token dict."""
    return {
        "input": getattr(usage, "input_tokens", 0) or 0,
        "output": getattr(usage, "output_tokens", 0) or 0,
        "cache_read": getattr(usage, "cache_read_input_tokens", 0) or 0,
        "cache_write": getattr(usage, "cache_creation_input_tokens", 0) or 0,
    }


class LLMClient(ABC):
    @abstractmethod
    def complete(self, system_prompt: str, user_message: str,
                 temperature: float = 0.0, max_tokens: int = 2048,
                 cache_system_prompt: bool = False) -> str: ...

    def complete_with_usage(self, system_prompt: str, user_message: str,
                            temperature: float = 0.0, max_tokens: int = 2048,
                            cache_system_prompt: bool = False) -> tuple[str, dict]:
        """Like complete() but also returns token usage dict. Override for real tracking."""
        text = self.complete(system_prompt, user_message, temperature, max_tokens, cache_system_prompt)
        return text, {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0}

    @property
    @abstractmethod
    def model_name(self) -> str: ...


class OpenAIClient(LLMClient):
    def __init__(self, model: str = "gpt-4o"):
        self._client = OpenAI(api_key=settings.openai_api_key)
        self._model = model

    def complete(self, system_prompt, user_message, temperature=0.0, max_tokens=2048,
                 cache_system_prompt: bool = False) -> str:
        response = self._client.chat.completions.create(
            model=self._model, temperature=temperature, max_tokens=max_tokens,
            messages=[{"role": "system", "content": system_prompt},
                      {"role": "user", "content": user_message}])
        return response.choices[0].message.content or ""

    @property
    def model_name(self): return self._model


class AnthropicClient(LLMClient):
    def __init__(self, model: str = "claude-sonnet-4-5"):
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self._model = model

    def complete(self, system_prompt, user_message, temperature=0.0, max_tokens=2048,
                 cache_system_prompt: bool = False) -> str:
        text, _ = self.complete_with_usage(
            system_prompt, user_message, temperature, max_tokens, cache_system_prompt
        )
        return text

    def complete_with_usage(self, system_prompt, user_message, temperature=0.0, max_tokens=2048,
                            cache_system_prompt: bool = False) -> tuple[str, dict]:
        system = (
            [{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}]
            if cache_system_prompt
            else system_prompt
        )
        response = self._client.messages.create(
            model=self._model, max_tokens=max_tokens, temperature=temperature,
            system=system, messages=[{"role": "user", "content": user_message}])
        return response.content[0].text, _extract_anthropic_usage(response.usage)

    @property
    def model_name(self): return self._model


class OllamaClient(LLMClient):
    def __init__(self, model: str = "llama3.1"):
        self._base_url = settings.ollama_base_url.rstrip("/")
        self._model = model

    def complete(self, system_prompt, user_message, temperature=0.0, max_tokens=2048,
                 cache_system_prompt: bool = False) -> str:
        response = httpx.post(f"{self._base_url}/api/chat", timeout=120.0, json={
            "model": self._model, "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
            "messages": [{"role": "system", "content": system_prompt},
                         {"role": "user", "content": user_message}]})
        response.raise_for_status()
        return response.json()["message"]["content"]

    @property
    def model_name(self): return f"ollama/{self._model}"


def get_llm_client() -> LLMClient:
    provider, model = settings.llm_provider, settings.llm_model
    if provider == "openai": return OpenAIClient(model=model)
    if provider == "anthropic": return AnthropicClient(model=model)
    if provider == "ollama": return OllamaClient(model=model)
    raise ValueError(f"Unknown provider: {provider}")
