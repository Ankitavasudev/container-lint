# Contributing to container-lint

Thanks for taking a look. The project is small on purpose:

- `container_lint/linter.py` — rules. Two classes, `DockerfileLinter` and
  `DockerComposeLinter`. No I/O beyond reading the file you pass in.
- `container_lint/cli.py` — argument parsing, output, exit codes.
- `tests/` — pytest. No network, no Docker, no fixtures to download.

## Adding a rule

1. Add the check inside `DockerfileLinter.lint_lines` or
   `DockerComposeLinter.lint_data`.
2. Reuse a hadolint id (`DL30xx`) when the check maps onto one; otherwise pick
   the next free id in the file's namespace and document it in the README table.
3. Return a `LintIssue` with a message that says what is wrong **and** what to
   do instead — "Pin the base image" beats "invalid FROM".
4. Add at least one test that would fail without the rule, and one that proves
   the compliant case stays quiet.

## Severities

| Level | Use for |
|---|---|
| `error` | the file will not work, or is a security hole (`privileged: true`) |
| `warning` | a real risk that a reviewer should fix |
| `info` | style / image-size advice |

`--fail-on` decides which level breaks the build, so keep `error` rare.

## Running the checks

```bash
pip install -e . -r requirements-dev.txt
python -m pytest -q
flake8 container_lint tests --max-line-length=120 --ignore=E501,W503
```

Both must be clean before a pull request. CI runs them on Python 3.9 – 3.13.
