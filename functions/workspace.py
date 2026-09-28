"""Descriptor-relative file access. All symlinks in paths are rejected."""

import os
import stat
from contextlib import contextmanager


class WorkspaceError(ValueError):
    pass


def path_parts(path, *, allow_root=False):
    if not isinstance(path, str) or "\x00" in path or os.path.isabs(path):
        raise WorkspaceError("Paths must be relative to the working directory")
    parts = [part for part in path.split("/") if part not in ("", ".")]
    if ".." in parts:
        raise WorkspaceError("Parent directory traversal is not permitted")
    if not parts and not allow_root:
        raise WorkspaceError("A file path is required")
    return parts


@contextmanager
def directory_fd(working_directory, parts=(), *, create=False):
    # Walk from / so a symlink in an ancestor cannot redirect the root either.
    root_parts = os.path.abspath(working_directory).split("/")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    fd = os.open("/", flags)
    try:
        for part in filter(None, root_parts):
            next_fd = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        for part in parts:
            if create:
                try:
                    os.mkdir(part, mode=0o700, dir_fd=fd)
                except FileExistsError:
                    pass
            next_fd = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        yield fd
    finally:
        os.close(fd)


@contextmanager
def regular_file_fd(working_directory, file_path):
    parts = path_parts(file_path)
    with directory_fd(working_directory, parts[:-1]) as parent:
        fd = os.open(
            parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
            dir_fd=parent,
        )
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                raise WorkspaceError("Path is not a regular file")
            yield fd
        finally:
            os.close(fd)


def file_error(exc):
    if isinstance(exc, WorkspaceError):
        return f"Error: {exc}"
    if isinstance(exc, UnicodeError):
        return "Error: File is not valid UTF-8 text"
    return f"Error: File operation failed ({getattr(exc, 'strerror', None) or type(exc).__name__})"
