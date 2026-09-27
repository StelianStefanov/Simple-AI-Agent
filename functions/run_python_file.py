import os 
import subprocess

schema_run_python_file = {
    "type": "function",
    "function": {
        "name": "run_python_file",
        "description": "Executes a Python file relative to the working directory and returns the stdout, stderr, and exit code",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the Python file to execute, relative to the working directory",
                },
                "args": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of command-line arguments to pass to the script",
                },
            },
            "required": ["file_path"],
        },
    },
}

def run_python_file(
    working_directory: str, file_path: str, args: list[str] | None = None
) -> str:
    try:
        absolute_path: str = os.path.abspath(working_directory)  
        target_file: str = os.path.normpath(os.path.join(absolute_path, file_path))
        
        valid_target_dir: bool = os.path.commonpath([absolute_path, target_file]) == absolute_path
            
        if not valid_target_dir:
            return f'Error: Cannot execute "{file_path}" as it is outside the permitted working directory'

        if not os.path.isfile(target_file):
            return f'Error: "{file_path}" does not exist or is not a regular file'

        if target_file[-3:] != ".py":
            return f'Error: "{file_path}" is not a Python file'

        command = ["python", target_file]
        if args is not None:
            command.extend(args)

        completed_process = subprocess.run(command, cwd=absolute_path, capture_output=True, text=True, timeout=30)

        parts = []

        if completed_process.returncode != 0:
            parts.append(f"Process exited with code {completed_process.returncode}")

        if completed_process.stdout:
            parts.append(f"STDOUT:\n{completed_process.stdout}")

        if completed_process.stderr:
            parts.append(f"STDERR:\n{completed_process.stderr}")

        if not parts:
            return "No output produced"

        return "\n".join(parts)
    except subprocess.TimeoutExpired:
        return f'Error: Execution of "{file_path}" timed out after 30 seconds'
    except FileNotFoundError:
        return 'Error: Python interpreter not found'
    except PermissionError:
        return f'Error: Permission denied when executing "{file_path}"'
    except ValueError:
        return f'Error: Cannot execute "{file_path}" as it is outside the permitted working directory'