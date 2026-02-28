"""
SUPABASE-NATIVE REAL ESTATE INTELLIGENCE SYSTEM
Groq LLM Client — Async with Semaphore Rate Limiting

FIX [MED-B3]: Retry now catches groq.RateLimitError (HTTP 429),
              groq.APIConnectionError, and groq.APIStatusError (5xx).
              Rate limit errors use longer backoff (min=2s, max=30s).
"""
import asyncio
import json
import structlog
from typing import AsyncGenerator, Optional, List, Dict, Any
from groq import AsyncGroq
import groq as groq_errors
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.core.config import get_settings

logger = structlog.get_logger(__name__)

# FIX [MED-B3]: All retriable exception types from the Groq SDK
_RETRIABLE_EXCEPTIONS = (
    TimeoutError,
    ConnectionError,
    groq_errors.APIConnectionError,   # Network-level connection failure
    groq_errors.APITimeoutError,       # Request timed out
    groq_errors.InternalServerError,   # Groq 5xx — transient
    groq_errors.RateLimitError,        # HTTP 429 — rate limited; MUST retry with backoff
)


class GroqClient:
    """Async Groq client with semaphore-based concurrency limiting."""

    def __init__(self):
        self.settings = get_settings()
        self._client: Optional[AsyncGroq] = None
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._request_count = 0
        self._error_count = 0

    @property
    def client(self) -> AsyncGroq:
        if self._client is None:
            self._client = AsyncGroq(
                api_key=self.settings.groq_api_key,
                timeout=self.settings.groq_timeout,
                max_retries=0,  # We handle retries ourselves
            )
        return self._client

    @property
    def semaphore(self) -> asyncio.Semaphore:
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.settings.groq_max_concurrent)
        return self._semaphore

    @retry(
        stop=stop_after_attempt(4),
        # FIX [MED-B3]: min=2s for rate limit back-off compliance; max=30s
        wait=wait_exponential(multiplier=1.5, min=2, max=30),
        retry=retry_if_exception_type(_RETRIABLE_EXCEPTIONS),
    )
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
        tools: Optional[List[Dict]] = None,
        tool_choice: Optional[str] = None,
        response_format: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Send a chat completion request with semaphore limiting."""
        async with self.semaphore:
            self._request_count += 1
            req_id = self._request_count

            logger.info(
                "groq_request_start",
                request_id=req_id,
                model=model or self.settings.groq_model,
                messages_count=len(messages),
            )

            try:
                kwargs = {
                    "model": model or self.settings.groq_model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
                if tools:
                    kwargs["tools"] = tools
                if tool_choice:
                    kwargs["tool_choice"] = tool_choice
                if response_format:
                    kwargs["response_format"] = response_format

                response = await self.client.chat.completions.create(**kwargs)

                logger.info(
                    "groq_request_complete",
                    request_id=req_id,
                    usage_prompt=response.usage.prompt_tokens if response.usage else 0,
                    usage_completion=response.usage.completion_tokens if response.usage else 0,
                )

                return {
                    "content": response.choices[0].message.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in (response.choices[0].message.tool_calls or [])
                    ],
                    "usage": {
                        "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                        "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                        "total_tokens": response.usage.total_tokens if response.usage else 0,
                    },
                    "model": response.model,
                    "finish_reason": response.choices[0].finish_reason,
                }

            except Exception as e:
                self._error_count += 1
                logger.error(
                    "groq_request_failed",
                    request_id=req_id,
                    error=str(e),
                    error_count=self._error_count,
                )
                raise

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> AsyncGenerator[str, None]:
        """Stream a chat completion response with semaphore limiting."""
        async with self.semaphore:
            self._request_count += 1

            try:
                stream = await self.client.chat.completions.create(
                    model=model or self.settings.groq_model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=True,
                )

                async for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content

            except Exception as e:
                self._error_count += 1
                logger.error("groq_stream_failed", error=str(e))
                raise

    async def function_call(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict],
        tool_choice: str = "auto",
    ) -> Dict[str, Any]:
        """Execute a function-calling request with strict JSON schema enforcement."""
        response = await self.chat(
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
            temperature=0.0,  # Deterministic for function calls
        )

        # Parse tool call arguments
        if response["tool_calls"]:
            for tc in response["tool_calls"]:
                try:
                    tc["function"]["parsed_arguments"] = json.loads(
                        tc["function"]["arguments"]
                    )
                except json.JSONDecodeError:
                    tc["function"]["parsed_arguments"] = None
                    logger.warning(
                        "tool_call_json_parse_failed",
                        tool=tc["function"]["name"],
                    )

        return response

    def get_metrics(self) -> Dict[str, int]:
        """Return client metrics."""
        return {
            "total_requests": self._request_count,
            "total_errors": self._error_count,
            "concurrent_limit": self.settings.groq_max_concurrent,
        }

    async def close(self):
        """Close the client."""
        if self._client:
            await self._client.close()
            self._client = None


# Singleton
_groq_client: Optional[GroqClient] = None


def get_groq_client() -> GroqClient:
    """Get the singleton Groq client."""
    global _groq_client
    if _groq_client is None:
        _groq_client = GroqClient()
    return _groq_client
