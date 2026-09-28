import json
import os
from dataclasses import dataclass

from dotenv import load_dotenv
from openai import OpenAI

from call_function import available_functions, call_function
from config import MAX_COMPLETION_TOKENS, MAX_HISTORY_CHARS, MAX_TOTAL_TOKENS


class AgentError(RuntimeError):
    """A response or budget failure that should stop the agent cleanly."""


@dataclass
class TurnResult:
    finished: bool
    text: str | None
    tokens_used: int


def create_client():
    load_dotenv()
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key or not api_key.strip():
        raise AgentError("OPENROUTER_API_KEY is not set")
    return OpenAI(
        base_url="https://openrouter.ai/api/v1", api_key=api_key,
        timeout=30.0, max_retries=2,
    )


def api_call(client, messages, verbose=False, remaining_tokens=MAX_TOTAL_TOKENS):
    serialized = json.dumps({"messages": messages, "tools": available_functions}, ensure_ascii=False)
    if len(serialized) > MAX_HISTORY_CHARS:
        raise AgentError("Conversation size limit exceeded")
    # Conservative fallback, including schemas, when provider usage is unavailable.
    estimated_input_tokens = len(serialized.encode("utf-8"))
    completion_budget = min(MAX_COMPLETION_TOKENS, remaining_tokens - estimated_input_tokens)
    if completion_budget <= 0:
        raise AgentError("Token budget exhausted before the next request")
    response = client.chat.completions.create(
        model=os.environ.get("OPENROUTER_MODEL", "openrouter/free"), messages=messages,
        temperature=0, tools=available_functions, max_tokens=completion_budget,
    )
    tokens_used = (
        response.usage.total_tokens if response.usage is not None
        else estimated_input_tokens + completion_budget
    )
    if verbose:
        print(f"Tokens used: {tokens_used}" + (" (estimated)" if response.usage is None else ""))
    if not response.choices:
        raise AgentError("Provider returned no response choices")
    choice = response.choices[0]
    if choice.finish_reason not in ("stop", "tool_calls"):
        raise AgentError(f"Provider stopped without a complete response: {choice.finish_reason}")
    if tokens_used > remaining_tokens:
        raise AgentError("Provider reported usage exceeding the remaining token budget")
    message = choice.message
    calls = message.tool_calls or []
    if len(calls) > 8:
        raise AgentError("Too many tool calls in one response (maximum 8)")
    if any(getattr(call, "type", "function") != "function" for call in calls):
        raise AgentError("Provider returned an unsupported tool call type")
    if not calls:
        text = message.content or getattr(message, "refusal", None)
        if not text or not text.strip():
            raise AgentError("Provider returned an empty final response")
        messages.append(message.model_dump(exclude_none=True))
        return TurnResult(True, text, tokens_used)
    messages.append(message.model_dump(exclude_none=True))
    for call in calls:
        messages.append(call_function(call, verbose=verbose))
    return TurnResult(False, None, tokens_used)
