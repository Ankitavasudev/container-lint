#!/usr/bin/env python3
"""Docker security scanner."""

import re
from typing import List
from dataclasses import dataclass


@dataclass
class SecurityRule:
    id: str
    name: str
    severity: str
    description: str
    fix: str


SECURITY_RULES = [
    SecurityRule("SEC001", "No sudo", "critical", "sudo should not be used", "Remove sudo usage"),
    SecurityRule("SEC002", "No curl pipe bash", "critical", "curl | bash is dangerous", "Download and verify before executing"),
    SecurityRule("SEC003", "No secrets in ENV", "critical", "Secrets should not be in ENV", "Use secrets or mounted files"),
    SecurityRule("SEC004", "Non-root user", "high", "Container should not run as root", "Add USER instruction"),
    SecurityRule("SEC005", "Read-only rootfs", "high", "Root filesystem should be read-only", "Add readOnlyRootFilesystem: true"),
    SecurityRule("SEC006", "No latest tag", "medium", "Using latest tag is risky", "Pin to specific version"),
    SecurityRule("SEC007", "Drop capabilities", "high", "Drop unnecessary capabilities", "Add cap_drop: ALL"),
    SecurityRule("SEC008", "No host network", "high", "Host network is dangerous", "Remove network_mode: host"),
    SecurityRule("SEC009", "No privileged", "critical", "Privileged containers are dangerous", "Remove privileged: true"),
    SecurityRule("SEC010", "Health check", "medium", "Add health check", "Add HEALTHCHECK instruction"),
]


def scan_security(content: str) -> List[SecurityRule]:
    findings = []
    lines = content.split('\n')

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # SEC001: sudo
        if 'sudo' in stripped.lower():
            findings.append(SECURITY_RULES[0])

        # SEC002: curl pipe bash
        if 'curl' in stripped and ('|' in stripped or '||' in stripped) and 'sh' in stripped:
            findings.append(SECURITY_RULES[1])

        # SEC003: secrets in ENV
        secret_patterns = ['password', 'secret', 'key', 'token', 'api_key']
        if stripped.upper().startswith('ENV'):
            for pattern in secret_patterns:
                if pattern in stripped.lower():
                    findings.append(SECURITY_RULES[2])
                    break

        # SEC004: no USER
        if stripped.upper().startswith('USER'):
            findings = [f for f in findings if f.id != "SEC004"]

        # SEC006: latest tag
        if stripped.upper().startswith('FROM') and ':latest' in stripped:
            findings.append(SECURITY_RULES[5])

        # SEC009: privileged
        if 'privileged' in stripped.lower() and 'true' in stripped.lower():
            findings.append(SECURITY_RULES[8])

    # SEC004: Check if USER exists
    has_user = any(l.strip().upper().startswith('USER') for l in lines)
    if not has_user:
        findings.append(SECURITY_RULES[3])

    # SEC010: Check HEALTHCHECK
    has_healthcheck = any(l.strip().upper().startswith('HEALTHCHECK') for l in lines)
    if not has_healthcheck:
        findings.append(SECURITY_RULES[9])

    return findings


def print_security_report(findings: List[SecurityRule]) -> str:
    report = "Security Scan Report\n"
    report += "===================\n\n"

    critical = [f for f in findings if f.severity == "critical"]
    high = [f for f in findings if f.severity == "high"]
    medium = [f for f in findings if f.severity == "medium"]

    report += f"Critical: {len(critical)}\n"
    report += f"High: {len(high)}\n"
    report += f"Medium: {len(medium)}\n\n"

    for f in findings:
        report += f"[{f.severity.upper()}] {f.name}: {f.description}\n"
        report += f"  Fix: {f.fix}\n\n"

    score = 100 - (len(critical) * 20 + len(high) * 10 + len(medium) * 5)
    report += f"Security Score: {max(0, score)}/100\n"

    return report