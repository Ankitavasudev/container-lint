"""Linting rules for Dockerfiles and docker-compose files.

The public surface is deliberately small: construct a linter, call `lint(path)`,
get a list of `LintIssue`. Rules borrow Hadolint's identifiers where they map
cleanly (DL30xx) so existing ignore-lists keep working.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

import yaml


@dataclass(frozen=True)
class LintIssue:
    file: str
    line: int
    severity: str  # error, warning, info
    rule: str
    message: str

    def as_dict(self) -> dict:
        return {
            "file": self.file,
            "line": self.line,
            "severity": self.severity,
            "rule": self.rule,
            "message": self.message,
        }


def _has_tag(image: str) -> bool:
    """A tag or a digest both pin an image; `ubuntu` and `ubuntu:latest` do not."""
    if "@" in image:
        return True
    last = image.rsplit("/", 1)[-1]
    return ":" in last and not last.endswith(":latest")


class DockerfileLinter:
    """Static checks for Dockerfiles. No Docker daemon required."""

    def lint(self, filepath: str) -> List[LintIssue]:
        try:
            content = Path(filepath).read_text(encoding="utf-8")
        except OSError as exc:
            return [LintIssue(filepath, 0, "error", "FILE_READ", str(exc))]
        return self.lint_lines(content.splitlines(), filepath)

    def lint_lines(self, lines: Iterable[str], filepath: str = "<string>") -> List[LintIssue]:
        issues: List[LintIssue] = []
        from_count = 0
        named_stages = 0
        unnamed_froms: List[int] = []
        has_user = False

        for number, raw in enumerate(lines, 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue

            parts = line.split(None, 1)
            instruction = parts[0].upper()
            rest = parts[1] if len(parts) > 1 else ""

            if instruction == "FROM":
                from_count += 1
                image = rest.split(" AS ")[0].split(" as ")[0].strip()
                if not _has_tag(image):
                    issues.append(
                        LintIssue(filepath, number, "warning", "DL3007",
                                  f"Pin the base image: '{image}' has no version tag or digest")
                    )
                if " as " in line.lower():
                    named_stages += 1
                elif from_count > 1:
                    unnamed_froms.append(number)

            elif instruction == "RUN":
                lowered = line.lower()
                if "apt-get install" in lowered and " -y" not in lowered:
                    issues.append(
                        LintIssue(filepath, number, "warning", "DL3008",
                                  "Add -y to apt-get install so the build does not hang")
                    )
                if "apt-get install" in lowered and "rm -rf /var/lib/apt/lists" not in lowered:
                    issues.append(
                        LintIssue(filepath, number, "info", "DL3009",
                                  "Remove /var/lib/apt/lists/* after installing to shrink the layer")
                    )
                if ("curl" in lowered or "wget" in lowered) and "|" in lowered and "sh" in lowered:
                    issues.append(
                        LintIssue(filepath, number, "warning", "DL4006",
                                  "Piping a download into a shell hides failures; set SHELL -o pipefail or verify a checksum")
                    )
                if "apt-get upgrade" in lowered or "apt upgrade" in lowered:
                    issues.append(
                        LintIssue(filepath, number, "warning", "DL3015",
                                  "Avoid upgrade in image builds; rebuild from an updated base instead")
                    )

            elif instruction == "COPY":
                if rest.strip() in (". .", ". ./"):
                    issues.append(
                        LintIssue(filepath, number, "warning", "DL3045",
                                  "Copy specific files, not the whole build context (add a .dockerignore at minimum)")
                    )

            elif instruction == "ADD":
                if "://" in rest:
                    issues.append(
                        LintIssue(filepath, number, "info", "DL3020",
                                  "Prefer COPY; ADD only for local archives")
                    )

            elif instruction == "USER":
                has_user = True
                if rest.strip() in ("root", "0"):
                    issues.append(
                        LintIssue(filepath, number, "warning", "DL3002",
                                  "Do not run the container as root")
                    )

            elif instruction == "CMD":
                if rest and not rest.lstrip().startswith("["):
                    issues.append(
                        LintIssue(filepath, number, "info", "DL3025",
                                  "Use the JSON form of CMD so signals reach the process")
                    )

            elif instruction == "EXPOSE":
                for port in rest.split():
                    digits = "".join(ch for ch in port if ch.isdigit())
                    if digits and int(digits) < 1024 and digits not in ("80", "443"):
                        issues.append(
                            LintIssue(filepath, number, "info", "DL3013",
                                      f"Exposing privileged port {digits}; bind to 8080/8443 instead")
                        )

        if from_count and not has_user:
            issues.append(
                LintIssue(filepath, 0, "warning", "DL3002",
                          "No USER instruction: the container will run as root")
            )

        if from_count > 1 and named_stages == 0:
            for number in unnamed_froms:
                issues.append(
                    LintIssue(filepath, number, "info", "DL3022",
                              "Name this build stage with 'AS <name>' for multi-stage builds")
                )

        return issues


class DockerComposeLinter:
    """Static checks for docker-compose.yml files."""

    SECRET_KEYS = ("password", "passwd", "secret", "token", "api_key", "apikey", "private_key")
    PLACEHOLDERS = {"", "changeme", "change-me", "password", "secret", "xxx", "${PASSWORD}", "${SECRET}"}

    def lint(self, filepath: str) -> List[LintIssue]:
        try:
            data = yaml.safe_load(Path(filepath).read_text(encoding="utf-8"))
        except OSError as exc:
            return [LintIssue(filepath, 0, "error", "FILE_READ", str(exc))]
        except yaml.YAMLError as exc:
            return [LintIssue(filepath, 0, "error", "YAML_ERROR", str(exc))]

        return self.lint_data(data, filepath)

    def lint_data(self, data, filepath: str = "<string>") -> List[LintIssue]:
        issues: List[LintIssue] = []
        if not isinstance(data, dict) or "services" not in data:
            return [LintIssue(filepath, 1, "error", "DC001", "No 'services' section found")]

        services = data.get("services") or {}
        if not isinstance(services, dict):
            return [LintIssue(filepath, 1, "error", "DC002", "'services' must be a mapping")]

        for name, service in services.items():
            if not isinstance(service, dict):
                issues.append(LintIssue(filepath, 0, "error", "DC003", f"Service '{name}' is not a mapping"))
                continue

            image = service.get("image")
            if isinstance(image, str) and not _has_tag(image):
                issues.append(
                    LintIssue(filepath, 0, "warning", "DC100", f"Service '{name}' pins no version: {image}")
                )

            if service.get("privileged") is True:
                issues.append(
                    LintIssue(filepath, 0, "error", "DC200", f"Service '{name}' runs privileged")
                )

            if service.get("network_mode") == "host":
                issues.append(
                    LintIssue(filepath, 0, "warning", "DC201", f"Service '{name}' uses host networking")
                )

            for port in service.get("ports") or []:
                text = str(port)
                if text.startswith("0.0.0.0:") or ":" not in text:
                    issues.append(
                        LintIssue(filepath, 0, "info", "DC300",
                                  f"Service '{name}' publishes {text} on every interface")
                    )

            environment = service.get("environment")
            pairs = {}
            if isinstance(environment, dict):
                pairs = {str(k): str(v) for k, v in environment.items()}
            elif isinstance(environment, list):
                for item in environment:
                    if isinstance(item, str) and "=" in item:
                        key, value = item.split("=", 1)
                        pairs[key] = value

            for key, value in pairs.items():
                lowered = key.lower()
                if any(word in lowered for word in self.SECRET_KEYS):
                    if value not in self.PLACEHOLDERS and not value.startswith("${"):
                        issues.append(
                            LintIssue(filepath, 0, "warning", "DC400",
                                      f"Service '{name}': '{key}' looks like a hardcoded secret")
                        )

        return issues
