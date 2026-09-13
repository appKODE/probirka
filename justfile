SOURCE_PATH := "probirka"
TESTS_PATH := "tests"
LINT_PATHS := SOURCE_PATH + " " + TESTS_PATH + " docs"

upgrade:
    uv lock --upgrade

fmt:
    uv run ruff format {{ LINT_PATHS }}

fmt-check:
    uv run ruff format --check {{ LINT_PATHS }}

lint:
    uv run ruff check {{ LINT_PATHS }}

ty:
    uv run ty check {{ SOURCE_PATH }}

fix:
    uv run ruff check --fix --unsafe-fixes {{ LINT_PATHS }}

tests:
    uv run pytest --cov=probirka --cov-report lcov:tests.lcov tests/

# integration tests against live services, see tests/integration/compose.yaml
tests-integration:
    PROBIRKA_INTEGRATION=1 uv run pytest --timeout 60 -m integration tests/integration/

services-up:
    docker compose -f tests/integration/compose.yaml up -d --wait

services-down:
    docker compose -f tests/integration/compose.yaml down -v

doc:
    cd docs && uv run sphinx-build -b html source build && cd ..
