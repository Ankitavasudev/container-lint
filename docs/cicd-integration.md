# CI/CD Integration Guide

## GitHub Actions

```yaml
name: Lint Dockerfiles
on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      
      - name: Install container-lint
        run: pip install container-lint
      
      - name: Lint Dockerfile
        run: python linter.py Dockerfile
      
      - name: Security scan
        run: python security_scanner.py Dockerfile
```

## GitLab CI

```yaml
lint-dockerfile:
  image: python:3.11
  script:
    - pip install container-lint
    - python linter.py Dockerfile
    - python security_scanner.py Dockerfile
```

## Pre-commit Hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: dockerfile-lint
        name: Lint Dockerfile
        entry: python container-lint/linter.py
        language: system
        files: Dockerfile
```

## Docker Usage

```bash
# Build the linter image
docker build -t container-lint .

# Lint a Dockerfile
docker run --rm -v $(pwd):/workspace container-lint /workspace/Dockerfile
```