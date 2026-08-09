# Container Lint

> Advanced Dockerfile linting tool with 15+ rules, health check validation, complexity analysis, and security scanning.

[![CI](https://github.com/Ankitavasudev/container-lint/actions/workflows/ci.yml/badge.svg)](https://github.com/Ankitavasudev/container-lint/actions)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## Features

- **15+ Lint Rules** - Comprehensive Dockerfile validation
- **Health Check Validation** - Verifies HEALTHCHECK instructions
- **Complexity Analysis** - Detects overly complex builds
- **Security Scanner** - Identifies security vulnerabilities
- **Best Practices** - Enforces Docker best practices
- **CI/CD Ready** - Exit codes for pipeline integration

## Quick Start

```bash
# Install
git clone https://github.com/Ankitavasudev/container-lint.git
cd container-lint
pip install -r requirements.txt

# Lint a Dockerfile
python linter.py Dockerfile

# Security scan
python security_scanner.py Dockerfile

# Complexity analysis
python complexity_analyzer.py Dockerfile

# Health check validation
python health_check.py Dockerfile
```

## Lint Rules

| Rule | Severity | Description |
|------|----------|-------------|
| DL001 | ERROR | Use COPY instead of ADD |
| DL002 | WARNING | Avoid latest tag |
| DL003 | WARNING | Pin package versions |
| DL004 | ERROR | Use multi-stage builds |
| DL005 | WARNING | Minimize layers |
| DL006 | ERROR | Run as non-root |
| DL007 | WARNING | Use .dockerignore |
| DL008 | WARNING | Add HEALTHCHECK |
| DL009 | INFO | Use specific base image |
| DL010 | WARNING | Avoid apt-get upgrade |
| DL011 | WARNING | Clean apt cache |
| DL012 | INFO | Use LABEL metadata |
| DL013 | WARNING | Avoid curl pipe bash |
| DL014 | WARNING | Pin versions in apt |
| DL015 | INFO | Use WORKDIR properly |

## Security Rules

| Rule | Severity | Description |
|------|----------|-------------|
| SEC001 | CRITICAL | Running as root |
| SEC002 | CRITICAL | No USER instruction |
| SEC003 | WARNING | Exposed ports |
| SEC004 | WARNING | No health check |
| SEC005 | INFO | Using latest tag |

## Architecture

```
container-lint/
├── linter.py              # Main linter with 15+ rules
├── security_scanner.py    # Security vulnerability scanner
├── complexity_analyzer.py # Build complexity analysis
├── health_check.py        # HEALTHCHECK validation
├── advanced_rules.py      # Extended rule set
├── requirements.txt       # Python dependencies
├── Dockerfile             # Self-contained container
└── .github/workflows/     # CI/CD pipeline
```

## Tech Stack

- **Python 3.9+** - Core language
- **Rich** - Terminal output formatting
- **Dockerfile parser** - Dockerfile AST parsing
- **pytest** - Testing framework

## License

MIT License - see [LICENSE](LICENSE) for details.