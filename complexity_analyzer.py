#!/usr/bin/env python3
"""Dockerfile complexity analyzer."""

import re
from typing import List, Dict
from dataclasses import dataclass


@dataclass
class ComplexityMetric:
    name: str
    value: int
    description: str
    rating: str


def analyze_complexity(content: str) -> List[ComplexityMetric]:
    metrics = []
    lines = content.split('\n')

    # Count instructions
    instructions = [l.strip() for l in lines if l.strip() and not l.strip().startswith('#')]
    metrics.append(ComplexityMetric(
        name="Total Instructions",
        value=len(instructions),
        description="Number of non-comment instructions",
        rating="low" if len(instructions) < 10 else "medium" if len(instructions) < 20 else "high"
    ))

    # Count RUN commands
    run_count = sum(1 for l in instructions if l.upper().startswith('RUN'))
    metrics.append(ComplexityMetric(
        name="RUN Commands",
        value=run_count,
        description="Number of RUN instructions",
        rating="low" if run_count < 3 else "medium" if run_count < 6 else "high"
    ))

    # Count COPY/ADD commands
    copy_count = sum(1 for l in instructions if l.upper().startswith(('COPY', 'ADD')))
    metrics.append(ComplexityMetric(
        name="COPY/ADD Commands",
        value=copy_count,
        description="Number of COPY/ADD instructions",
        rating="low" if copy_count < 5 else "medium" if copy_count < 10 else "high"
    ))

    # Count ENV/ARG commands
    env_count = sum(1 for l in instructions if l.upper().startswith(('ENV', 'ARG')))
    metrics.append(ComplexityMetric(
        name="ENV/ARG Commands",
        value=env_count,
        description="Number of ENV/ARG instructions",
        rating="low" if env_count < 3 else "medium" if env_count < 6 else "high"
    ))

    # Count layers (FROM instructions)
    from_count = sum(1 for l in instructions if l.upper().startswith('FROM'))
    metrics.append(ComplexityMetric(
        name="Build Stages",
        value=from_count,
        description="Number of FROM instructions (multi-stage)",
        rating="low" if from_count <= 1 else "medium" if from_count <= 3 else "high"
    ))

    # Check for complex RUN commands
    complex_runs = 0
    for l in instructions:
        if l.upper().startswith('RUN'):
            if '&&' in l or '|' in l or ';' in l:
                complex_runs += 1
    metrics.append(ComplexityMetric(
        name="Complex RUN Commands",
        value=complex_runs,
        description="RUN commands with chaining (&&, |, ;)",
        rating="low" if complex_runs < 2 else "medium" if complex_runs < 5 else "high"
    ))

    return metrics


def calculate_health_score(metrics: List[ComplexityMetric]) -> int:
    score = 100
    for metric in metrics:
        if metric.rating == "high":
            score -= 15
        elif metric.rating == "medium":
            score -= 5
    return max(0, score)


def print_complexity_report(metrics: List[ComplexityMetric]) -> str:
    report = "Dockerfile Complexity Report\n"
    report += "===========================\n\n"

    for metric in metrics:
        report += f"{metric.name}: {metric.value} ({metric.rating})\n"
        report += f"  {metric.description}\n"

    score = calculate_health_score(metrics)
    report += f"\nHealth Score: {score}/100\n"

    if score >= 80:
        report += "Rating: Good\n"
    elif score >= 60:
        report += "Rating: Fair\n"
    else:
        report += "Rating: Needs Improvement\n"

    return report