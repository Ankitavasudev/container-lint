"""Command-line entry point: `container-lint [paths...]`."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable, List

from .linter import DockerComposeLinter, DockerfileLinter, LintIssue

SEVERITY_ORDER = {"info": 1, "warning": 2, "error": 3}
SEVERITY_COLOURS = {"info": "\033[36m", "warning": "\033[33m", "error": "\033[31m"}
COMPOSE_NAMES = {"docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"}


def _default_targets() -> List[Path]:
    """With no arguments, lint the Dockerfiles and compose files in this directory."""
    found = []
    for path in sorted(Path(".").rglob("*")):
        if ".git" in path.parts or not path.is_file():
            continue
        if path.name == "Dockerfile" or path.name.startswith("Dockerfile."):
            found.append(path)
        elif path.name in COMPOSE_NAMES:
            found.append(path)
    return found


def _kind(path: Path) -> str:
    if path.name in COMPOSE_NAMES:
        return "compose"
    return "dockerfile"


def lint_paths(paths: Iterable[Path]) -> List[LintIssue]:
    issues: List[LintIssue] = []
    for path in paths:
        if not path.exists():
            issues.append(LintIssue(str(path), 0, "error", "FILE_READ", "file not found"))
            continue
        if path.is_dir():
            issues.extend(lint_paths(sorted(p for p in path.rglob("*") if p.is_file())))
            continue
        if _kind(path) == "compose":
            issues.extend(DockerComposeLinter().lint(str(path)))
        else:
            issues.extend(DockerfileLinter().lint(str(path)))
    return issues


def _use_colour() -> bool:
    return sys.stdout.isatty()


def print_text(issues: List[LintIssue]) -> None:
    colour = _use_colour()
    for issue in issues:
        reset = "\033[0m" if colour else ""
        prefix = SEVERITY_COLOURS[issue.severity] if colour else ""
        location = f"{issue.file}:{issue.line}" if issue.line else issue.file
        print(f"{prefix}{issue.severity:<7}{reset} {location}  [{issue.rule}] {issue.message}")
    if issues:
        counts = {level: sum(1 for i in issues if i.severity == level) for level in SEVERITY_ORDER}
        print(
            f"\n{len(issues)} issue(s): {counts['error']} error, "
            f"{counts['warning']} warning, {counts['info']} info"
        )
    else:
        print("No issues found.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="container-lint",
        description="Lint Dockerfiles and docker-compose files without a Docker daemon.",
    )
    parser.add_argument(
        "paths", nargs="*", type=Path,
        help="Files or directories to lint (default: scan the current directory)",
    )
    parser.add_argument(
        "--format", choices=["text", "json"], default="text", help="Output format",
    )
    parser.add_argument(
        "--fail-on", choices=["error", "warning", "info", "never"], default="warning",
        help="Lowest severity that makes the command exit non-zero (default: warning)",
    )
    return parser


def main(argv: "list[str] | None" = None) -> int:
    args = build_parser().parse_args(argv)

    targets = args.paths or _default_targets()
    if not targets:
        print("No Dockerfile or docker-compose file found.", file=sys.stderr)
        return 2

    issues = lint_paths(targets)

    if args.format == "json":
        print(json.dumps([issue.as_dict() for issue in issues], indent=2))
    else:
        print_text(issues)

    if args.fail_on == "never":
        return 0
    threshold = SEVERITY_ORDER[args.fail_on]
    return 1 if any(SEVERITY_ORDER[issue.severity] >= threshold for issue in issues) else 0


if __name__ == "__main__":
    sys.exit(main())
