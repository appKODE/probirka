# AGENTS.md

Working rules for probirka: what the package is, where its boundaries are and how a change is
expected to look. They apply to everyone who edits the repository, people and tools alike.

## What probirka is

A framework-agnostic library for running health probes in Python applications. The core has no
runtime dependencies. Ready-made probes for client libraries (Redis, PostgreSQL, HTTP, Kafka, ...)
and adapters for HTTP frameworks (FastAPI, aiohttp, Django, plain ASGI) ship in the same package
but are imported only when used.

## Map

| Path | Role |
| --- | --- |
| `probirka/__init__.py` | The public surface: re-exports and `__all__`, nothing else |
| `probirka/_lazy.py` | Registry of the names that need a third-party package, the PEP 562 hooks, `MissingDependencyError` |
| `probirka/_redact.py` | Secret masking, stdlib only |
| `probirka/_results.py` | `ProbeResult`, `ProbirkaResult` |
| `probirka/_probirka.py` | `Probirka`: registration, groups, concurrency, timeouts |
| `probirka/_probes/__init__.py` | Barrel of the dependency-free probe names |
| `probirka/_probes/_base.py` | `Probe` protocol, `ProbeBase`, `CallableProbe` |
| `probirka/_probes/_common.py` | `ProbeFailure`, `ClientOrFactory`, constructor helpers |
| `probirka/_probes/_client_base.py`, `_http_base.py`, `_mongo_base.py` | Base classes shared by the driver probes |
| `probirka/_probes/_http_policy.py` | `HttpProbePolicy`, the SSRF protection of the HTTP probes, stdlib only |
| `probirka/_probes/_tcp.py` | `TcpProbe`, the one ready-made probe without a client library |
| `probirka/_probes/_<library>.py` | One driver probe per client library; imports the library at module level |
| `probirka/_ext/__init__.py` | Barrel of the dependency-free adapter names |
| `probirka/_ext/_common.py` | "Run the probes, render the body", shared by the adapters |
| `probirka/_ext/asgi.py` | `make_asgi_app`, needs no framework |
| `probirka/_ext/<framework>.py` | One adapter per framework; imports the framework at module level |
| `tests/probes/` | Unit tests of the probes with the client mocked |
| `tests/integration/` | Tests against live services, run with `PROBIRKA_INTEGRATION=1` |
| `docs/source/` | Sphinx documentation, `api.rst` has one `automodule` per private module |

## Architecture boundaries

### Public API

- Public is what `probirka/__init__.py` exports. Everything under an `_`-prefixed path is private
  and may change without notice.
- README, the Sphinx docs (`add_module_names = False`) and the tests refer to public names as
  `probirka.X`, never by the private module they live in.

### The core imports with nothing but the standard library

- `import probirka` and `from probirka import *` work with no third-party package installed. CI
  runs exactly that in an isolated interpreter.
- A third-party library is imported at module level only in the driver module that needs it:
  `probirka/_probes/_<library>.py` or `probirka/_ext/<framework>.py`. Nothing imports those
  modules eagerly; the package root reaches them through the registry in `probirka/_lazy.py`, and
  `__all__` lists them only when their package is installed.
- `make_asgi_app` and `TcpProbe` need no third-party package and are the only eager exceptions.

### Layers import downwards only

1. `_redact`, `_lazy` (import nothing from the package)
2. `_results`
3. `_probes/_base`, `_probes/_common`, `_probes/_http_policy`
4. `_probes/_client_base`, `_probes/_tcp`, `_probirka`
5. `_probes/_http_base`, `_probes/_mongo_base`, `_ext/_common`
6. driver probes `_probes/_<library>.py`, adapters `_ext/asgi.py` and `_ext/<framework>.py`
7. the barrels: `_probes/__init__.py`, `_ext/__init__.py`, and the package root

A module imports from its own layer or a lower one, never from a higher one. In particular:
nothing inside the package imports the root `probirka`; `_probes/*` never import `_probirka` or
`_ext`; `_ext/*` never import `_probes`.

### `__init__.py` files only re-export

- Allowed in an `__init__.py`: a module docstring, `import` and `from ... import`, a
  `TYPE_CHECKING` block of imports, `__all__`, package metadata dunders such as `__version__`.
- Not allowed: classes, functions, constants, control flow. Code lives in a named module
  (`_probes/_base.py`, not `_probes/__init__.py`).
- Inside a subpackage, siblings import each other by concrete module path
  (`from probirka._probes._base import ProbeBase`), never through the subpackage `__init__`. A
  barrel imported by its own members is a circular import waiting to happen. Only the package
  root and the tests consume barrels.
- A subpackage `__init__` re-exports its dependency-free names only; driver modules are never
  re-exported.
- The package root additionally binds the PEP 562 hooks by assignment
  (`__getattr__ = _module_getattr`, `__dir__ = _module_dir`) and appends the installed lazy names
  to `__all__`. That is the whole exception.
- `tests/test_architecture.py` enforces all of the above.

### Probe contract

- `run_check()` never raises. Exceptions and timeouts become `ProbeResult.error`.
- Raise `ProbeFailure` when the service answered but is not healthy; its message is the error.
- A probe registers every secret it hands to a client library with `_register_secrets()` so that
  the error text is masked. Ready-made probes register the connection-string password and the
  request header values.
- `allow_failure=True` keeps a probe's failure out of the overall `ok`; the probe's own result
  still shows it.

## Adding a probe or an adapter

1. Create `probirka/_probes/_<library>.py` extending `ClientProbeBase` (or `HttpProbeBase`,
   `MongoProbeBase`), or `probirka/_ext/<framework>.py` built on `run_and_render` from
   `_ext/_common.py`. Import the library at module level in that file only.
2. Add the name to `LAZY` in `probirka/_lazy.py` (module path, import name, pip package) and a
   `TYPE_CHECKING` import to `probirka/__init__.py`.
3. Add the library to the `dev` dependency group in `pyproject.toml`.
4. Unit tests with the client mocked in `tests/probes/`; an integration test in
   `tests/integration/` plus the service in `tests/integration/compose.yaml` and in the
   `services:` block of `.github/workflows/tests.yml`.
5. An `automodule` block in `docs/source/api.rst`, a README section and a `CHANGELOG.md` entry
   under `Unreleased`.

## Tooling

- `uv sync --dev` once; then `just fmt`, `just lint`, `just ty`, `just tests`, `just doc`.
  `just services-up && just tests-integration` runs the live-service tests. CI runs the same
  recipes.
- Ruff (lint and format) covers `probirka`, `tests` and `docs`; `ty` covers `probirka`.
- The ruff configuration is in `pyproject.toml`. Every global ignore and every per-file ignore
  carries a comment saying why. A `# noqa` carries a reason
  (`# noqa: S101 -- narrowed by require_exactly_one in __init__`). Do not widen
  `per-file-ignores` to silence one line.
- Pre-commit runs ruff and ty on the changed files; keep its ruff version equal to the one in
  `uv.lock`.

## Code style

- Single quotes, 120 columns, `from __future__ import annotations` in every module, absolute
  imports only, typing-only imports under `TYPE_CHECKING`.
- Docstrings in pep257 form with Sphinx fields (`:param:`, `:return:`, `:raises:`) and an
  imperative first line. Every public module, class and function has one.
- Exception messages go through a variable: `msg = ...; raise ValueError(msg)`.
- Booleans are passed by keyword at call sites.
- Identifiers, comments, docstrings and commit messages are English.

## Tests

- Import from `probirka`. Use a private module only for a symbol that has no public path or to
  `monkeypatch` a module object.
- `tests/test_lazy_imports.py` and `tests/test_architecture.py` are the executable specification
  of the boundaries above; extend them when a boundary changes.
- `just tests` needs no Docker: `tests/integration/` is skipped unless `PROBIRKA_INTEGRATION=1`.

## Commits, merge requests, changelog

- Commit subject: `<type>: <imperative summary>` with one of `feat`, `fix`, `chore`, `test`,
  `docs`; English, no trailing period.
- Merge request description: short. Plain sentences and bulleted or numbered lists are the only
  formatting. No headings, bold text, tables, code blocks or emoji.
- Do not mention AI assistants, language models or code generators anywhere in the repository or
  its history: not in code, comments or docstrings, not in commit messages or trailers (no
  `Co-authored-by` for a tool, no "generated with"), not in merge request titles or descriptions,
  not in the changelog.
- User-visible changes go to `CHANGELOG.md` under `Unreleased`, in the existing style.
