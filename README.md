# Simple AI Agent

A small coding agent based on a Boot.dev exercise. It uses an OpenRouter API model
to inspect and edit the included calculator project and run Python in isolation.

## Setup and usage

Requires Python 3.14 or newer. File tools and execution isolation target Linux.
Install dependencies with `uv sync --locked`. For execution, install Bubblewrap
(`bwrap`) and util-linux (`prlimit`) through your distribution's package manager.
The Python executable underlying the virtual environment must live under `/usr`.
The kernel must allow unprivileged user namespaces. Missing or unsupported sandbox
features cause execution to fail; the agent never falls back to host execution.

Set `OPENROUTER_API_KEY` in your environment or a local `.env` file. Keep this file
out of version control. Optionally set `OPENROUTER_MODEL` to a tool-capable model;
the default is `openrouter/free`.

```sh
uv run python main.py "Explain how the calculator evaluates expressions"
uv run python main.py "Run the calculator tests" --verbose
```

The workspace is always this project's `calculator/` directory, regardless of the
shell's current directory. Verbose mode logs tool names and token usage, never
complete tool arguments or results. Final model answers are still printed.

## File and execution permissions

- File paths must be relative to the workspace. Parent traversal and symlink path
  components are rejected using descriptor-relative, no-follow filesystem access.
- Reads use UTF-8 and return at most 10,000 characters plus a truncation marker.
  Directory listings are limited to 200 entries and about 10,000 characters.
- Writes accept at most 100,000 characters, create missing parent directories, and
  atomically replace regular files. Failed replacement leaves the original intact.
- Scripts run inside Bubblewrap with isolated namespaces, no host network,
  no inherited credentials, no stdin, and a read-only workspace at `/workspace`.
  The host's `/usr`, `/bin`, and library directories are exposed read-only as the
  runtime; home directories and host `/tmp` are not mounted.
- Only standard-library Python and workspace modules are available. Virtualenv
  packages are not mounted. Scripts can use an ephemeral `/tmp`; persistent
  changes must go through the write tool. Execution produces no bytecode files.
- Execution limits include 30 seconds wall time, 5 seconds CPU per process,
  512 MiB address space per process, 64 processes/threads in the sandbox user
  namespace, 64 open descriptors, 10 MiB per written file, a 16 MiB temporary
  filesystem, and 64 KiB combined stdout/stderr. On timeout or excess output,
  the launcher is killed and the PID namespace cleans up descendants.

Limits live in `config.py` and the runner. Resource limits are not an aggregate
cgroup memory/CPU quota, and Bubblewrap shares the host kernel; this is not a VM
for arbitrary hostile workloads. Keep secrets out of the workspace and runtime
mounts. The model can read workspace contents and send tool results to OpenRouter.
Instructions embedded in files are treated as untrusted by the system prompt;
the filesystem and execution restrictions are enforced independently of that prompt.

The isolation design uses Bubblewrap's [namespace and parent-death options](https://github.com/containers/bubblewrap/blob/main/bwrap.xml)
and Linux [resource limits](https://man7.org/linux/man-pages/man2/getrlimit.2.html).

## Conversation limits and errors

The agent allows at most 20 requests and 8 tool calls per response. Requests cap
completion tokens at 2,000; the conversation has a 120,000-character limit and a
30,000-token budget. Provider usage is counted when available; otherwise a
conservative UTF-8-byte estimate includes messages, schemas, and the reserved
completion budget. This is a local request budget, not a provider billing cap.

API requests use a 30-second timeout and up to two SDK retries. Invalid tool calls
return tool errors so the model can recover. Empty, truncated, filtered, or
otherwise incomplete final responses stop with an error. CLI failures return a
nonzero exit status without printing API response bodies or credentials.

## Tests

Run from this project directory:

```sh
AI_AGENT_REQUIRE_SANDBOX=1 .venv/bin/python -B -m unittest discover -v
.venv/bin/python -B calculator/tests.py
```

Tests use temporary fixtures and mocked API responses; they make no model calls
and do not overwrite calculator files. The required-sandbox flag makes unavailable
isolation fail the suite. Without it, sandbox integration tests report a skip on
unsupported hosts. Coverage includes traversal and symlinks, atomic-write failure,
truncation, malformed tool calls, budgets, API failures, isolated execution,
output limits, timeouts, and calculator grammar.
