SOURCE_DIR := "probirka"
TESTS_DIR := "tests"

pre-commit:
  pre-commit run --show-diff-on-failure

pre-commit-all:
  pre-commit run --all-files --show-diff-on-failure

# CI

ci: isort black ruff mypy tests

# FORMATTERS

formatters: isort black

isort:
  python -m poetry run isort {{SOURCE_DIR}}
  python -m poetry run isort {{TESTS_DIR}}

isort-check:
  python -m poetry run isort {{SOURCE_DIR}} --diff --check-only
  python -m poetry run isort {{TESTS_DIR}} --diff --check-only

black:
  python -m poetry run black {{SOURCE_DIR}} {{TESTS_DIR}}

black-check:
  python -m poetry run black {{SOURCE_DIR}} {{TESTS_DIR}} --check

# LINTERS

lint: isort-check ruff mypy black-check

ruff:
  python -m poetry run ruff check --fix {{SOURCE_DIR}}

mypy:
  python -m poetry run mypy --pretty -p {{SOURCE_DIR}}

# SECURITY

security: safety bandit

bandit:
  python -m poetry run bandit -r ./{{SOURCE_DIR}}

safety:
  python -m poetry run safety --disable-optional-telemetry check --full-report --file poetry.lock --ignore 70612

# TESTS

tests:
  python -m poetry run pytest --cov={{SOURCE_DIR}} --cov-config=coverage.ini --junitxml=report.xml -vv {{TESTS_DIR}}/

# UTILS

clean:
  rm -f .coverage
  rm -rf htmlcov/
  rm -rf .pytest_cache/
  rm -rf .cache/
  rm -rf .mypy_cache
