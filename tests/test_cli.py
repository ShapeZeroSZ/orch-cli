import subprocess
import sys
import time

import pytest
from click.testing import CliRunner

from orch_cli import __version__
from orch_cli.cli import cli

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="uses POSIX shell commands")


def run(*args):
    return CliRunner().invoke(cli, ["run", *args])


def test_version():
    result = CliRunner().invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_all_succeed_exit_zero():
    result = run("-q", "true", "true")
    assert result.exit_code == 0
    assert "2/2 tasks succeeded" in result.output


def test_sequential_stops_at_first_failure(tmp_path):
    marker = tmp_path / "ran"
    result = run("-q", "exit 3", f"touch {marker}")
    assert result.exit_code == 1
    assert not marker.exists()
    assert "failed, exit 3" in result.output
    assert "0/2 tasks succeeded" in result.output


def test_keep_going_runs_remaining_tasks(tmp_path):
    marker = tmp_path / "ran"
    result = run("-q", "-k", "false", f"touch {marker}")
    assert result.exit_code == 1
    assert marker.exists()
    assert "1/2 tasks succeeded" in result.output


def test_quiet_hides_success_output_but_shows_failures():
    result = run("-q", "-k", "echo hidden-text", "echo shown-text; exit 1")
    assert "hidden-text" not in result.output
    assert "shown-text" in result.output


def test_parallel_runs_concurrently_and_keeps_output_together():
    start = time.monotonic()
    result = run(
        "--parallel",
        "echo a1; sleep 0.5; echo a2",
        "echo b1; sleep 0.5; echo b2",
    )
    assert result.exit_code == 0
    assert time.monotonic() - start < 0.9
    assert "\na1\na2\n" in result.output
    assert "\nb1\nb2\n" in result.output


def test_parallel_failure_sets_exit_code():
    result = run("-p", "-q", "true", "exit 5")
    assert result.exit_code == 1
    assert "failed, exit 5" in result.output


def test_jobs_limits_concurrency():
    start = time.monotonic()
    result = run("-p", "-j", "1", "sleep 0.3", "sleep 0.3")
    assert result.exit_code == 0
    assert time.monotonic() - start >= 0.6


def test_timeout_kills_whole_task_tree():
    result = run("-t", "0.5", "sleep 30 & sleep 30; wait")
    assert result.exit_code == 1
    assert "timed out" in result.output
    time.sleep(0.2)
    leftover = subprocess.run(["pgrep", "-f", "^sleep 30$"], capture_output=True)
    assert leftover.returncode != 0, leftover.stdout


def test_requires_a_task():
    result = run()
    assert result.exit_code == 2
