"""DataPilot — LLM Client"""
import logging
from abc import ABC, abstractmethod
import anthropic
import httpx
from openai import OpenAI
from app.config import settings

logger = logging.getLogger(__name__)


class LLMClient(ABC):
    @abstractmethod
    def complete(self, system_prompt: str, user_message: str,
                 temperature: float = 0.0, max_tokens: int = 2048) -> str: ...
    @property
    @abstractmethod
    def model_name(self) -> str: ...


class OpenAIClient(LLMClient):
    def __init__(self, model: str = "gpt-4o"):
        self._client = OpenAI(api_key=settings.openai_api_key)
        self._model = model

    def complete(self, system_prompt, user_message, temperature=0.0, max_tokens=2048) -> str:
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

    def complete(self, system_prompt, user_message, temperature=0.0, max_tokens=2048) -> str:
        response = self._client.messages.create(
            model=self._model, max_tokens=max_tokens, temperature=temperature,
            system=system_prompt, messages=[{"role": "user", "content": user_message}])
        return response.content[0].text

    @property
    def model_name(self): return self._model


class OllamaClient(LLMClient):
    def __init__(self, model: str = "llama3.1"):
        self._base_url = settings.ollama_base_url.rstrip("/")
        self._model = model

    def complete(self, system_prompt, user_message, temperature=0.0, max_tokens=2048) -> str:
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
