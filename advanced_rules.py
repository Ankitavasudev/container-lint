#!/usr/bin/env python3
"""Advanced Dockerfile linting rules."""

import re
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class LintRule:
    id: str
    name: str
    severity: str  # error, warning, info
    description: str
    fix: str


@dataclass
class LintResult:
    rule: LintRule
    file: str
    line: int
    message: str
    suggestion: str = ""


# Advanced rules
ADVANCED_RULES = [
    LintRule(
        id="DL3000",
        name="Use absolute WORKDIR",
        severity="warning",
        description="WORKDIR should use absolute paths",
        fix="Change WORKDIR to use absolute path (e.g., /app instead of app)"
    ),
    LintRule(
        id="DL3001",
        name="Avoid multiple ENTRYPOINT",
        severity="error",
        description="Multiple ENTRYPOINT instructions found",
        fix="Use only one ENTRYPOINT in Dockerfile"
    ),
    LintRule(
        id="DL3002",
        name="Avoid running as root",
        severity="warning",
        description="Container runs as root user",
        fix="Add USER instruction to run as non-root"
    ),
    LintRule(
        id="DL3003",
        name="Avoid cd in RUN",
        severity="warning",
        description="Use WORKDIR instead of cd in RUN",
        fix="Replace 'RUN cd /app' with 'WORKDIR /app' followed by RUN"
    ),
    LintRule(
        id="DL3004",
        name="Avoid sudo",
        severity="error",
        description="sudo should not be used in Dockerfile",
        fix="Use COPY or RUN to install packages without sudo"
    ),
    LintRule(
        id="DL3005",
        name="Pin package versions",
        severity="warning",
        description="Package versions should be pinned",
        fix="Use specific version: apt-get install -y package=1.2.3"
    ),
    LintRule(
        id="DL3006",
        name="Always tag images",
        severity="warning",
        description="FROM should use specific tag, not latest",
        fix="Use specific tag: FROM python:3.11-slim instead of python:latest"
    ),
    LintRule(
        id="DL3007",
        name="Using latest is risky",
        severity="info",
        description="Using 'latest' tag is unpredictable",
        fix="Pin to specific version for reproducible builds"
    ),
    LintRule(
        id="DL3008",
        name="Sort apt packages",
        severity="info",
        description="Sort apt-get install packages alphabetically",
        fix="Sort packages: apt-get install -y a b c"
    ),
    LintRule(
        id="DL3009",
        name="Delete apt lists",
        severity="warning",
        description="apt-get install should clean up apt lists",
        fix="Add: RUN rm -rf /var/lib/apt/lists/*"
    ),
    LintRule(
        id="DL3010",
        name="Use ADD for archives",
        severity="info",
        description="ADD can extract tar archives automatically",
        fix="Use ADD for .tar.gz files instead of COPY + RUN tar"
    ),
    LintRule(
        id="DL3011",
        name="Valid EXPOSE port",
        severity="error",
        description="EXPOSE port must be valid (1-65535)",
        fix="Use valid port number in EXPOSE"
    ),
    LintRule(
        id="DL3012",
        name="Avoid multiple COPY",
        severity="info",
        description="Multiple COPY instructions can be combined",
        fix="Combine multiple COPY instructions where possible"
    ),
    LintRule(
        id="DL3013",
        name="Health check defined",
        severity="info",
        description="No HEALTHCHECK instruction found",
        fix="Add HEALTHCHECK for container orchestration"
    ),
    LintRule(
        id="DL3014",
        name="Use -y flag",
        severity="warning",
        description="apt-get install should use -y flag",
        fix="Add -y flag: apt-get install -y package"
    ),
    LintRule(
        id="DL3015",
        name="Avoid apt-get upgrade",
        severity="warning",
        description="apt-get upgrade should not be used in Dockerfile",
        fix="Use specific package versions instead of upgrade"
    ),
]


def check_dockerfile_advanced(content: str, filename: str = "Dockerfile") -> List[LintResult]:
    results = []
    lines = content.split('\n')
    
    entrypoint_count = 0
    has_user = False
    has_healthcheck = False
    apt_installs = []
    
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        
        if stripped.startswith('#') or not stripped:
            continue
        
        # DL3000: Absolute WORKDIR
        if stripped.upper().startswith('WORKDIR'):
            path = stripped.split()[1] if len(stripped.split()) > 1 else ""
            if path and not path.startswith('/') and not path.startswith('$'):
                results.append(LintResult(
                    rule=ADVANCED_RULES[0],
                    file=filename,
                    line=i,
                    message=f"WORKDIR '{path}' is not absolute"
                ))
        
        # DL3001: Multiple ENTRYPOINT
        if stripped.upper().startswith('ENTRYPOINT'):
            entrypoint_count += 1
            if entrypoint_count > 1:
                results.append(LintResult(
                    rule=ADVANCED_RULES[1],
                    file=filename,
                    line=i,
                    message="Multiple ENTRYPOINT instructions found"
                ))
        
        # DL3002: Running as root
        if stripped.upper().startswith('USER'):
            has_user = True
        
        # DL3003: cd in RUN
        if stripped.upper().startswith('RUN') and 'cd ' in stripped.lower():
            results.append(LintResult(
                rule=ADVANCED_RULES[3],
                file=filename,
                line=i,
                message="Use WORKDIR instead of cd in RUN"
            ))
        
        # DL3004: sudo usage
        if 'sudo ' in stripped.lower():
            results.append(LintResult(
                rule=ADVANCED_RULES[4],
                file=filename,
                line=i,
                message="sudo should not be used in Dockerfile"
            ))
        
        # DL3005: Unpinned packages
        if stripped.upper().startswith('RUN') and 'apt-get install' in stripped:
            packages = re.findall(r'install\s+(?:-\w+\s+)*([\w\.\-]+)', stripped)
            for pkg in packages:
                if '=' not in pkg and pkg not in ['-y', '-q', '--no-install-recommends']:
                    apt_installs.append((i, pkg))
        
        # DL3006: Latest tag
        if stripped.upper().startswith('FROM'):
            if ':latest' in stripped or ':' not in stripped:
                results.append(LintResult(
                    rule=ADVANCED_RULES[6],
                    file=filename,
                    line=i,
                    message="Using 'latest' tag or no tag specified"
                ))
        
        # DL3011: Valid EXPOSE
        if stripped.upper().startswith('EXPOSE'):
            ports = re.findall(r'(\d+)', stripped)
            for port in ports:
                if int(port) > 65535:
                    results.append(LintResult(
                        rule=ADVANCED_RULES[11],
                        file=filename,
                        line=i,
                        message=f"Invalid port number: {port}"
                    ))
        
        # DL3013: Healthcheck
        if stripped.upper().startswith('HEALTHCHECK'):
            has_healthcheck = True
    
    # Add unpinned package warnings
    for line_num, pkg in apt_installs:
        results.append(LintResult(
            rule=ADVANCED_RULES[5],
            file=filename,
            line=line_num,
            message=f"Package '{pkg}' is not version-pinned"
        ))
    
    # Check for missing USER
    if not has_user:
        results.append(LintResult(
            rule=ADVANCED_RULES[2],
            file=filename,
            line=0,
            message="No USER instruction - container will run as root"
        ))
    
    # Check for missing HEALTHCHECK
    if not has_healthcheck:
        results.append(LintResult(
            rule=ADVANCED_RULES[12],
            file=filename,
            line=0,
            message="No HEALTHCHECK instruction found"
        ))
    
    return results


def export_html_report(results: List[LintResult], filename: str):
    rows = ""
    for r in results:
        severity_class = r.severity.lower()
        rows += f"""
        <tr>
            <td>{r.rule.id}</td>
            <td>{r.rule.name}</td>
            <td class="{severity_class}">{r.severity.upper()}</td>
            <td>{r.file}:{r.line}</td>
            <td>{r.message}</td>
            <td>{r.suggestion or r.rule.fix}</td>
        </tr>"""
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Dockerfile Lint Report</title>
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
    <h1>Dockerfile Lint Report</h1>
    <div class="summary">
        <div class="stat"><h3>Errors</h3><p>{sum(1 for r in results if r.severity == 'error')}</p></div>
        <div class="stat"><h3>Warnings</h3><p>{sum(1 for r in results if r.severity == 'warning')}</p></div>
        <div class="stat"><h3>Info</h3><p>{sum(1 for r in results if r.severity == 'info')}</p></div>
    </div>
    <table>
        <tr><th>Rule</th><th>Name</th><th>Severity</th><th>Location</th><th>Message</th><th>Fix</th></tr>
        {rows}
    </table>
</body>
</html>"""
    
    with open(filename, 'w') as f:
        f.write(html)
    print(f"HTML report exported to {filename}")