# Orch CLI

Run shell commands one after another or all at once, with clear per-task results and a meaningful exit code.

```bash
orch run "git pull" "npm install" "npm test"
orch run "npm run lint" "npm test" "npm run typecheck" --parallel
```

## Install

Requires Python 3.9+.

```bash
pipx install git+https://github.com/ShapeZeroSZ/orch-cli
# or
pip install git+https://github.com/ShapeZeroSZ/orch-cli
```

From a clone: `pip install .` (or `pip install -e ".[dev]"` for development).

## Usage

```
orch run [OPTIONS] TASKS...
```

Each task is a shell command, run with your system shell (`sh` on Linux/macOS, `cmd` on Windows). Quote each one.

| Option | Meaning |
|--------|---------|
| `-p`, `--parallel` | Run all tasks at once. Default is sequential. |
| `-j`, `--jobs N` | With `--parallel`, run at most N tasks at a time. |
| `-t`, `--timeout SECONDS` | Kill a task that runs longer than this. `0` (default) means no limit. |
| `-k`, `--keep-going` | Sequential mode: keep going after a task fails. By default orch stops at the first failure, like `&&`. |
| `-q`, `--quiet` | Hide output from tasks that succeed. Failed tasks still show their output. |
| `-V`, `--version` | Print the version. |

### Behaviour

- **Exit code:** `0` if every task succeeded, `1` if any failed, timed out or was skipped, `130` if interrupted with Ctrl+C.
- **Sequential mode** streams each task's output live. Tasks can read from stdin.
- **Parallel mode** collects each task's output and prints it as one block when that task finishes, so output from different tasks never interleaves. Tasks get no stdin.
- **Status lines** (`▶ task`, `ok`, `failed`, the summary) go to stderr, so stdout holds only the tasks' own output.
- **Timeouts and Ctrl+C** stop the task's whole process tree, not just the shell that started it.

### Examples

```bash
# Stop at the first failure (default)
orch run "make build" "make test" "make deploy"

# Run checks at once, at most 2 at a time, and give up on any that take over 10 minutes
orch run -p -j 2 -t 600 "npm run lint" "npm test" "npm run e2e"

# In CI: only show output from what failed
orch run -q -k "pytest" "ruff check ." "mypy src"
```

## Standalone binary

`./build.sh` uses PyInstaller to build a single `orch` executable for the current platform (no Python needed to run it).

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT
