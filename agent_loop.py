import argparse

from ai_api_call import api_call, create_client
from prompt import system_prompt

def agent_loop():
    parser = argparse.ArgumentParser(description="Chatbot")
    parser.add_argument("user_prompt", type=str, help="User prompt")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    args = parser.parse_args()

    if args.verbose:
        print(f"User prompt: {args.user_prompt}")

    client = create_client()
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": args.user_prompt},
    ]

    iterations = 20
    for _ in range(iterations):
        result = api_call(client, messages, verbose=args.verbose)
        if result is not None:
            # Model gave a final text response (no tool calls), we're done
            return

    print("INFO: The iterations limit has been exceeded! Exiting...")
    exit(1)