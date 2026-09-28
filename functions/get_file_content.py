import os
from config import MAX_CHARS

schema_get_file_content = {
    "type": "function",
    "function": {
        "name": "get_file_content",
        "description": "Reads and returns the content of a specified file, relative to the working directory. Truncates content if it exceeds the maximum character limit.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to read, relative to the working directory",
                },
            },
            "required": ["file_path"],
        },
    },
}

def get_file_content(working_directory: str, file_path: str) -> str:
    from functions.workspace import regular_file_fd, file_error

    try:
        with regular_file_fd(working_directory, file_path) as fd:
            with os.fdopen(os.dup(fd), encoding="utf-8") as stream:
                content = stream.read(MAX_CHARS)
                if stream.read(1):
                    content += f'\n[...File "{file_path}" truncated at {MAX_CHARS} characters]'
                return content
    except (OSError, ValueError, TypeError) as exc:
        return file_error(exc)
