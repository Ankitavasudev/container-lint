"""SARIF 2.1.0 output, for GitHub code scanning and other SARIF consumers.

SARIF is what GitHub expects from `upload-sarif`, so findings from this linter
can appear in the Security > Code scanning tab next to CodeQL results.
"""

from __future__ import annotations

import json
from typing import Dict, Iterable, List

from .linter import LintIssue

SARIF_VERSION = "2.1.0"
SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"
TOOL_URI = "https://github.com/Ankitavasudev/container-lint"
DOCS_URI = TOOL_URI + "/blob/main/README.md#rules"

# SARIF has three levels; the linter's "info" maps to "note".
LEVELS = {"error": "error", "warning": "warning", "info": "note"}


def _help_uri(rule: str) -> str:
    """hadolint keeps one wiki page per DL rule; compose rules live in our README."""
    if rule.startswith("DL") and rule[2:].isdigit():
        return "https://github.com/hadolint/hadolint/wiki/" + rule
    return DOCS_URI


def _rules(issues: Iterable[LintIssue]) -> List[Dict]:
    """One descriptor per rule that actually fired, in first-seen order."""
    seen: Dict[str, Dict] = {}
    for issue in issues:
        if issue.rule in seen:
            continue
        seen[issue.rule] = {
            "id": issue.rule,
            "name": issue.rule,
            "shortDescription": {"text": issue.message},
            "helpUri": _help_uri(issue.rule),
            "defaultConfiguration": {"level": LEVELS.get(issue.severity, "warning")},
        }
    return list(seen.values())


def _location(issue: LintIssue) -> Dict:
    region = {"startLine": max(1, issue.line)}
    return {
        "physicalLocation": {
            "artifactLocation": {"uri": issue.file.replace("\\", "/")},
            "region": region,
        }
    }


def to_sarif(issues: Iterable[LintIssue], version: str = "2.1.0") -> Dict:
    """Build a SARIF log. Line 0 (file-level findings) is reported as line 1."""
    issues = list(issues)
    return {
        "$schema": SCHEMA,
        "version": SARIF_VERSION,
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "container-lint",
                        "informationUri": TOOL_URI,
                        "version": version,
                        "rules": _rules(issues),
                    }
                },
                "results": [
                    {
                        "ruleId": issue.rule,
                        "level": LEVELS.get(issue.severity, "warning"),
                        "message": {"text": issue.message},
                        "locations": [_location(issue)],
                    }
                    for issue in issues
                ],
            }
        ],
    }


def dumps(issues: Iterable[LintIssue], version: str = "2.1.0") -> str:
    return json.dumps(to_sarif(issues, version), indent=2)
