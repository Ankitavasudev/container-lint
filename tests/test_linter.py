"""Tests for the real linter module (container_lint.linter)."""

import textwrap

from container_lint.linter import DockerComposeLinter, DockerfileLinter, LintIssue


def lint_dockerfile(content: str):
    return DockerfileLinter().lint_lines(textwrap.dedent(content).splitlines(), "Dockerfile")


def rules(issues):
    return [issue.rule for issue in issues]


def lint_compose(content: str):
    import yaml

    return DockerComposeLinter().lint_data(yaml.safe_load(textwrap.dedent(content)), "docker-compose.yml")


# ------------------------------------------------------------------ from/tag


def test_untagged_base_image_is_flagged():
    issues = lint_dockerfile("FROM ubuntu\n")
    assert "DL3007" in rules(issues)
    assert issues[0].severity == "warning"


def test_latest_tag_is_flagged():
    assert "DL3007" in rules(lint_dockerfile("FROM ubuntu:latest\n"))


def test_pinned_tag_is_clean():
    assert "DL3007" not in rules(lint_dockerfile("FROM ubuntu:20.04\nUSER app\n"))


def test_digest_is_considered_pinned():
    content = "FROM ubuntu@sha256:" + "a" * 64 + "\nUSER app\n"
    assert "DL3007" not in rules(lint_dockerfile(content))


def test_tag_on_registry_with_port_is_understood():
    assert "DL3007" not in rules(lint_dockerfile("FROM registry:5000/team/app:1.2\nUSER app\n"))


def test_multi_stage_requires_stage_names():
    content = """
        FROM golang:1.22
        RUN go build ./...
        FROM gcr.io/distroless/static:nonroot
        USER nonroot
    """
    assert "DL3022" in rules(lint_dockerfile(content))


def test_named_stages_do_not_warn():
    content = """
        FROM golang:1.22 AS build
        FROM gcr.io/distroless/static:nonroot
        USER nonroot
    """
    assert "DL3022" not in rules(lint_dockerfile(content))


# ----------------------------------------------------------------------- run


def test_apt_get_without_y_flag():
    assert "DL3008" in rules(lint_dockerfile("FROM debian:12\nRUN apt-get install curl\nUSER app\n"))


def test_apt_get_with_y_flag():
    content = "FROM debian:12\nRUN apt-get install -y curl\nUSER app\n"
    assert "DL3008" not in rules(lint_dockerfile(content))


def test_apt_lists_left_behind():
    content = "FROM debian:12\nRUN apt-get update && apt-get install -y curl\nUSER app\n"
    assert "DL3009" in rules(lint_dockerfile(content))


def test_apt_lists_cleaned_up():
    content = (
        "FROM debian:12\n"
        "RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*\n"
        "USER app\n"
    )
    assert "DL3009" not in rules(lint_dockerfile(content))


def test_curl_piped_to_shell():
    content = "FROM alpine:3.20\nRUN curl -fsSL https://example.com/i.sh | sh\nUSER app\n"
    assert "DL4006" in rules(lint_dockerfile(content))


def test_apt_get_upgrade_is_flagged():
    content = "FROM debian:12\nRUN apt-get update && apt-get upgrade -y\nUSER app\n"
    assert "DL3015" in rules(lint_dockerfile(content))


# ------------------------------------------------------------------- copy/add


def test_copy_everything_is_flagged():
    assert "DL3045" in rules(lint_dockerfile("FROM node:20\nCOPY . .\nUSER node\n"))


def test_copy_specific_files_is_clean():
    assert "DL3045" not in rules(lint_dockerfile("FROM node:20\nCOPY package.json ./\nUSER node\n"))


def test_add_with_url_is_flagged():
    content = "FROM alpine:3.20\nADD https://example.com/x.tgz /x.tgz\nUSER app\n"
    assert "DL3020" in rules(lint_dockerfile(content))


# ------------------------------------------------------------------ user/cmd


def test_user_root_is_flagged():
    assert "DL3002" in rules(lint_dockerfile("FROM alpine:3.20\nUSER root\n"))


def test_missing_user_is_flagged_once():
    issues = lint_dockerfile("FROM alpine:3.20\nCMD [\"sh\"]\n")
    assert rules(issues).count("DL3002") == 1
    assert issues[-1].line == 0


def test_shell_form_cmd_is_flagged():
    assert "DL3025" in rules(lint_dockerfile("FROM alpine:3.20\nUSER app\nCMD sh -c 'run'\n"))


def test_json_form_cmd_is_clean():
    content = 'FROM alpine:3.20\nUSER app\nCMD ["sh", "-c", "run"]\n'
    assert "DL3025" not in rules(lint_dockerfile(content))


def test_privileged_port_exposed():
    assert "DL3013" in rules(lint_dockerfile("FROM alpine:3.20\nUSER app\nEXPOSE 22\n"))


def test_common_ports_are_fine():
    assert "DL3013" not in rules(lint_dockerfile("FROM alpine:3.20\nUSER app\nEXPOSE 80 443 8080\n"))


# --------------------------------------------------------------- housekeeping


def test_comments_and_blank_lines_are_ignored():
    content = "\n\n# a comment\nFROM ubuntu:20.04\n\nUSER app\n"
    issues = lint_dockerfile(content)
    assert all(issue.line != 3 for issue in issues)
    assert "DL3007" not in rules(issues)


def test_line_numbers_are_one_based():
    issues = lint_dockerfile("FROM ubuntu\nUSER app\n")
    assert issues[0].line == 1


def test_issue_serialises_to_a_dict():
    issue = LintIssue("Dockerfile", 3, "warning", "DL3007", "msg")
    assert issue.as_dict() == {
        "file": "Dockerfile",
        "line": 3,
        "severity": "warning",
        "rule": "DL3007",
        "message": "msg",
    }


def test_missing_file_reports_one_error():
    issues = DockerfileLinter().lint("does/not/exist")
    assert len(issues) == 1
    assert issues[0].rule == "FILE_READ"
    assert issues[0].severity == "error"


def test_lint_reads_from_disk(tmp_path):
    path = tmp_path / "Dockerfile"
    path.write_text("FROM ubuntu\nUSER app\n", encoding="utf-8")
    assert "DL3007" in rules(DockerfileLinter().lint(str(path)))


# ------------------------------------------------------------------- compose


def test_compose_without_services():
    assert rules(DockerComposeLinter().lint_data({}, "docker-compose.yml")) == ["DC001"]


def test_compose_untagged_image():
    issues = lint_compose("""
        services:
          web:
            image: nginx
    """)
    assert "DC100" in rules(issues)


def test_compose_pinned_image_is_clean():
    issues = lint_compose("""
        services:
          web:
            image: nginx:1.27
    """)
    assert rules(issues) == []


def test_compose_privileged_is_an_error():
    issues = lint_compose("""
        services:
          db:
            image: postgres:16
            privileged: true
    """)
    assert "DC200" in rules(issues)
    assert [i for i in issues if i.rule == "DC200"][0].severity == "error"


def test_compose_public_port_binding():
    issues = lint_compose("""
        services:
          web:
            image: nginx:1.27
            ports:
              - "0.0.0.0:8080:80"
    """)
    assert "DC300" in rules(issues)


def test_compose_hardcoded_secret():
    issues = lint_compose("""
        services:
          db:
            image: postgres:16
            environment:
              POSTGRES_PASSWORD: hunter2
    """)
    assert "DC400" in rules(issues)


def test_compose_secret_from_env_is_fine():
    issues = lint_compose("""
        services:
          db:
            image: postgres:16
            environment:
              POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    """)
    assert "DC400" not in rules(issues)


def test_compose_secret_as_list_is_detected():
    issues = lint_compose("""
        services:
          db:
            image: postgres:16
            environment:
              - API_TOKEN=abc123
    """)
    assert "DC400" in rules(issues)


def test_compose_host_network_is_flagged():
    issues = lint_compose("""
        services:
          proxy:
            image: traefik:3.1
            network_mode: host
    """)
    assert "DC201" in rules(issues)


def test_compose_invalid_yaml_returns_an_error(tmp_path):
    path = tmp_path / "docker-compose.yml"
    path.write_text("services: [", encoding="utf-8")
    issues = DockerComposeLinter().lint(str(path))
    assert len(issues) == 1
    assert issues[0].severity == "error"
