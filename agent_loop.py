import argparse
import sys

from openai import OpenAIError

from ai_api_call import AgentError, api_call, create_client
from config import MAX_ITERATIONS, MAX_TOTAL_TOKENS
from prompt import system_prompt


def agent_loop(argv=None):
    parser = argparse.ArgumentParser(description="A coding agent with isolated Python execution")
    parser.add_argument("user_prompt", help="User prompt")
    parser.add_argument("--verbose", action="store_true", help="Show tool names and token usage")
    args = parser.parse_args(argv)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": args.user_prompt},
    ]
    remaining = MAX_TOTAL_TOKENS
    try:
        with create_client() as client:
            for _ in range(MAX_ITERATIONS):
                result = api_call(client, messages, verbose=args.verbose, remaining_tokens=remaining)
                remaining -= result.tokens_used
                if result.finished:
                    print(result.text)
                    return 0
        raise AgentError("Iteration limit exceeded")
    except AgentError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except OpenAIError as exc:
        print(f"Error: API request failed ({type(exc).__name__}); check credentials, connectivity, and provider limits", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Error: Interrupted", file=sys.stderr)
        return 130
