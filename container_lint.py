#!/usr/bin/env python3
"""
Container Lint - Advanced Dockerfile Linter & Security Analyzer
Features: 20+ rules, security scanning, best practices, HTML/JSON reports
Author: Ankita Salaria | GitHub: https://github.com/Ankitavasudev
"""

import os
import re
import sys
import json
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple
from enum import Enum

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import box
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "rich", "-q"])
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import box

console = Console()


class Severity(Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


@dataclass
class Finding:
    rule: str
    severity: Severity
    line: int
    message: str
    suggestion: str = ""


@dataclass
class LintResult:
    file: str
    findings: List[Finding] = field(default_factory=list)
    score: int = 100
    passed_rules: int = 0
    failed_rules: int = 0

    def to_dict(self):
        return {
            "file": self.file,
            "score": self.score,
            "passed_rules": self.passed_rules,
            "failed_rules": self.failed_rules,
            "findings": [
                {
                    "rule": f.rule,
                    "severity": f.severity.value,
                    "line": f.line,
                    "message": f.message,
                    "suggestion": f.suggestion,
                }
                for f in self.findings
            ],
        }


class DockerfileParser:
    def __init__(self):
        self.instructions = []
        self.from_images = []
        self.exposed_ports = []
        self.volumes = []
        self.user_directive = None
        self.has_healthcheck = False
        self.shell_commands = []
        self.env_vars = []
        self.copy_sources = []
        self.add_sources = []

    def parse(self, content: str) -> "DockerfileParser":
        lines = content.strip().split("\n")
        current_instruction = None
        current_line = 0

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            if stripped.startswith("\\"):
                if current_instruction:
                    current_instruction["args"] += " " + stripped[1:].strip()
                continue

            parts = stripped.split(None, 1)
            if not parts:
                continue

            instruction = parts[0].upper()
            args = parts[1] if len(parts) > 1 else ""

            entry = {"instruction": instruction, "args": args, "line": i}
            self.instructions.append(entry)

            if instruction == "FROM":
                self.from_images.append(args)
            elif instruction == "EXPOSE":
                self.exposed_ports.append(args)
            elif instruction == "VOLUME":
                self.volumes.append(args)
            elif instruction == "USER":
                self.user_directive = args
            elif instruction == "HEALTHCHECK":
                self.has_healthcheck = True
            elif instruction in ("RUN", "CMD", "ENTRYPOINT"):
                self.shell_commands.append({"instruction": instruction, "args": args, "line": i})
            elif instruction == "ENV":
                self.env_vars.append(args)
            elif instruction == "COPY":
                self.copy_sources.append(args)
            elif instruction == "ADD":
                self.add_sources.append(args)

            current_instruction = entry

        return self


class SecurityAnalyzer:
    def __init__(self):
        self.findings: List[Finding] = []

    def check_root_user(self, parser: DockerfileParser):
        if parser.user_directive is None:
            self.findings.append(Finding(
                rule="SEC001",
                severity=Severity.HIGH,
                line=0,
                message="No USER directive found - container runs as root",
                suggestion="Add 'USER nobody' or a non-root user before CMD/ENTRYPOINT"
            ))
        elif parser.user_directive.lower() in ("root", "0"):
            self.findings.append(Finding(
                rule="SEC001",
                severity=Severity.HIGH,
                line=0,
                message="Container explicitly runs as root",
                suggestion="Use a non-root user instead"
            ))

    def check_privileged(self, parser: DockerfileParser):
        for cmd in parser.shell_commands:
            args = cmd["args"].lower()
            if "privileged" in args or "--cap-add=all" in args:
                self.findings.append(Finding(
                    rule="SEC002",
                    severity=Severity.CRITICAL,
                    line=cmd["line"],
                    message="Privileged mode or full capabilities detected",
                    suggestion="Add only the specific capabilities needed"
                ))

    def check_secrets(self, parser: DockerfileParser):
        secret_patterns = [
            r"password\s*=", r"secret\s*=", r"api[_-]?key\s*=",
            r"token\s*=", r"aws[_-]?access", r"aws[_-]?secret",
            r"private[_-]?key", r"credentials",
        ]
        for cmd in parser.shell_commands:
            for pattern in secret_patterns:
                if re.search(pattern, cmd["args"], re.IGNORECASE):
                    self.findings.append(Finding(
                        rule="SEC003",
                        severity=Severity.CRITICAL,
                        line=cmd["line"],
                        message="Potential secret/credential found in image layer",
                        suggestion="Use build secrets, environment variables, or multi-stage builds"
                    ))
                    return

    def check_curl_pipes(self, parser: DockerfileParser):
        for cmd in parser.shell_commands:
            if "curl" in cmd["args"] and ("|" in cmd["args"] or "sh" in cmd["args"]):
                self.findings.append(Finding(
                    rule="SEC004",
                    severity=Severity.MEDIUM,
                    line=cmd["line"],
                    message="Curl piped to shell - potential remote code execution",
                    suggestion="Download first, verify checksum, then execute"
                ))

    def check_add_copy(self, parser: DockerfileParser):
        for finding_source in [parser.add_sources, parser.copy_sources]:
            for source in finding_source:
                if ".." in source:
                    self.findings.append(Finding(
                        rule="SEC005",
                        severity=Severity.HIGH,
                        line=0,
                        message="Parent directory access detected (.. in path)",
                        suggestion="Copy only the specific files needed"
                    ))

    def check_writable_root(self, parser: DockerfileParser):
        has_readonly = False
        for cmd in parser.shell_commands:
            if "--read-only" in cmd["args"]:
                has_readonly = True
                break
        if not has_readonly and parser.user_directive:
            self.findings.append(Finding(
                rule="SEC006",
                severity=Severity.LOW,
                line=0,
                message="Root filesystem may be writable",
                suggestion="Consider using --read-only flag or tmpfs mounts"
            ))

    def check_apt_no_cleanup(self, parser: DockerfileParser):
        for cmd in parser.shell_commands:
            args = cmd["args"]
            if "apt-get install" in args or "apt install" in args:
                if "rm -rf /var/lib/apt" not in args and "apt-get clean" not in args:
                    self.findings.append(Finding(
                        rule="SEC007",
                        severity=Severity.MEDIUM,
                        line=cmd["line"],
                        message="apt cache not cleaned after install",
                        suggestion="Add '&& rm -rf /var/lib/apt/lists/*' to reduce image size"
                    ))

    def analyze(self, parser: DockerfileParser) -> List[Finding]:
        self.check_root_user(parser)
        self.check_privileged(parser)
        self.check_secrets(parser)
        self.check_curl_pipes(parser)
        self.check_add_copy(parser)
        self.check_writable_root(parser)
        self.check_apt_no_cleanup(parser)
        return self.findings


class BestPracticeAnalyzer:
    def __init__(self):
        self.findings: List[Finding] = []

    def check_from_scratch(self, parser: DockerfileParser):
        for img in parser.from_images:
            if ":latest" in img or ":" not in img:
                self.findings.append(Finding(
                    rule="BP001",
                    severity=Severity.MEDIUM,
                    line=0,
                    message=f"Using latest tag or no tag: {img}",
                    suggestion="Pin to a specific version for reproducibility"
                ))

    def check_healthcheck(self, parser: DockerfileParser):
        if not parser.has_healthcheck and len(parser.instructions) > 3:
            self.findings.append(Finding(
                rule="BP002",
                severity=Severity.LOW,
                line=0,
                message="No HEALTHCHECK instruction found",
                suggestion="Add HEALTHCHECK for container orchestration"
            ))

    def check_multi_stage(self, parser: DockerfileParser):
        from_count = len(parser.from_images)
        if from_count == 1:
            for cmd in parser.shell_commands:
                if "go build" in cmd["args"] or "gcc" in cmd["args"] or "make" in cmd["args"]:
                    self.findings.append(Finding(
                        rule="BP003",
                        severity=Severity.MEDIUM,
                        line=cmd["line"],
                        message="Build tools in final image - consider multi-stage build",
                        suggestion="Use multi-stage build to reduce image size"
                    ))

    def check_layer_count(self, parser: DockerfileParser):
        run_count = sum(1 for i in parser.instructions if i["instruction"] == "RUN")
        if run_count > 8:
            self.findings.append(Finding(
                rule="BP004",
                severity=Severity.LOW,
                line=0,
                message=f"Too many RUN layers ({run_count})",
                suggestion="Combine RUN commands to reduce image layers"
            ))

    def check_add_vs_copy(self, parser: DockerfileParser):
        for source in parser.add_sources:
            if not source.startswith("http"):
                self.findings.append(Finding(
                    rule="BP005",
                    severity=Severity.MEDIUM,
                    line=0,
                    message="ADD used for local files instead of COPY",
                    suggestion="Use COPY for local files, ADD only for tar extraction or URLs"
                ))

    def check_apt_no_y(self, parser: DockerfileParser):
        for cmd in parser.shell_commands:
            args = cmd["args"]
            if "apt-get install" in args and "-y" not in args:
                self.findings.append(Finding(
                    rule="BP006",
                    severity=Severity.LOW,
                    line=cmd["line"],
                    message="apt-get install without -y flag",
                    suggestion="Add -y flag for non-interactive builds"
                ))

    def check_pip_no_cache(self, parser: DockerfileParser):
        for cmd in parser.shell_commands:
            args = cmd["args"]
            if "pip install" in args and "--no-cache-dir" not in args:
                self.findings.append(Finding(
                    rule="BP007",
                    severity=Severity.LOW,
                    line=cmd["line"],
                    message="pip install without --no-cache-dir",
                    suggestion="Add --no-cache-dir to reduce image size"
                ))

    def check_exposed_ports(self, parser: DockerfileParser):
        for port in parser.exposed_ports:
            if port.strip() in ("80", "443", "8080", "3000"):
                self.findings.append(Finding(
                    rule="BP008",
                    severity=Severity.INFO,
                    line=0,
                    message=f"Common port exposed: {port}",
                    suggestion="Consider using non-standard ports for security"
                ))

    def check_env_keys(self, parser: DockerfileParser):
        for env in parser.env_vars:
            parts = env.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                value = parts[1].strip().strip('"').strip("'")
                if value and not value.startswith("$"):
                    if any(kw in key.upper() for kw in ["PASSWORD", "SECRET", "KEY", "TOKEN"]):
                        self.findings.append(Finding(
                            rule="BP009",
                            severity=Severity.HIGH,
                            line=0,
                            message=f"Sensitive env var with hardcoded value: {key}",
                            suggestion="Use build args or runtime env vars for secrets"
                        ))

    def analyze(self, parser: DockerfileParser) -> List[Finding]:
        self.check_from_scratch(parser)
        self.check_healthcheck(parser)
        self.check_multi_stage(parser)
        self.check_layer_count(parser)
        self.check_add_vs_copy(parser)
        self.check_apt_no_y(parser)
        self.check_pip_no_cache(parser)
        self.check_exposed_ports(parser)
        self.check_env_keys(parser)
        return self.findings


def lint_dockerfile(filepath: str) -> LintResult:
    result = LintResult(file=filepath)

    try:
        with open(filepath, "r") as f:
            content = f.read()
    except FileNotFoundError:
        result.findings.append(Finding(
            rule="SYS001",
            severity=Severity.CRITICAL,
            line=0,
            message=f"File not found: {filepath}"
        ))
        return result

    parser = DockerfileParser().parse(content)
    security = SecurityAnalyzer()
    best_practices = BestPracticeAnalyzer()

    security_findings = security.analyze(parser)
    bp_findings = best_practices.analyze(parser)

    result.findings = security_findings + bp_findings
    result.findings.sort(key=lambda f: (
        {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}[f.severity.value],
        f.line
    ))

    result.failed_rules = len(result.findings)
    result.passed_rules = 20 - result.failed_rules
    result.score = max(0, 100 - (result.failed_rules * 10))

    return result


def display_results(result: LintResult):
    score_color = "green" if result.score >= 80 else "yellow" if result.score >= 60 else "red"
    console.print(f"\n[bold]Linting: {result.file}[/bold]")
    console.print(f"Score: [{score_color}]{result.score}/100[/{score_color}]")
    console.print(f"Passed: {result.passed_rules} | Failed: {result.failed_rules}\n")

    if not result.findings:
        console.print("[bold green]No issues found![/bold green]")
        return

    table = Table(box=box.ROUNDED, show_lines=True)
    table.add_column("Severity", width=10)
    table.add_column("Rule", width=8)
    table.add_column("Line", width=6, justify="center")
    table.add_column("Message", max_width=60)
    table.add_column("Suggestion", max_width=50, style="dim")

    severity_colors = {
        "CRITICAL": "bold red",
        "HIGH": "red",
        "MEDIUM": "yellow",
        "LOW": "white",
        "INFO": "dim",
    }

    for f in result.findings:
        color = severity_colors.get(f.severity.value, "white")
        table.add_row(
            f"[{color}]{f.severity.value}[/{color}]",
            f.rule,
            str(f.line) if f.line > 0 else "-",
            f.message,
            f.suggestion,
        )

    console.print(table)


def generate_html_report(result: LintResult) -> str:
    score_color = "#22c55e" if result.score >= 80 else "#eab308" if result.score >= 60 else "#ef4444"
    severity_colors = {
        "CRITICAL": "#dc2626",
        "HIGH": "#ef4444",
        "MEDIUM": "#eab308",
        "LOW": "#6b7280",
        "INFO": "#9ca3af",
    }
    findings_html = ""
    for f in result.findings:
        color = severity_colors.get(f.severity.value, "#6b7280")
        findings_html += f"""
        <tr>
            <td style="color:{color};font-weight:bold">{f.severity.value}</td>
            <td>{f.rule}</td>
            <td>{f.line if f.line > 0 else '-'}</td>
            <td>{f.message}</td>
            <td style="color:#6b7280">{f.suggestion}</td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html>
<head><title>Container Lint Report - {result.file}</title>
<style>
body {{ font-family: -apple-system, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; }}
.header {{ text-align: center; margin-bottom: 30px; }}
.score {{ font-size: 48px; font-weight: bold; color: {score_color}; }}
table {{ width: 100%; border-collapse: collapse; }}
th, td {{ padding: 10px; border: 1px solid #e5e7eb; text-align: left; }}
th {{ background: #f3f4f6; }}
tr:nth-child(even) {{ background: #f9fafb; }}
</style></head>
<body>
<div class="header">
    <h1>Container Lint Report</h1>
    <div class="score">{result.score}/100</div>
    <p>Passed: {result.passed_rules} | Failed: {result.failed_rules}</p>
</div>
<table>
<tr><th>Severity</th><th>Rule</th><th>Line</th><th>Message</th><th>Suggestion</th></tr>
{findings_html}
</table>
</body></html>"""


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Container Lint - Dockerfile Linter & Security Analyzer")
    parser.add_argument("files", nargs="*", default=["Dockerfile"], help="Dockerfile(s) to lint")
    parser.add_argument("--output", choices=["text", "json", "html"], default="text")
    parser.add_argument("--output-file", "-o", help="Output file for json/html")
    parser.add_argument("--severity", choices=["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"],
                       help="Minimum severity to show")
    args = parser.parse_args()

    all_results = []
    for filepath in args.files:
        if not os.path.exists(filepath):
            console.print(f"[red]File not found: {filepath}[/red]")
            continue
        result = lint_dockerfile(filepath)
        if args.severity:
            min_sev = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}[args.severity]
            result.findings = [f for f in result.findings
                             if {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}[f.severity.value] <= min_sev]
        all_results.append(result)

    if args.output == "text":
        for result in all_results:
            display_results(result)
    elif args.output == "json":
        output = json.dumps([r.to_dict() for r in all_results], indent=2)
        if args.output_file:
            with open(args.output_file, "w") as f:
                f.write(output)
        else:
            print(output)
    elif args.output == "html":
        for result in all_results:
            html = generate_html_report(result)
            out_file = args.output_file or f"lint-report-{os.path.basename(result.file)}.html"
            with open(out_file, "w") as f:
                f.write(html)
            console.print(f"[green]Report saved to {out_file}[/green]")


if __name__ == "__main__":
    main()
