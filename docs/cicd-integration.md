# CI/CD integration

`container-lint` exits non-zero when it finds something at or above
`--fail-on` (default: `warning`), so no extra glue is needed.

## GitHub Actions

```yaml
name: Lint containers

on: [push, pull_request]

jobs:
  container-lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - run: pip install container-lint==2.0.0

      - name: Lint
        run: container-lint . --fail-on error

      - name: Upload the report
        if: always()
        run: container-lint . --format json > container-lint.json

      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: container-lint-report
          path: container-lint.json
```

## GitLab CI

```yaml
container-lint:
  image: python:3.11-slim
  script:
    - pip install container-lint==2.0.0
    - container-lint . --format json > container-lint.json || true
    - container-lint . --fail-on error
  artifacts:
    when: always
    paths: [container-lint.json]
```

## pre-commit

`.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: container-lint
        name: container-lint
        entry: container-lint
        language: system
        files: '(^|/)(Dockerfile|Dockerfile\..*|docker-compose\.ya?ml|compose\.ya?ml)$'
        pass_filenames: true
```

## GitHub Actions summaries

Pipe the JSON through `jq` to annotate the job summary:

```bash
container-lint . --format json \
  | jq -r '.[] | "\(.severity)\t\(.file):\(.line)\t[\(.rule)] \(.message)"' \
  > "$GITHUB_STEP_SUMMARY"
```

## In a monorepo

Pass the directories you care about; anything else is ignored:

```bash
container-lint services/api services/worker --fail-on warning
```

Directories are walked recursively, and files are classified by name:
`Dockerfile`, `Dockerfile.*`, `docker-compose.y[a]ml`, `compose.y[a]ml`.
