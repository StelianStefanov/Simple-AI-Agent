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
    from config import MAX_CHARS, MAX_DIRECTORY_ENTRIES
    from functions.workspace import directory_fd, path_parts, file_error

    try:
        with directory_fd(working_directory, path_parts(directory, allow_root=True)) as fd:
            messages = []
            length = 0
            with os.scandir(fd) as entries:
                for entry in entries:
                    if len(messages) >= MAX_DIRECTORY_ENTRIES:
                        messages.append("[...Directory listing truncated]")
                        break
                    try:
                        info = entry.stat(follow_symlinks=False)
                        line = (
                            f"{entry.name!r}: file_size={info.st_size} bytes, "
                            f"is_dir={entry.is_dir(follow_symlinks=False)}, "
                            f"is_symlink={entry.is_symlink()}"
                        )
                    except OSError:
                        line = f"{entry.name!r}: metadata unavailable"
                    if length + len(line) + 1 > MAX_CHARS:
                        messages.append("[...Directory listing truncated]")
                        break
                    messages.append(line)
                    length += len(line) + 1
            return "\n".join(messages)
    except (OSError, ValueError, TypeError) as exc:
        return file_error(exc)
