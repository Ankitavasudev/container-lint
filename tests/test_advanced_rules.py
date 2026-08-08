import pytest
from advanced_rules import check_dockerfile_advanced, ADVANCED_RULES, export_html_report


def test_no_root_user():
    dockerfile = """
FROM python:3.11
RUN apt-get update
CMD ["python", "app.py"]
"""
    results = check_dockerfile_advanced(dockerfile)
    root_rules = [r for r in results if r.rule.id == "DL3002"]
    assert len(root_rules) > 0


def test_absolute_workdir():
    dockerfile = """
FROM python:3.11
WORKDIR /app
CMD ["python", "app.py"]
"""
    results = check_dockerfile_advanced(dockerfile)
    workdir_issues = [r for r in results if r.rule.id == "DL3000"]
    assert len(workdir_issues) == 0


def test_relative_workdir():
    dockerfile = """
FROM python:3.11
WORKDIR app
CMD ["python", "app.py"]
"""
    results = check_dockerfile_advanced(dockerfile)
    workdir_issues = [r for r in results if r.rule.id == "DL3000"]
    assert len(workdir_issues) > 0


def test_latest_tag():
    dockerfile = """
FROM python:latest
CMD ["python", "app.py"]
"""
    results = check_dockerfile_advanced(dockerfile)
    tag_issues = [r for r in results if r.rule.id == "DL3006"]
    assert len(tag_issues) > 0


def test_pinned_tag():
    dockerfile = """
FROM python:3.11-slim
CMD ["python", "app.py"]
"""
    results = check_dockerfile_advanced(dockerfile)
    tag_issues = [r for r in results if r.rule.id == "DL3006"]
    assert len(tag_issues) == 0


def test_sudo_usage():
    dockerfile = """
FROM python:3.11
RUN sudo apt-get install vim
CMD ["python", "app.py"]
"""
    results = check_dockerfile_advanced(dockerfile)
    sudo_issues = [r for r in results if r.rule.id == "DL3004"]
    assert len(sudo_issues) > 0


def test_cd_in_run():
    dockerfile = """
FROM python:3.11
RUN cd /app && python main.py
"""
    results = check_dockerfile_advanced(dockerfile)
    cd_issues = [r for r in results if r.rule.id == "DL3003"]
    assert len(cd_issues) > 0


def test_healthcheck():
    dockerfile = """
FROM python:3.11
HEALTHCHECK CMD curl -f http://localhost/ || exit 1
CMD ["python", "app.py"]
"""
    results = check_dockerfile_advanced(dockerfile)
    health_issues = [r for r in results if r.rule.id == "DL3013"]
    assert len(health_issues) == 0


def test_rules_count():
    assert len(ADVANCED_RULES) >= 15


def test_export_html(tmp_path):
    dockerfile = """
FROM python:latest
RUN apt-get install vim
"""
    results = check_dockerfile_advanced(dockerfile)
    filepath = str(tmp_path / "report.html")
    export_html_report(results, filepath)
    assert os.path.exists(filepath)