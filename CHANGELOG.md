# Changelog

## [1.1.0] - 2026-09-30

### Added
- `--timeout/-t` to set the per-task timeout (default: no limit)
- `--jobs/-j` to limit how many tasks run at once in parallel mode
- `--keep-going/-k`; sequential runs now stop at the first failure by default
- `--version/-V`
- Per-task status lines and a summary on stderr
- Installable package with an `orch` command (`pip install .`)
- Test suite

### Fixed
- Source files were saved with literal `\n` and HTML-escaped quotes, so nothing ran
- Exit code is now 1 when any task fails (was always 0)
- Parallel output from different tasks no longer interleaves
- Timeouts and Ctrl+C now kill the task's whole process tree, not just the shell
- `--quiet` now still shows the output of failed tasks

### Removed
- Hard-coded 5 minute timeout
- Unused Gumroad sales plan and licence-check notes

## [1.0.0] - 2026-02-03

### Added
- Initial release with `run` command
- Sequential and parallel task execution
- Per-task timeout (5 min)
- Quiet mode
