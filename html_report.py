#!/usr/bin/env python3
"""HTML report generator for container-lint results."""

import json
from typing import List, Dict, Any


def generate_html_report(results: List[Dict[str, Any]], filename: str = "report.html"):
    errors = sum(1 for r in results if r.get("severity") == "error")
    warnings = sum(1 for r in results if r.get("severity") == "warning")
    html = f"<html><head><title>Lint Report</title></head><body>"
    html += f"<h1>Container Lint Report</h1>"
    html += f"<p>Errors: {errors} | Warnings: {warnings}</p>"
    html += "<table><tr><th>Line</th><th>Rule</th><th>Severity</th><th>Message</th></tr>"
    for r in results:
        html += f"<tr><td>{r.get('line','')}</td><td>{r.get('rule','')}</td><td>{r.get('severity','')}</td><td>{r.get('message','')}</td></tr>"
    html += "</table></body></html>"
    with open(filename, "w") as f:
        f.write(html)