import sys
import re
import yaml
from pathlib import Path
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class LintIssue:
    file: str
    line: int
    severity: str  # error, warning, info
    rule: str
    message: str


class DockerfileLinter:
    SECURITY_RULES = [
        ("DL3007", "warning", "Using latest tag is not recommended"),
        ("DL3002", "warning", "Last user should not be root"),
        ("DL3003", "warning", "Use WORKDIR instead of mkdir"),
        ("DL3006", "warning", "Always tag the version of an image explicitly"),
        ("DL3008", "warning", "Pin versions in apt get install"),
        ("DL3009", "info", "Delete the apt-get lists after installing"),
        ("DL3018", "warning", "Pin versions in apk add"),
        ("DL3025", "info", "Use JSON form for CMD"),
    ]

    def lint(self, filepath: str) -> List[LintIssue]:
        issues = []
        try:
            content = Path(filepath).read_text()
            lines = content.splitlines()
        except Exception as e:
            issues.append(LintIssue(filepath, 0, "error", "FILE_READ", str(e)))
            return issues

        from_count = 0
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            if stripped.upper().startswith("FROM "):
                from_count += 1
                if "latest" in stripped.lower() and ":" not in stripped:
                    issues.append(LintIssue(filepath, i, "warning", "DL3007", "Using 'latest' tag"))
                if " as " not in stripped.lower() and from_count > 1:
                    issues.append(LintIssue(filepath, i, "info", "DL3022", "Multi-stage build: name stages"))

            if stripped.upper().startswith("RUN "):
                if "apt-get install" in stripped and "-y" not in stripped:
                    issues.append(LintIssue(filepath, i, "warning", "DL3008", "Add -y flag to apt-get install"))
                if "curl" in stripped and "|" in stripped and "sh" in stripped:
                    issues.append(LintIssue(filepath, i, "warning", "DL4006", "Set SHELL option -o pipefail"))

            if stripped.upper().startswith("COPY ") and "*" not in stripped:
                if "package*.json" not in stripped and "go.mod" not in stripped:
                    if stripped.count("COPY") == 1 and ". " in stripped:
                        pass  # OK

            if stripped.upper().startswith("EXPOSE "):
                ports = re.findall(r"\d+", stripped)
                for p in ports:
                    if int(p) < 1024 and int(p) != 80 and int(p) != 443:
                        issues.append(LintIssue(filepath, i, "info", "DL3013", f"Privileged port {p} exposed"))

        return issues


class DockerComposeLinter:
    def lint(self, filepath: str) -> List[LintIssue]:
        issues = []
        try:
            content = Path(filepath).read_text()
            data = yaml.safe_load(content)
        except yaml.YAMLError as e:
            issues.append(LintIssue(filepath, 0, "error", "YAML_ERROR", str(e)))
            return issues
        except Exception as e:
            issues.append(LintIssue(filepath, 0, "error", "FILE_READ", str(e)))
            return issues

        if not data or "services" not in data:
            issues.append(LintIssue(filepath, 1, "info", "DC001", "No services defined"))
            return issues

        for name, service in data["services"].items():
            if "image" in service:
                img = service["image"]
                if ":latest" in img or ":" not in img:
                    issues.append(LintIssue(filepath, 0, "warning", "DC100", f"Service '{name}' uses latest tag"))

            if "build" in service:
                issues.append(LintIssue(filepath, 0, "info", "DC101", f"Service '{name}' uses build context"))

            if " privileged: true" in str(service):
                issues.append(LintIssue(filepath, 0, "error", "DC200", f"Service '{name}' runs privileged"))

            if "ports" in service:
                for port in service.get("ports", []):
                    if isinstance(port, str) and "0.0.0.0" in port:
                        issues.append(LintIssue(filepath, 0, "warning", "DC300", f"Service '{name}' binds to all interfaces"))

            if "environment" in service:
                env = service["environment"]
                if isinstance(env, list):
                    for e in env:
                        if isinstance(e, str) and ("password" in e.lower() or "secret" in e.lower() or "key" in e.lower()):
                            if "=" in e:
                                val = e.split("=", 1)[1]
                                if val and val not in ["", "changeme", "password"]:
                                    issues.append(LintIssue(filepath, 0, "warning", "DC400", f"Service '{name}': potential hardcoded secret"))

        return issues


def main():
    if len(sys.argv) < 2:
        print("Usage: container-lint <Dockerfile|docker-compose.yml>")
        print("       container-lint --all <directory>")
        sys.exit(1)

    all_issues = []

    if sys.argv[1] == "--all" and len(sys.argv) > 2:
        directory = Path(sys.argv[2])
        for f in directory.rglob("Dockerfile*"):
            all_issues.extend(DockerfileLinter().lint(str(f)))
        for f in directory.rglob("docker-compose*.y*ml"):
            all_issues.extend(DockerComposeLinter().lint(str(f)))
    else:
        filepath = Path(sys.argv[1])
        if "docker-compose" in filepath.name:
            all_issues.extend(DockerComposeLinter().lint(str(filepath)))
        else:
            all_issues.extend(DockerfileLinter().lint(str(filepath)))

    if not all_issues:
        print("No issues found!")
        sys.exit(0)

    errors = sum(1 for i in all_issues if i.severity == "error")
    warnings = sum(1 for i in all_issues if i.severity == "warning")
    infos = sum(1 for i in all_issues if i.severity == "info")

    print(f"\nFound {len(all_issues)} issues ({errors} errors, {warnings} warnings, {infos} info)\n")

    icons = {"error": "ERROR", "warning": "WARN", "info": "INFO"}
    for issue in all_issues:
        print(f"  [{icons[issue.severity]}] {issue.file}:{issue.line} {issue.rule}: {issue.message}")

    print()
    sys.exit(1 if errors > 0 else 0)


if __name__ == "__main__":
    main()