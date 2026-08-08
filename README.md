# container-lint

Dockerfile & docker-compose.yml linter with security best practices checks.

## Features

- Dockerfile linting (DL3000-series rules)
- Docker-compose.yml validation
- Security checks (privileged containers, hardcoded secrets, latest tags)
- CI/CD integration ready

## Install

`ash
pip install container-lint
`

## Usage

`ash
# Lint a Dockerfile
container-lint Dockerfile

# Lint docker-compose
container-lint docker-compose.yml

# Lint entire directory
container-lint --all ./project
`

## Rules

| Rule | Severity | Description |
|------|----------|-------------|
| DL3007 | warning | Using latest tag |
| DL3002 | warning | Last user is root |
| DL3008 | warning | Unpinned apt packages |
| DC200 | error | Privileged container |
| DC400 | warning | Hardcoded secrets |