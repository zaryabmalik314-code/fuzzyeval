"""
LLM API clients for Groq and Google Gemini.
"""

import os
import asyncio
import httpx
from dataclasses import dataclass


@dataclass
class LLMResponse:
    model_name: str
    provider: str
    response_text: str
    model_id: str
    error: str | None = None


async def query_groq(prompt: str, api_key: str, model: str = "openai/gpt-oss-120b") -> LLMResponse:
    """Send prompt to Groq API (OpenAI-compatible)."""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "max_tokens": 1024,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            text = data["choices"][0]["message"]["content"]
            return LLMResponse(
                model_name=f"Groq ({model.split('-')[0].title()})",
                provider="groq",
                response_text=text,
                model_id=model,
            )
    except Exception as e:
        return LLMResponse(
            model_name=f"Groq ({model})",
            provider="groq",
            response_text="",
            model_id=model,
            error=str(e),
        )


async def query_gemini(prompt: str, api_key: str, model: str = "gemini-3.8-flash") -> LLMResponse:
    """Send prompt to Google Gemini API."""
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                url,
                headers={"Content-Type": "application/json"},
                params={"key": api_key},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.7,
                        "maxOutputTokens": 1024,
                    },
                },
            )
            resp.raise_for_status()
            data = resp.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return LLMResponse(
                model_name=f"Gemini ({model})",
                provider="gemini",
                response_text=text,
                model_id=model,
            )
    except Exception as e:
        return LLMResponse(
            model_name=f"Gemini ({model})",
            provider="gemini",
            response_text="",
            model_id=model,
            error=str(e),
        )


async def query_both(
    prompt: str,
    groq_key: str,
    gemini_key: str,
    groq_model: str = "openai/gpt-oss-120b",
    gemini_model: str = "gemini-3.8-flash",
) -> list[LLMResponse]:
    """Query both LLMs in parallel."""
    results = await asyncio.gather(
        query_groq(prompt, groq_key, groq_model),
        query_gemini(prompt, gemini_key, gemini_model),
    )
    return list(results)
