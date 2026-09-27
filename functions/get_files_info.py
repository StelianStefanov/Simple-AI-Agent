import os


schema_get_files_info = {
        "type": "function",
        "function": {
            "name": "get_files_info",
            "description": "Lists files in a specified directory relative to the working directory, providing file size and directory status",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "Directory path to list files from, relative to the working directory (default is the working directory itself)",
                    },
                },
            },
        },
    }


def get_files_info(working_directory: str, directory: str = ".") -> str:
    try:
        absolute_path: str = os.path.abspath(working_directory)  # noqa: PTH100
        target_dir: str = os.path.normpath(os.path.join(absolute_path, directory))  # noqa: PTH118
        
        valid_target_dir: bool = os.path.commonpath([absolute_path, target_dir]) == absolute_path

        if not valid_target_dir:
            return f'Error: Cannot list "{directory}" as it is outside the permitted working directory'

        if not os.path.isdir(target_dir):
            return f'Error: "{directory}" is not a directory'

        
        
        if os.path.isdir(target_dir):
            sub_dirs = os.listdir(target_dir)
            messages = []
            for sub_dir in sub_dirs:
                abs_sub_dir = f"{target_dir}/{sub_dir}"
                size = os.path.getsize(abs_sub_dir)
                is_dir = os.path.isdir(abs_sub_dir)
                messages.append(f"{sub_dir}: file_size={size} bytes, is_dir={is_dir}")
                
            return "\n".join(messages)
    except PermissionError:
        return f'Error: Permission denied when accessing "{directory}"'
    except FileNotFoundError:
        return f'Error: "{directory}" not found (it may have been removed)'
    except ValueError:
        return f'Error: Cannot list "{directory}" as it is outside the permitted working directory'
