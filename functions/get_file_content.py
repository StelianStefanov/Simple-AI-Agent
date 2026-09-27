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
    try:
        absolute_path: str = os.path.abspath(working_directory)  # noqa: PTH100
        target_file: str = os.path.normpath(os.path.join(absolute_path, file_path))

        valid_target_dir: bool = os.path.commonpath([absolute_path, target_file]) == absolute_path

        if not valid_target_dir:
            return f'Error: Cannot read "{file_path}" as it is outside the permitted working directory'

        if not os.path.isfile(target_file):
            return f'Error: File not found or is not a regular file: "{file_path}"'

        with open(target_file) as f:
            content = f.read(MAX_CHARS)

            if f.read(1):
                content += f'\n[...File "{file_path}" truncated at {MAX_CHARS} characters]'

        return content
    except PermissionError:
        return f'Error: Permission denied when reading "{file_path}"'
    except FileNotFoundError:
        return f'Error: "{file_path}" not found (it may have been removed)'
    except ValueError:
        return f'Error: Cannot read "{file_path}" as it is outside the permitted working directory'
    except UnicodeDecodeError:
        return f'Error: "{file_path}" is not a text file or uses an unsupported encoding'
    except IsADirectoryError:
        return f'Error: "{file_path}" is a directory, not a file'