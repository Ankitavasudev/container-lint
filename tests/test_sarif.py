"""Tests for the SARIF 2.1.0 output."""

import json

from container_lint.linter import LintIssue
from container_lint.sarif import SCHEMA, dumps, to_sarif


def issue(rule="DL3008", severity="warning", line=3, message="apt-get without -y",
          file="Dockerfile"):
    return LintIssue(file, line, severity, rule, message)


def test_log_has_the_required_sarif_shape():
    log = to_sarif([issue()])
    assert log["$schema"] == SCHEMA
    assert log["version"] == "2.1.0"
    run = log["runs"][0]
    assert run["tool"]["driver"]["name"] == "container-lint"
    assert run["tool"]["driver"]["version"] == "2.1.0"


def test_severities_map_to_sarif_levels():
    log = to_sarif([
        issue(severity="error"), issue(severity="warning"), issue(severity="info"),
    ])
    levels = [result["level"] for result in log["runs"][0]["results"]]
    assert levels == ["error", "warning", "note"]


def test_each_rule_is_described_once():
    log = to_sarif([
        issue(rule="DL3008"), issue(rule="DL3008"), issue(rule="DL3007", severity="warning"),
    ])
    rules = log["runs"][0]["tool"]["driver"]["rules"]
    assert [rule["id"] for rule in rules] == ["DL3008", "DL3007"]
    assert rules[0]["helpUri"].endswith("/DL3008")


def test_compose_rules_point_at_our_own_docs():
    rules = to_sarif([issue(rule="DC100")])["runs"][0]["tool"]["driver"]["rules"]
    assert rules[0]["helpUri"].endswith("#rules")


def test_location_uses_forward_slashes_and_a_valid_line():
    log = to_sarif([issue(file="win\\path\\Dockerfile", line=0)])
    location = log["runs"][0]["results"][0]["locations"][0]["physicalLocation"]
    assert location["artifactLocation"]["uri"] == "win/path/Dockerfile"
    assert location["region"]["startLine"] == 1


def test_dumps_is_valid_json():
    payload = json.loads(dumps([issue()]))
    assert payload["runs"][0]["results"][0]["ruleId"] == "DL3008"


def test_no_issues_produces_an_empty_run():
    log = to_sarif([])
    assert log["runs"][0]["results"] == []
    assert log["runs"][0]["tool"]["driver"]["rules"] == []
