"""
LLM Client Module
Simple wrapper for OpenAI chat completions.
"""
from typing import Optional, List, Dict

from openai import OpenAI

from app.config import settings

_client: Optional[OpenAI] = None


def _get_client() -> OpenAI:
    """Create or return a cached OpenAI client."""
    global _client
    if _client is None:
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not configured")
        _client = OpenAI(api_key=settings.openai_api_key)
    return _client


def generate_completion(
    prompt: str,
    chat_history: Optional[List[Dict[str, str]]] = None,
) -> str:
    """Generate a completion, optionally with conversation history."""
    client = _get_client()

    messages: List[Dict[str, str]] = []

    if chat_history:
        messages.extend(chat_history)

    messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=messages,
        temperature=0.0,
        max_tokens=1500,
    )
    message = response.choices[0].message.content or ""
    return message.strip()


def generate_completion_json(prompt: str) -> str:
    """Generate a completion with strict JSON output. Uses response_format so the model returns valid JSON only."""
    client = _get_client()
    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=2000,
        response_format={"type": "json_object"},
    )
    message = response.choices[0].message.content or ""
    return message.strip()
"""
# LLM Module

## What it does:
Abstraction layer for Large Language Model operations. Supports multiple LLM providers
(OpenAI, Anthropic, Groq, etc.). Handles prompt building, API calls, and response parsing.

## How it works:
- Provides abstract interface for LLM operations
- Supports multiple providers (configurable)
- Handles API calls with retry logic
- Manages rate limiting
- Supports streaming responses

## What to include:
- generate(prompt: str, model: str, **kwargs) -> str
  - Generates text completion
  - Returns generated text
  
- generate_stream(prompt: str, model: str, **kwargs) -> Iterator[str]
  - Generates streaming response
  - Yields text chunks
  
- chat(messages: List[Message], model: str, **kwargs) -> str
  - Chat completion
  - Messages: role (user/assistant/system), content
  
- get_available_models(provider: str) -> List[str]
  - Returns available models for provider
  
- Provider implementations: OpenAIClient, AnthropicClient, GroqClient
- Error handling and retry logic
- Token counting utilities
- Cost estimation (optional)
"""

