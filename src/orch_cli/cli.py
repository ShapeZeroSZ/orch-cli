"""Command-line interface for orch."""

from __future__ import annotations

import concurrent.futures
import os
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass

import click

from orch_cli import __version__


@dataclass
class Result:
    index: int
    task: str
    returncode: int | None = None  # None means the task never ran
    output: str = ""
    duration: float = 0.0
    timed_out: bool = False

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and not self.timed_out


class Runner:
    """Runs shell commands, each in its own process group so a timeout or
    Ctrl+C stops the whole command tree, not just the shell."""

    def __init__(self, timeout: float | None) -> None:
        self.timeout = timeout
        self._running: set[subprocess.Popen] = set()
        self._lock = threading.Lock()

    def run(self, index: int, task: str, capture: bool, stdin=None) -> Result:
        start = time.monotonic()
        proc = subprocess.Popen(
            task,
            shell=True,
            stdin=stdin,
            stdout=subprocess.PIPE if capture else None,
            stderr=subprocess.STDOUT if capture else None,
            text=True,
            errors="replace",
            start_new_session=True,
        )
        with self._lock:
            self._running.add(proc)
        timed_out = False
        try:
            output, _ = proc.communicate(timeout=self.timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            self._kill(proc)
            output, _ = proc.communicate()
        finally:
            with self._lock:
                self._running.discard(proc)
        return Result(
            index=index,
            task=task,
            returncode=proc.returncode,
            output=output or "",
            duration=time.monotonic() - start,
            timed_out=timed_out,
        )

    def kill_all(self) -> None:
        with self._lock:
            procs = list(self._running)
        for proc in procs:
            self._kill(proc)

    @staticmethod
    def _kill(proc: subprocess.Popen) -> None:
        try:
            if os.name == "posix":
                os.killpg(proc.pid, signal.SIGKILL)
            else:
                proc.kill()
        except (ProcessLookupError, PermissionError):
            pass


def _status(msg: str, quiet: bool = False) -> None:
    if not quiet:
        click.echo(msg, err=True)


def _describe(r: Result) -> str:
    if r.returncode is None:
        return click.style("skipped", fg="yellow")
    if r.timed_out:
        return click.style(f"timed out after {r.duration:.1f}s", fg="red")
    if r.ok:
        return click.style(f"ok ({r.duration:.1f}s)", fg="green")
    return click.style(f"failed, exit {r.returncode} ({r.duration:.1f}s)", fg="red")


def _print_output(r: Result) -> None:
    if r.output:
        click.echo(r.output, nl=not r.output.endswith("\n"))


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, "-V", "--version", prog_name="orch")
def cli() -> None:
    """Orch CLI - run shell tasks in sequence or in parallel.

    \b
    Examples:
        orch run "git pull" "npm install" "npm test"
        orch run "npm run lint" "npm test" --parallel
    """


@cli.command()
@click.argument("tasks", nargs=-1, required=True)
@click.option(
    "--parallel/--sequential",
    "-p/-s",
    default=False,
    help="Run all tasks at once, or one after another.  [default: sequential]",
)
@click.option(
    "-j",
    "--jobs",
    type=click.IntRange(min=1),
    help="With --parallel, run at most this many tasks at once.  [default: all]",
)
@click.option(
    "-t",
    "--timeout",
    type=click.FloatRange(min=0),
    default=0,
    show_default=True,
    help="Seconds before a task is killed. 0 means no limit.",
)
@click.option(
    "-k",
    "--keep-going",
    is_flag=True,
    help="Sequential mode: keep running after a task fails.",
)
@click.option(
    "-q",
    "--quiet",
    is_flag=True,
    help="Hide output of tasks that succeed; still show failures.",
)
def run(tasks, parallel, jobs, timeout, keep_going, quiet):
    """Run shell TASKS in order, or in parallel with --parallel.

    Sequential runs stop at the first failure unless --keep-going is set.
    Exits 0 if every task succeeded and 1 otherwise.
    """
    runner = Runner(timeout or None)
    try:
        if parallel:
            results = _run_parallel(runner, tasks, jobs, quiet)
        else:
            results = _run_sequential(runner, tasks, keep_going, quiet)
    except KeyboardInterrupt:
        runner.kill_all()
        _status(click.style("Interrupted; stopped running tasks.", fg="red"))
        sys.exit(130)

    succeeded = sum(r.ok for r in results)
    failed = succeeded < len(tasks)
    if len(tasks) > 1 or failed:
        summary = f"{succeeded}/{len(tasks)} tasks succeeded"
        _status(click.style(summary, fg="red" if failed else "green", bold=True))
    sys.exit(1 if failed else 0)


def _run_sequential(runner, tasks, keep_going, quiet):
    results = []
    for i, task in enumerate(tasks):
        _status(click.style(f"▶ {task}", bold=True), quiet)
        # Stream output live unless quiet, in which case it is kept for failures.
        r = runner.run(i, task, capture=quiet)
        results.append(r)
        if not r.ok:
            if quiet:
                _status(click.style(f"▶ {task}", bold=True))
                _print_output(r)
            _status(f"  {_describe(r)}")
            if not keep_going:
                results += [Result(j, t) for j, t in enumerate(tasks[i + 1 :], i + 1)]
                break
        else:
            _status(f"  {_describe(r)}", quiet)
    return results


def _run_parallel(runner, tasks, jobs, quiet):
    results = []
    workers = min(jobs or len(tasks), len(tasks))
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [
            pool.submit(runner.run, i, t, True, subprocess.DEVNULL)
            for i, t in enumerate(tasks)
        ]
        try:
            # Each task's output is printed as one block when it finishes,
            # so output from different tasks never interleaves.
            for fut in concurrent.futures.as_completed(futures):
                r = fut.result()
                results.append(r)
                if quiet and r.ok:
                    continue
                _status(click.style(f"▶ {r.task}", bold=True) + f"  {_describe(r)}")
                _print_output(r)
        except KeyboardInterrupt:
            for fut in futures:
                fut.cancel()
            raise
    return sorted(results, key=lambda r: r.index)


def main() -> None:
    cli()
