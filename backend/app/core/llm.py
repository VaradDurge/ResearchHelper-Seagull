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

