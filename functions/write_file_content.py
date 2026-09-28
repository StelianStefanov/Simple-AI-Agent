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
    import secrets
    import stat

    from config import MAX_WRITE_CHARS
    from functions.workspace import directory_fd, path_parts, file_error, WorkspaceError

    try:
        if not isinstance(content, str) or len(content) > MAX_WRITE_CHARS:
            raise WorkspaceError(f"Content must be text of at most {MAX_WRITE_CHARS} characters")
        # Validate encoding before touching an existing file or creating directories.
        encoded = content.encode("utf-8")
        parts = path_parts(file_path)
        with directory_fd(working_directory, parts[:-1], create=True) as parent:
            mode = 0o600
            try:
                existing = os.stat(parts[-1], dir_fd=parent, follow_symlinks=False)
                if not stat.S_ISREG(existing.st_mode):
                    raise WorkspaceError("Target must be a regular file, not a symlink or directory")
                mode = stat.S_IMODE(existing.st_mode) & 0o777
            except FileNotFoundError:
                pass
            temporary = f".agent-write-{secrets.token_hex(16)}"
            fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600, dir_fd=parent)
            try:
                with os.fdopen(fd, "wb") as stream:
                    stream.write(encoded)
                    stream.flush()
                    os.fchmod(stream.fileno(), mode)
                    os.fsync(stream.fileno())
                os.replace(temporary, parts[-1], src_dir_fd=parent, dst_dir_fd=parent)
            finally:
                try:
                    os.unlink(temporary, dir_fd=parent)
                except FileNotFoundError:
                    pass
        return f'Successfully wrote to "{file_path}" ({len(content)} characters written)'
    except (OSError, ValueError, TypeError) as exc:
        return file_error(exc)
