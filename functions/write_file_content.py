import os

schema_write_file = {
    "type": "function",
    "function": {
        "name": "write_file",
        "description": "Writes content to a specified file relative to the working directory. Creates parent directories if they don't exist. Overwrites the file if it already exists.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to write, relative to the working directory",
                },
                "content": {
                    "type": "string",
                    "description": "The text content to write to the file",
                },
            },
            "required": ["file_path", "content"],
        },
    },
}

def write_file(working_directory: str, file_path: str, content: str) -> str:
    try:
        absolute_path: str = os.path.abspath(working_directory)  
        target_file: str = os.path.normpath(os.path.join(absolute_path, file_path))

        valid_target_dir: bool = os.path.commonpath([absolute_path, target_file]) == absolute_path
        
        if not valid_target_dir:
            return f'Error: Cannot write "{file_path}" as it is outside the permitted working directory'

        if os.path.isdir(target_file):
            return f'Error: Cannot write to "{file_path}" as it is a directory'

        os.makedirs(os.path.dirname(target_file), exist_ok=True)

        with open(target_file, "w") as f:
            f.write(content)

        return f'Successfully wrote to "{file_path}" ({len(content)} characters written)'
    except PermissionError:
        return f'Error: Permission denied when writing to "{file_path}"'
    except IsADirectoryError:
        return f'Error: "{file_path}" is a directory, not a file'
    except FileNotFoundError:
        return f'Error: Path to "{file_path}" not found'
    except ValueError:
        return f'Error: Cannot write "{file_path}" as it is outside the permitted working directory'
    except OSError as e:
        return f'Error: Failed to write "{file_path}": {e.strerror}'