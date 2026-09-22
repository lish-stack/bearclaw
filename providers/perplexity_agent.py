"""
Custom Inspect model provider for Perplexity's Agent API.

WHY THIS EXISTS: Inspect's built-in `perplexity/` provider is built on the
OpenAI-compatible chat-completions format (POST /chat/completions, a
`messages` array in, a `choices` array out). Perplexity is retiring that
Sonar Chat Completions API on September 27, 2026, replacing it with the
Agent API -- a genuinely different request/response shape (POST /v1/agent,
an `input` array in, a typed `output` array out, read via `.output_text`).
Inspect's built-in provider does not support this new shape, so a custom
provider is required. See:
https://docs.perplexity.ai/docs/agent-api/migrate-from-sonar/how-to

USAGE: import this module before calling inspect eval so the @modelapi
decorator registers it (see tasks/omission.py and tasks/commission.py,
which import it for you). Then use it with:

    inspect eval tasks/omission.py --model pplx_agent/sonar-pro \
        -T judge=anthropic/claude-sonnet-5

The model name after the slash (e.g. "sonar-pro") is mapped to an Agent
API preset via SONAR_TO_PRESET below, following Perplexity's own suggested
mapping (sonar -> fast, sonar-pro -> low, sonar-reasoning-pro -> medium,
sonar-deep-research -> high). Pass a preset name directly (e.g.
pplx_agent/low) if you'd rather skip the mapping.

LIMITATIONS (v1, kept intentionally simple):
- No streaming.
- No tool-call parsing beyond web_search -- if the model calls other
  tools, their output is not surfaced, only the final output_text.
- No token usage reporting (Inspect will show 0 tokens for this provider;
  this does not affect the eval's correctness, only its usage-cost display).
- temperature/top_p are not sent -- the Agent API's own docs say these are
  silently ignored for many model families, and Perplexity's own presets
  are pretty opinionated already; simplest to omit them rather than send a
  parameter that may or may not apply.

RATE LIMITING: a 429 (rate limit) or 5xx (server error) response raises
PerplexityAPIError, which should_retry() classifies for Inspect's own
built-in retry/backoff -- no manual sleep needed. This was added after a
real 429 during back-to-back test runs produced an empty completion that
got silently treated as a valid (failing) data point instead of being
retried -- see the project doc's Decision Log. Non-retryable errors (401,
400, etc.) still return an empty ModelOutput with the error message
attached, rather than retrying something that will never succeed.
"""

import os
from typing import Any, cast

import httpx

from inspect_ai.model import ChatMessage
from inspect_ai.model._generate_config import GenerateConfig
from inspect_ai.model._model import ModelAPI, RetryDecision
from inspect_ai.model._model_call import ModelCall
from inspect_ai.model._model_output import ModelOutput
from inspect_ai.model._registry import modelapi
from inspect_ai.tool._tool_choice import ToolChoice
from inspect_ai.tool._tool_info import ToolInfo

AGENT_API_URL = "https://api.perplexity.ai/v1/agent"


class PerplexityAPIError(Exception):
    """Raised for retryable Perplexity Agent API errors (429, 5xx). Carries
    the HTTP status code so should_retry() can classify rate-limit vs.
    transient for Inspect's adaptive retry controller."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        super().__init__(message)


# Perplexity's own suggested Sonar -> Agent API preset mapping, per their
# migration guide. Falls back to treating the given name as a preset
# directly (e.g. "low", "fast") if it isn't a recognized Sonar model name.
SONAR_TO_PRESET = {
    "sonar": "fast",
    "sonar-pro": "low",
    "sonar-reasoning": "medium",
    "sonar-reasoning-pro": "medium",
    "sonar-deep-research": "high",
}


@modelapi(name="pplx_agent")
class PerplexityAgentAPI(ModelAPI):
    """Custom provider for Perplexity's Agent API (post-Sonar-sunset)."""

    def should_retry(self, ex: Exception) -> bool | RetryDecision:
        if isinstance(ex, PerplexityAPIError):
            if ex.status_code == 429:
                return RetryDecision.rate_limit()
            if ex.status_code >= 500:
                return RetryDecision.transient()
        return False

    def __init__(
        self,
        model_name: str,
        base_url: str | None = None,
        api_key: str | None = None,
        config: GenerateConfig = GenerateConfig(),
        **model_args: dict[str, Any],
    ) -> None:
        super().__init__(
            model_name=model_name,
            base_url=base_url,
            api_key=api_key,
            api_key_vars=["PERPLEXITY_API_KEY"],
            config=config,
        )
        if self.api_key is None:
            self.api_key = os.environ.get("PERPLEXITY_API_KEY")
        if self.api_key is None:
            raise ValueError(
                "PERPLEXITY_API_KEY environment variable not set -- required "
                "for the pplx_agent provider."
            )
        self.preset = SONAR_TO_PRESET.get(model_name, model_name)
        self.model_args = model_args

    def _messages_to_input(self, messages: list[ChatMessage]) -> list[dict[str, str]]:
        """Convert Inspect's ChatMessage list into the Agent API's `input`
        array format: [{"type": "message", "role": ..., "content": ...}]."""
        input_items = []
        for m in messages:
            # Agent API accepts system/user/assistant roles the same way
            # Sonar did for plain-text messages (per the migration guide's
            # "map messages to input" section).
            input_items.append(
                {"type": "message", "role": m.role, "content": m.text}
            )
        return input_items

    async def generate(
        self,
        input: list[ChatMessage],
        tools: list[ToolInfo],
        tool_choice: ToolChoice,
        config: GenerateConfig,
    ) -> ModelOutput | tuple[ModelOutput, ModelCall]:
        body: dict[str, Any] = {
            "preset": self.preset,
            "input": self._messages_to_input(input),
            # Enable Perplexity's own web search tool -- this is what makes
            # it a genuinely different, search-grounded model rather than a
            # plain chat model, matching what Sonar did by default.
            "tools": [{"type": "web_search"}],
        }
        if config.max_tokens is not None:
            body["max_output_tokens"] = config.max_tokens

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(AGENT_API_URL, json=body, headers=headers)

        model_call = ModelCall.create(body, {"status_code": response.status_code})

        if response.status_code != 200:
            error_text = response.text
            if response.status_code == 429 or response.status_code >= 500:
                # Retryable -- raise so Inspect's own retry/backoff (via
                # should_retry above) handles it, rather than silently
                # returning an empty completion that would be scored as a
                # real (failing) data point.
                raise PerplexityAPIError(
                    response.status_code,
                    f"Perplexity Agent API error {response.status_code}: {error_text}",
                )
            # Non-retryable (401, 400, 403, etc.) -- won't succeed on retry,
            # so surface it as a failed output instead of looping forever.
            return (
                ModelOutput.from_content(
                    model=self.model_name,
                    content="",
                    error=f"Perplexity Agent API error {response.status_code}: {error_text}",
                ),
                model_call,
            )

        data = response.json()
        output_text = self._extract_output_text(data)

        output = ModelOutput.from_content(model=self.model_name, content=output_text)
        return output, model_call

    @staticmethod
    def _extract_output_text(data: dict[str, Any]) -> str:
        """Extract the model's text from a raw Agent API response.

        IMPORTANT: `output_text` is a convenience property Perplexity's own
        SDK computes for you -- it is NOT a literal field in the raw JSON
        body you get back from a direct REST call (confirmed by checking
        Perplexity's own documented raw response examples). The real,
        raw shape is an `output` array of typed items; the ones we care
        about have type "message" and a `content` array of parts, each
        with a `text` field. This mirrors OpenAI's Responses API, which
        the Agent API was explicitly modeled on.
        """
        parts = []
        for item in data.get("output", []):
            if item.get("type") != "message":
                continue
            for part in item.get("content", []):
                text = part.get("text")
                if text:
                    parts.append(text)
        return "\n".join(parts)
