SOURCE_PATH := "probirka"
TESTS_PATH := "tests"

upgrade:
    uv lock --upgrade

fmt:
    uv run ruff format {{ SOURCE_PATH }}

lint:
    uv run ruff check {{ SOURCE_PATH }}

mypy:
    uv run python -m mypy --pretty {{ SOURCE_PATH }}

fix:
    uv run ruff check --fix --unsafe-fixes {{ SOURCE_PATH }}

tests:
    uv run pytest --cov=probirka --cov-report lcov:tests.lcov tests/

doc:
    cd docs && uv run sphinx-build -b html source build && cd ..
