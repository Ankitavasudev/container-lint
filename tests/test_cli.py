"""Tests for the command-line interface."""

import json

from container_lint.cli import main


BAD_DOCKERFILE = """FROM ubuntu
RUN apt-get install curl
COPY . .
"""

CLEAN_DOCKERFILE = """FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py ./
USER 1000
CMD ["python", "app.py"]
"""


def write(tmp_path, name, content):
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


def test_clean_dockerfile_exits_zero(tmp_path, capsys):
    path = write(tmp_path, "Dockerfile", CLEAN_DOCKERFILE)
    assert main([str(path)]) == 0
    assert "No issues found." in capsys.readouterr().out


def test_bad_dockerfile_exits_one(tmp_path, capsys):
    path = write(tmp_path, "Dockerfile", BAD_DOCKERFILE)
    assert main([str(path)]) == 1
    out = capsys.readouterr().out
    assert "warning" in out
    assert "DL3007" in out


def test_fail_on_info_is_stricter(tmp_path):
    path = write(tmp_path, "Dockerfile", "FROM alpine:3.20\nUSER app\nCMD sh -c run\n")
    assert main([str(path), "--fail-on", "warning"]) == 0
    assert main([str(path), "--fail-on", "info"]) == 1


def test_fail_on_never_always_exits_zero(tmp_path):
    path = write(tmp_path, "Dockerfile", BAD_DOCKERFILE)
    assert main([str(path), "--fail-on", "never"]) == 0


def test_json_format_is_machine_readable(tmp_path, capsys):
    path = write(tmp_path, "Dockerfile", BAD_DOCKERFILE)
    main([str(path), "--format", "json", "--fail-on", "never"])
    payload = json.loads(capsys.readouterr().out)
    assert payload
    assert set(payload[0]) == {"file", "line", "severity", "rule", "message"}


def test_directory_is_scanned_recursively(tmp_path, capsys):
    write(tmp_path, "Dockerfile", BAD_DOCKERFILE)
    nested = tmp_path / "services" / "api"
    nested.mkdir(parents=True)
    write(nested, "Dockerfile", "FROM node\n")
    main([str(tmp_path), "--format", "json", "--fail-on", "never"])
    payload = json.loads(capsys.readouterr().out)
    assert {item["file"] for item in payload} >= {
        str(tmp_path / "Dockerfile"),
        str(nested / "Dockerfile"),
    }


def test_compose_file_is_detected_by_name(tmp_path, capsys):
    path = write(tmp_path, "docker-compose.yml", """
services:
  db:
    image: postgres
    privileged: true
""")
    assert main([str(path)]) == 1
    out = capsys.readouterr().out
    assert "DC200" in out
    assert "DC100" in out


def test_missing_path_reports_an_error(tmp_path, capsys):
    missing = tmp_path / "nope"
    assert main([str(missing)]) == 1
    assert "FILE_READ" in capsys.readouterr().out


def test_no_targets_exits_two(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert main([]) == 2
    assert "No Dockerfile" in capsys.readouterr().err


def test_default_targets_come_from_cwd(tmp_path, capsys, monkeypatch):
    write(tmp_path, "Dockerfile", BAD_DOCKERFILE)
    monkeypatch.chdir(tmp_path)
    assert main(["--format", "json", "--fail-on", "never"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["file"].endswith("Dockerfile")


def test_directory_scan_skips_files_it_cannot_parse(tmp_path, capsys):
    """A repo contains binaries and lock files; scanning it must not crash."""
    write(tmp_path, "Dockerfile", CLEAN_DOCKERFILE)
    (tmp_path / "package-lock.bin").write_bytes(b"\xe6\x00\x01binary")
    (tmp_path / ".venv").mkdir()
    write(tmp_path / ".venv", "Dockerfile", "FROM scratch\n")

    assert main([str(tmp_path), "--fail-on", "never"]) == 0
    out = capsys.readouterr().out
    assert "No issues found." in out
    assert "package-lock" not in out


def test_explicit_binary_file_reports_a_readable_error(tmp_path, capsys):
    path = tmp_path / "Dockerfile"
    path.write_bytes(b"FROM alpine\xe6\n")
    assert main([str(path)]) == 1
    out = capsys.readouterr().out
    assert "FILE_ENCODING" in out
    assert "not valid UTF-8" in out


def test_sarif_format_from_the_cli(tmp_path, capsys):
    path = write(tmp_path, "Dockerfile", BAD_DOCKERFILE)
    main([str(path), "--format", "sarif", "--fail-on", "never"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["version"] == "2.1.0"
    assert payload["runs"][0]["results"]
    assert payload["runs"][0]["tool"]["driver"]["name"] == "container-lint"


def test_directory_scan_finds_the_same_files_pre_commit_does(tmp_path, capsys):
    """`*.dockerfile` is matched by the pre-commit hook, so the scan must too."""
    write(tmp_path, "app.dockerfile", BAD_DOCKERFILE)

    assert main([str(tmp_path), "--format", "json", "--fail-on", "never"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload
    assert payload[0]["file"].endswith("app.dockerfile")
