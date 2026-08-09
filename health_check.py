#!/usr/bin/env python3
"""Docker health check validator."""

import re
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class HealthCheckRule:
    id: str
    name: str
    severity: str
    description: str
    fix: str


HEALTH_CHECK_RULES = [
    HealthCheckRule(
        id="HC001",
        name="HEALTHCHECK defined",
        severity="error",
        description="Dockerfile should have HEALTHCHECK instruction",
        fix="Add HEALTHCHECK instruction to monitor container health"
    ),
    HealthCheckRule(
        id="HC002",
        name="HEALTHCHECK interval",
        severity="warning",
        description="HEALTHCHECK interval should be specified",
        fix="Add --interval flag: HEALTHCHECK --interval=30s CMD ..."
    ),
    HealthCheckRule(
        id="HC003",
        name="HEALTHCHECK timeout",
        severity="warning",
        description="HEALTHCHECK timeout should be specified",
        fix="Add --timeout flag: HEALTHCHECK --timeout=10s CMD ..."
    ),
    HealthCheckRule(
        id="HC004",
        name="HEALTHCHECK retries",
        severity="info",
        description="HEALTHCHECK retries should be specified",
        fix="Add --retries flag: HEALTHCHECK --retries=3 CMD ..."
    ),
    HealthCheckRule(
        id="HC005",
        name="HEALTHCHECK CMD",
        severity="error",
        description="HEALTHCHECK must have CMD instruction",
        fix="Add CMD to HEALTHCHECK: HEALTHCHECK CMD curl -f http://localhost/ || exit 1"
    ),
    HealthCheckRule(
        id="HC006",
        name="HEALTHCHECK start period",
        severity="info",
        description="Consider adding --start-period for slow-starting containers",
        fix="Add --start-period: HEALTHCHECK --start-period=30s CMD ..."
    ),
]


@dataclass
class HealthCheckResult:
    rule: HealthCheckRule
    line: int
    message: str
    suggestion: str = ""


def validate_healthcheck(content: str) -> List[HealthCheckResult]:
    results = []
    lines = content.split('\n')
    
    has_healthcheck = False
    healthcheck_line = 0
    
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.upper().startswith('HEALTHCHECK'):
            has_healthcheck = True
            healthcheck_line = i
            
            # HC002: Check interval
            if '--interval' not in stripped:
                results.append(HealthCheckResult(
                    rule=HEALTH_CHECK_RULES[1],
                    line=i,
                    message="HEALTHCHECK missing --interval flag"
                ))
            
            # HC003: Check timeout
            if '--timeout' not in stripped:
                results.append(HealthCheckResult(
                    rule=HEALTH_CHECK_RULES[2],
                    line=i,
                    message="HEALTHCHECK missing --timeout flag"
                ))
            
            # HC004: Check retries
            if '--retries' not in stripped:
                results.append(HealthCheckResult(
                    rule=HEALTH_CHECK_RULES[3],
                    line=i,
                    message="HEALTHCHECK missing --retries flag"
                ))
            
            # HC005: Check CMD
            if 'CMD' not in stripped:
                # Check next lines for CMD
                for j in range(i, min(i+5, len(lines))):
                    if lines[j].strip().upper().startswith('CMD'):
                        break
                else:
                    results.append(HealthCheckResult(
                        rule=HEALTH_CHECK_RULES[4],
                        line=i,
                        message="HEALTHCHECK missing CMD instruction"
                    ))
            
            # HC006: Check start period
            if '--start-period' not in stripped:
                results.append(HealthCheckResult(
                    rule=HEALTH_CHECK_RULES[5],
                    line=i,
                    message="Consider adding --start-period for slow-starting containers"
                ))
    
    # HC001: Check if HEALTHCHECK exists
    if not has_healthcheck:
        results.append(HealthCheckResult(
            rule=HEALTH_CHECK_RULES[0],
            line=0,
            message="No HEALTHCHECK instruction found in Dockerfile"
        ))
    
    return results


def export_healthcheck_report(results: List[HealthCheckResult], filename: str):
    rows = ""
    for r in results:
        severity_class = r.rule.severity.lower()
        rows += f"""
        <tr>
            <td>{r.rule.id}</td>
            <td>{r.rule.name}</td>
            <td class="{severity_class}">{r.rule.severity.upper()}</td>
            <td>Line {r.line}</td>
            <td>{r.message}</td>
            <td>{r.suggestion or r.rule.fix}</td>
        </tr>"""
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Docker Health Check Report</title>
    <style>
        body {{ font-family: system-ui; max-width: 1200px; margin: 0 auto; padding: 20px; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #f5f5f5; }}
        .error {{ color: red; font-weight: bold; }}
        .warning {{ color: orange; font-weight: bold; }}
        .info {{ color: blue; font-weight: bold; }}
        h1 {{ color: #333; }}
        .summary {{ display: flex; gap: 20px; margin: 20px 0; }}
        .stat {{ padding: 15px; border-radius: 8px; background: #f5f5f5; }}
        .stat h3 {{ margin: 0; }}
        .stat p {{ margin: 5px 0 0 0; font-size: 24px; font-weight: bold; }}
    </style>
</head>
<body>
    <h1>Docker Health Check Report</h1>
    <div class="summary">
        <div class="stat"><h3>Errors</h3><p>{sum(1 for r in results if r.rule.severity == 'error')}</p></div>
        <div class="stat"><h3>Warnings</h3><p>{sum(1 for r in results if r.rule.severity == 'warning')}</p></div>
        <div class="stat"><h3>Info</h3><p>{sum(1 for r in results if r.rule.severity == 'info')}</p></div>
    </div>
    <table>
        <tr><th>Rule</th><th>Name</th><th>Severity</th><th>Location</th><th>Message</th><th>Fix</th></tr>
        {rows}
    </table>
</body>
</html>"""
    
    with open(filename, 'w') as f:
        f.write(html)
    print(f"Health check report exported to {filename}")