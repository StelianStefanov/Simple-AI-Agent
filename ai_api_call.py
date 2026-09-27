import os
import json

from dotenv import load_dotenv
from openai import OpenAI
from openai.types.chat.chat_completion import ChatCompletion
from prompt import system_prompt
from call_function import call_function

from call_function import available_functions


def create_client():
    load_dotenv()
    api_key = os.environ.get("OPENROUTER_API_KEY")

    if api_key is None:
        raise RuntimeError("OPENROUTER_API_KEY is not set in the environment variables.")

    return OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)


def api_call(client, messages, verbose=False):
    response: ChatCompletion = client.chat.completions.create(
        model="openrouter/free",
        messages=messages,
        temperature=0,
        tools=available_functions,
    )

    if verbose:
        if response.usage is not None:
            print(f"Prompt tokens: {response.usage.prompt_tokens}")
            print(f"Response tokens: {response.usage.completion_tokens}")
        else:
            raise RuntimeError(
                "Response usage is None. Unable to retrieve token usage information."
            )

    message = response.choices[0].message
    messages.append(message)

    if message.tool_calls is None or message.tool_calls == []:
        print(message.content)
        return message.content
    else:
        for tool_call in message.tool_calls:
            function_args = json.loads(tool_call.function.arguments or "{}")
            print(f"Calling function: {tool_call.function.name}({function_args})")
            result_message = call_function(tool_call, verbose=verbose)
            messages.append(result_message)
            print(f"-> {result_message['content']}")
        return None
