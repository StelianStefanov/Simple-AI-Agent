import json

from config import MAX_WRITE_CHARS, WORKING_DIRECTORY
from functions.get_files_info import schema_get_files_info, get_files_info
from functions.get_file_content import schema_get_file_content, get_file_content
from functions.run_python_file import schema_run_python_file, run_python_file
from functions.write_file_content import schema_write_file, write_file

available_functions = [
    schema_get_files_info, schema_get_file_content, schema_run_python_file, schema_write_file,
]
FUNCTIONS = {
    "get_file_content": get_file_content,
    "get_files_info": get_files_info,
    "run_python_file": run_python_file,
    "write_file": write_file,
}
SCHEMAS = {schema["function"]["name"]: schema["function"]["parameters"] for schema in available_functions}
for schema in SCHEMAS.values():
    schema["additionalProperties"] = False


def call_function(tool_call, verbose: bool = False) -> dict:
    name = tool_call.function.name
    response = {"role": "tool", "tool_call_id": tool_call.id}
    try:
        if name not in FUNCTIONS:
            raise ValueError(f"Unknown function: {name}")
        raw = tool_call.function.arguments or "{}"
        if not isinstance(raw, str) or len(raw) > MAX_WRITE_CHARS * 6 + 4096:
            raise ValueError("Tool arguments are too large or are not JSON text")
        arguments = json.loads(raw)
        schema = SCHEMAS[name]
        if not isinstance(arguments, dict):
            raise ValueError("Tool arguments must be a JSON object")
        if arguments.keys() - schema["properties"].keys():
            raise ValueError("Unexpected tool argument")
        if set(schema.get("required", [])) - arguments.keys():
            raise ValueError("Missing required tool argument")
        for key, value in arguments.items():
            kind = schema["properties"][key]["type"]
            if kind == "string" and not isinstance(value, str):
                raise ValueError(f"{key} must be a string")
            if kind == "array" and (not isinstance(value, list) or any(not isinstance(item, str) for item in value)):
                raise ValueError(f"{key} must be an array of strings")
        if verbose:
            print(f"Calling tool: {name}")
        response["content"] = FUNCTIONS[name](working_directory=WORKING_DIRECTORY, **arguments)
    except (ValueError, TypeError, OSError, RecursionError):
        # Do not echo arbitrary arguments, host paths, or secrets into logs/history.
        response["content"] = f"Error: Invalid arguments or failed operation for tool {name}"
    return response
