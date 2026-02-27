import json
import logging
from typing import Generator

import httpx
from httpx_sse import connect_sse

from .config import AppConfig
from .models import APIResponse, UsageInfo, CostInfo, SearchResult

logger = logging.getLogger(__name__)


class APIError(Exception):
    """Base API error."""

    def __init__(self, message: str, status_code: int | None = None):
        self.status_code = status_code
        super().__init__(message)


class RateLimitError(APIError):
    pass


class AuthenticationError(APIError):
    pass


class PerplexityClient:
    def __init__(self, config: AppConfig):
        self.config = config
        self.client = httpx.Client(
            base_url=config.api_base_url,
            headers={
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(connect=10, read=120, write=10, pool=10),
        )

    def _build_payload(self, messages: list[dict], model: str, **overrides) -> dict:
        payload = {
            "model": model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "top_p": self.config.top_p,
            "stream": True,
            "return_citations": self.config.return_citations,
            "return_related_questions": self.config.return_related_questions,
            "return_images": self.config.return_images,
        }
        if self.config.search_domain_filter:
            payload["search_domain_filter"] = self.config.search_domain_filter
        if self.config.search_recency_filter:
            payload["search_recency_filter"] = self.config.search_recency_filter
        if self.config.search_mode != "web":
            payload["search_mode"] = self.config.search_mode
        if self.config.search_context_size != "medium":
            payload["search_context_size"] = self.config.search_context_size
        payload.update(overrides)
        return payload

    def stream_chat(
        self, messages: list[dict], model: str, **overrides
    ) -> Generator[str | APIResponse, None, None]:
        """
        Stream a chat completion. Yields:
          - str: incremental text tokens (for display)
          - APIResponse: final response object (last yield, after stream ends)
        """
        payload = self._build_payload(messages, model, **overrides)
        previous_content = ""
        final_data = {}

        try:
            with connect_sse(
                self.client, "POST", "/chat/completions", json=payload
            ) as event_source:
                # Check HTTP status before iterating
                if event_source.response.status_code == 401:
                    raise AuthenticationError("Invalid API key", 401)
                if event_source.response.status_code == 402:
                    raise APIError(
                        "Insufficient balance. Top up at perplexity.ai/settings/api", 402
                    )
                if event_source.response.status_code == 429:
                    raise RateLimitError("Rate limited. Wait and retry.", 429)
                if event_source.response.status_code >= 400:
                    raise APIError(
                        f"API error {event_source.response.status_code}",
                        event_source.response.status_code,
                    )

                for sse in event_source.iter_sse():
                    if sse.data == "[DONE]":
                        break

                    try:
                        chunk = json.loads(sse.data)
                    except json.JSONDecodeError:
                        continue

                    final_data = chunk

                    # Extract content — handle cumulative mode
                    delta_content = ""
                    choices = chunk.get("choices", [])
                    if choices:
                        choice = choices[0]
                        content = (
                            choice.get("delta", {}).get("content", "")
                            or choice.get("message", {}).get("content", "")
                            or ""
                        )

                        if content:
                            if len(content) > len(previous_content) and content.startswith(
                                previous_content
                            ):
                                # Cumulative: extract only the new part
                                delta_content = content[len(previous_content) :]
                            elif content != previous_content:
                                # True delta or first chunk
                                delta_content = content
                            previous_content = (
                                content
                                if len(content) >= len(previous_content)
                                else previous_content + content
                            )

                    if delta_content:
                        yield delta_content

        except (AuthenticationError, RateLimitError, APIError):
            raise
        except httpx.TimeoutException:
            raise APIError("Request timed out. The server took too long to respond.")
        except httpx.TransportError as e:
            raise APIError(f"Network error: {e}")

        # Parse the final chunk for metadata
        yield self._parse_final_response(final_data, previous_content)

    def _parse_final_response(self, data: dict, full_content: str) -> APIResponse:
        """Extract citations, usage, cost from the final SSE chunk."""
        citations = data.get("citations", []) or []

        search_results_raw = data.get("search_results", []) or []
        search_results = [
            SearchResult(
                title=sr.get("title", ""),
                url=sr.get("url", ""),
                snippet=sr.get("snippet", ""),
                date=sr.get("date"),
                source=sr.get("source", "web"),
            )
            for sr in search_results_raw
        ]

        usage_raw = data.get("usage", {})
        usage = UsageInfo(
            prompt_tokens=usage_raw.get("prompt_tokens", 0),
            completion_tokens=usage_raw.get("completion_tokens", 0),
            total_tokens=usage_raw.get("total_tokens", 0),
            citation_tokens=usage_raw.get("citation_tokens", 0),
            reasoning_tokens=usage_raw.get("reasoning_tokens", 0),
            num_search_queries=usage_raw.get("num_search_queries", 0),
        )

        cost_raw = usage_raw.get("cost", {})
        cost = CostInfo(
            input_tokens_cost=cost_raw.get("input_tokens_cost", 0),
            output_tokens_cost=cost_raw.get("output_tokens_cost", 0),
            reasoning_tokens_cost=cost_raw.get("reasoning_tokens_cost", 0),
            citation_tokens_cost=cost_raw.get("citation_tokens_cost", 0),
            search_queries_cost=cost_raw.get("search_queries_cost", 0),
            total_cost=cost_raw.get("total_cost", 0),
        )

        related = data.get("related_questions", []) or []

        return APIResponse(
            content=full_content,
            citations=citations,
            search_results=search_results,
            related_questions=related,
            usage=usage,
            cost=cost,
            model=data.get("model", ""),
            finish_reason=data.get("choices", [{}])[0].get("finish_reason", ""),
        )

    def close(self):
        self.client.close()
