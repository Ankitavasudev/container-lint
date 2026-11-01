# container-lint

Lint Dockerfiles and `docker-compose.yml` files **without a Docker daemon**.
Pure Python, one dependency (`pyyaml`), usable as a library or a CLI.

```bash
pip install .
container-lint path/to/Dockerfile
container-lint .                    # walk the tree for Dockerfiles + compose files
container-lint Dockerfile --format json --fail-on error
```

Exit codes: `0` clean, `1` findings at or above `--fail-on` (default `warning`),
`2` nothing to lint. That makes it drop-in for CI.

## Rules

Rule ids follow [hadolint](https://github.com/hadolint/hadolint)'s `DL30xx`
naming so existing ignore-lists keep working.

| Rule | Severity | Check |
|---|---|---|
| `DL3007` | warning | base image has no tag or digest, or uses `:latest` |
| `DL3022` | info | multi-stage build where no stage is named with `AS` |
| `DL3008` | warning | `apt-get install` without `-y` (build would hang) |
| `DL3009` | info | `/var/lib/apt/lists` not removed after installing |
| `DL3015` | warning | `apt-get upgrade` inside the image |
| `DL4006` | warning | download piped straight into a shell interpreter |
| `DL3045` | warning | `COPY . .` pulls in the whole build context |
| `DL3020` | info | `ADD` from a URL â€” `COPY` is enough |
| `DL3002` | warning | no `USER`, or `USER root` |
| `DL3025` | info | shell-form `CMD`, which breaks signal handling |
| `DL3013` | info | `EXPOSE` on a privileged port (<1024, excluding 80/443) |

Compose files get their own checks:

| Rule | Severity | Check |
|---|---|---|
| `DC001` / `DC002` / `DC003` | error | file shape is not a `services` mapping |
| `DC100` | warning | service image is unpinned |
| `DC200` | error | `privileged: true` |
| `DC201` | warning | `network_mode: host` |
| `DC300` | info | port published on every interface |
| `DC400` | warning | hardcoded secret in `environment` |

Secrets that come from `${VAR}` are not flagged, and neither are obvious
placeholders (`changeme`, `xxx`, â€¦).

## Try it

`examples/` contains a deliberately broken Dockerfile and compose file:

```bash
container-lint examples
# 14 issue(s): 1 error, 7 warning, 6 info
```

## Library use

```python
from container_lint import DockerfileLinter, DockerComposeLinter

for issue in DockerfileLinter().lint("Dockerfile"):
    print(issue.severity, issue.rule, issue.message)

DockerComposeLinter().lint("docker-compose.yml")
```

Both linters also expose `lint_lines(lines, filename)` / `lint_data(dict, filename)`
so you can lint strings from a test or an HTTP request without touching disk.
`LintIssue.as_dict()` returns the JSON shape used by `--format json`.

## CI

```yaml
- uses: actions/checkout@v4
- uses: actions/setup-python@v5
  with:
    python-version: "3.11"
- run: pip install .
- run: container-lint . --fail-on error
```

See [docs/cicd-integration.md](docs/cicd-integration.md) for GitLab and
pre-commit variants.

## Development

```bash
pip install -e . -r requirements-dev.txt
python -m pytest -q
```

47 tests, no network, no Docker.

## License

MIT â€” see [LICENSE](LICENSE).

