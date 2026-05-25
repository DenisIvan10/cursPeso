from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from ..config import settings


class ProviderResult(Dict[str, Any]):
    pass


class BaseProvider:
    name = "base"

    def is_configured(self) -> bool:
        return False

    async def complete(self, system_prompt: str, user_message: str, tool_data: Optional[Dict[str, Any]] = None) -> str:
        raise NotImplementedError


class OpenAIProvider(BaseProvider):
    name = "openai"

    def is_configured(self) -> bool:
        return bool(settings.openai_api_key and settings.openai_model)

    async def complete(self, system_prompt: str, user_message: str, tool_data: Optional[Dict[str, Any]] = None) -> str:
        payload = {
            "model": settings.openai_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"User message: {user_message}\nTool data: {tool_data or {}}",
                },
            ],
            "temperature": 0.2,
        }
        headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
        return data["choices"][0]["message"]["content"].strip()


class GeminiProvider(BaseProvider):
    name = "gemini"

    def is_configured(self) -> bool:
        return bool(settings.gemini_api_key and settings.gemini_model)

    async def complete(self, system_prompt: str, user_message: str, tool_data: Optional[Dict[str, Any]] = None) -> str:
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{settings.gemini_model}:generateContent?key={settings.gemini_api_key}"
        )
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": f"{system_prompt}\n\nUser message: {user_message}\nTool data: {tool_data or {}}"
                        }
                    ]
                }
            ],
            "generationConfig": {"temperature": 0.2},
        }
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()


class OllamaProvider(BaseProvider):
    name = "ollama"

    def is_configured(self) -> bool:
        return bool(settings.ollama_base_url and settings.ollama_model)

    async def complete(self, system_prompt: str, user_message: str, tool_data: Optional[Dict[str, Any]] = None) -> str:
        payload = {
            "model": settings.ollama_model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"User message: {user_message}\nTool data: {tool_data or {}}",
                },
            ],
        }
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(f"{settings.ollama_base_url.rstrip('/')}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
        return data["message"]["content"].strip()


def get_provider_chain() -> list[BaseProvider]:
    providers = {
        "openai": OpenAIProvider(),
        "gemini": GeminiProvider(),
        "ollama": OllamaProvider(),
    }
    return [providers[name] for name in settings.provider_priority if name in providers]
