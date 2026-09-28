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

def run_python_file(working_directory: str, file_path: str, args: list[str] | None = None) -> str:
    """Run standard-library Python in a read-only, network-isolated Linux sandbox."""
    import selectors
    import shutil
    import signal
    import sys
    import time
    from pathlib import Path

    from config import (
        EXECUTION_TIMEOUT_SECONDS, EXECUTION_MEMORY_BYTES,
        EXECUTION_CPU_SECONDS, MAX_TOOL_OUTPUT_BYTES,
    )
    from functions.workspace import directory_fd, regular_file_fd, path_parts, file_error

    try:
        parts = path_parts(file_path)
        if not parts[-1].endswith(".py"):
            return "Error: Target must be a Python (.py) file"
        if args is not None and (
            not isinstance(args, list) or len(args) > 100
            or any(not isinstance(arg, str) or "\x00" in arg for arg in args)
            or sum(len(arg) for arg in args) > 10_000
        ):
            return "Error: Arguments must be a list of at most 100 strings totaling at most 10000 characters"
        bwrap = shutil.which("bwrap", path=os.defpath)
        prlimit = shutil.which("prlimit", path=os.defpath)
        interpreter = Path(sys.executable).resolve()
        if sys.platform != "linux" or not bwrap or not prlimit or not interpreter.is_relative_to("/usr"):
            return "Error: Isolated execution requires Linux, Bubblewrap, prlimit, and a Python interpreter installed under /usr"
        with regular_file_fd(working_directory, file_path):
            pass
        with directory_fd(working_directory) as workspace:
            command = [
                prlimit, f"--as={EXECUTION_MEMORY_BYTES}",
                f"--cpu={EXECUTION_CPU_SECONDS}", "--fsize=10485760", "--nofile=64",
                "--", bwrap,
                "--unshare-all", "--unshare-user", "--disable-userns",
                "--die-with-parent", "--new-session", "--cap-drop", "ALL",
                "--clearenv", "--setenv", "PATH", "/usr/bin:/bin",
                "--setenv", "LANG", "C.UTF-8", "--setenv", "HOME", "/tmp",
            ]
            for runtime in ("/usr", "/bin", "/lib", "/lib64"):
                if os.path.isdir(runtime):
                    command.extend(["--ro-bind", runtime, runtime])
            command.extend([
                "--proc", "/proc", "--dev", "/dev", "--size", "16777216", "--tmpfs", "/tmp",
                "--ro-bind", f"/proc/self/fd/{workspace}", "/workspace",
                "--chdir", "/workspace", "--", str(Path(prlimit).resolve()), "--nproc=64", "--",
                str(interpreter), "-B", "-E", "-s", "-S",
                "/workspace/" + "/".join(parts), *(args or []),
            ])
            # Sanitize the launcher too (e.g. LD_PRELOAD), not just the child.
            with subprocess.Popen(
                command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, env={"PATH": os.defpath, "LANG": "C.UTF-8"},
                pass_fds=(workspace,), start_new_session=True,
            ) as process:
                output = {"STDOUT": bytearray(), "STDERR": bytearray()}
                total = 0
                failure = None
                deadline = time.monotonic() + EXECUTION_TIMEOUT_SECONDS
                try:
                    with selectors.DefaultSelector() as selector:
                        selector.register(process.stdout, selectors.EVENT_READ, "STDOUT")
                        selector.register(process.stderr, selectors.EVENT_READ, "STDERR")
                        while selector.get_map():
                            remaining = deadline - time.monotonic()
                            if remaining <= 0:
                                failure = "Execution timed out"
                                break
                            for key, _ in selector.select(min(remaining, 0.1)):
                                data = os.read(key.fileobj.fileno(), min(8192, MAX_TOOL_OUTPUT_BYTES - total + 1))
                                if not data:
                                    selector.unregister(key.fileobj)
                                    continue
                                available = MAX_TOOL_OUTPUT_BYTES - total
                                output[key.data].extend(data[:available])
                                total += min(len(data), available)
                                if len(data) > available:
                                    failure = "Execution output limit exceeded"
                                    break
                            if failure:
                                break
                    if not failure:
                        try:
                            process.wait(timeout=max(0.001, deadline - time.monotonic()))
                        except subprocess.TimeoutExpired:
                            failure = "Execution timed out"
                finally:
                    # Kill the launcher group even when the script closes its pipes.
                    # Bubblewrap's PID namespace/die-with-parent kills descendants.
                    try:
                        if process.poll() is None:
                            os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    process.wait()
                results = []
                if failure:
                    results.append(f"Error: {failure}")
                elif process.returncode:
                    results.append(f"Error: Isolated process exited with code {process.returncode}")
                else:
                    results.append("Process exited with code 0")
                for label, data in output.items():
                    if data:
                        results.append(f"{label}:\n{data.decode('utf-8', errors='replace')}")
                return "\n".join(results)
    except (OSError, ValueError, TypeError) as exc:
        return file_error(exc)
