# PROB🧪RKA

[![PyPI](https://img.shields.io/pypi/v/probirka.svg)](https://pypi.python.org/pypi/probirka)
[![Python](https://img.shields.io/pypi/pyversions/probirka.svg)](https://pypi.python.org/pypi/probirka)
[![PyPI](https://img.shields.io/pypi/dm/probirka.svg)](https://pypi.python.org/pypi/probirka)
[![Coverage Status](https://coveralls.io/repos/github/appKODE/probirka/badge.svg?branch=main)](https://coveralls.io/github/appKODE/probirka?branch=main)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

Framework-agnostic library for running health probes in Python applications.

A small async engine that runs checks concurrently, handles timeouts, caches results and exposes them over HTTP, with ready-made probes for common infrastructure such as PostgreSQL, Redis, HTTP, Kafka, RabbitMQ and MongoDB.

* 🚫 no runtime dependencies in the core
* ⚡ concurrent async execution
* ⏱ per-probe and overall timeouts
* 💾 separate caching of successful and failed results
* 🧩 optional probe groups — cheap liveness, expensive readiness
* 🟡 `allow_failure` — non-critical probes that may fail without failing the check
* 🔌 ready-made probes for common infrastructure
* 🌐 FastAPI, aiohttp and Django adapters, plus a dependency-free ASGI app for everything else
* 🐍 fully typed

[Documentation](https://appkode.github.io/probirka/) · [Changelog](CHANGELOG.md)

## Installation

```bash
pip install probirka
```

Requires Python 3.11 or newer. The core has no runtime dependencies.

Ready-made probes and framework integrations use client libraries that you install alongside. Install only what you need:

```bash
pip install probirka asyncpg redis fastapi
```

If a library is missing, accessing the corresponding probe or adapter raises an `ImportError` that names the package to install:

```text
ImportError: RedisProbe requires the 'redis' package, install it with: pip install redis
```

See the [documentation](https://appkode.github.io/probirka/probes.html) for the complete list of probes and their dependencies.

## Quick start

The simplest way to add a probe is a function:

```python
import asyncio

from probirka import Probirka


probirka = Probirka(success_ttl=30)


@probirka.add(name='database', timeout=2)
async def check_database():
    return True


@probirka.add(name='external_api', timeout=2)
async def check_external_api():
    return True


async def main():
    result = await probirka.run()

    print(result.ok)
    print(result.to_dict())


asyncio.run(main())
```

Probes are executed concurrently. Synchronous functions are supported too — they run in the event loop's default executor, so they neither block the loop nor escape their timeout.

## How it works

A **probe** is a single check of some application dependency or subsystem. `Probirka` runs probes and aggregates their results into a single health-check result.

```text
                 Probirka
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
    PostgreSQL     Redis       HTTP
      probe        probe       probe
        │           │           │
        └───────────┼───────────┘
                    ▼
             ProbirkaResult
```

Probes are independent and can be implemented as simple functions or as reusable `Probe` classes.

A probe never crashes the health check. Whatever it does is turned into a `ProbeResult`:

| The probe                  | `ok`    | `error`                                        |
| -------------------------- | ------- | ---------------------------------------------- |
| returns `True` or `None`   | `True`  | `None`                                         |
| returns `False`            | `False` | `None`                                         |
| raises an exception        | `False` | `'ExcType: message'`                           |
| exceeds its `timeout`      | `False` | `'TimeoutError: probe timed out after 2s'`     |

A failing check therefore looks like this:

```python
{
    'ok': False,
    'started_at': '2026-09-12T16:00:00.000000+03:00',
    'elapsed': 2.001,
    'info': None,
    'checks': [
        {
            'name': 'database',
            'ok': False,
            'cached': False,
            'started_at': '2026-09-12T16:00:00.000000+03:00',
            'elapsed': 2.0,
            'info': None,
            'error': 'TimeoutError: probe timed out after 2s',
            'allow_failure': False,
        },
        ...
    ],
    'error': None,
}
```

The top-level `ok` is `True` when every probe that ran passed, except probes marked with `allow_failure` — those may fail without affecting it, see [Allowing failures](#allowing-failures).

## Ready-made probes

| Probe                  | Dependency | What it checks                                             |
| ---------------------- | ---------- | ---------------------------------------------------------- |
| `TcpProbe`             | —          | A TCP connection to `host:port` can be established         |
| `PostgresAsyncpgProbe` | `asyncpg`  | `SELECT 1` on a pool, connection or `dsn`                  |
| `RedisProbe`           | `redis`    | `PING` via `redis.asyncio`                                 |
| `HttpHttpxProbe`       | `httpx`    | Response status code of a request                          |
| `HttpHttpx2Probe`      | `httpx2`   | Same, with `httpx2`                                        |
| `HttpAiohttpProbe`     | `aiohttp`  | Same, with `aiohttp.ClientSession`                         |
| `KafkaAiokafkaProbe`   | `aiokafka` | Cluster metadata via a producer, consumer or admin client  |
| `RabbitmqAiopikaProbe` | `aio-pika` | A channel can be opened and closed                         |
| `MongoPymongoProbe`    | `pymongo`  | `ping` command via `pymongo.AsyncMongoClient`              |
| `MongoMotorProbe`      | `motor`    | `ping` command via `AsyncIOMotorClient`                    |

For example, checking application dependencies:

```python
from probirka import (
    Probirka,
    PostgresAsyncpgProbe,
    RedisProbe,
    HttpHttpxProbe,
)

probirka = Probirka()

probirka.add_probes(
    PostgresAsyncpgProbe(
        lambda: app.state.pool,
        name='postgres',
        timeout=2,
    ),
    RedisProbe(
        url='redis://cache:6379/0',
        name='redis',
        timeout=1,
    ),
    HttpHttpxProbe(
        'https://example.com/health',
        name='external-api',
        timeout=2,
    ),
)
```

Every probe that talks to a service takes either an existing client or a connection string — exactly one of the two:

* **an existing client** (first positional argument): the probe reuses your pool and its configuration and never closes it;
* **a connection string** (`dsn`, `url`, `bootstrap_servers`): the probe opens a short-lived connection for each check and closes it afterwards.

When the client is created after the probes are registered — in a FastAPI lifespan, an aiohttp startup signal — pass a zero-argument function instead of the client, as in the `lambda: app.state.pool` above. It is called on every check. This makes it possible to reuse application connection pools instead of creating additional connections just for health checks.

A probe that reaches the service but does not like the answer raises `ProbeFailure`, which lands in `error` as, for example, `'ProbeFailure: unexpected status 503'`.

## Custom probes

Ready-made probes are just regular `Probe` implementations. For application-specific checks, use a function:

```python
@probirka.add(name='application')
async def check_application():
    return await something_is_working()
```

Or create a reusable probe:

```python
from probirka import ProbeBase


class MyProbe(ProbeBase):
    async def _check(self) -> bool:
        return await check_something()
```

There is no special API for custom probes. They use the same execution, timeout, caching and result handling as built-in probes.

## Metadata

Both the health check and individual probes can carry arbitrary metadata, which ends up in the `info` field of the result:

```python
probirka.add_info('version', '1.4.0')
probirka.add_info('environment', 'production')


class DatabaseProbe(ProbeBase):
    async def _check(self) -> bool:
        pool = app.state.pool
        self.add_info('pool_size', pool.get_size())
        return True
```

## Groups

Some checks may be too expensive or too slow to run on every health request. Put them into an optional group:

```python
@probirka.add(
    name='external',
    groups=['external'],
)
async def check_external_service():
    return True
```

Probes without groups are required and run on every call. Grouped probes run only when their group is requested:

```python
await probirka.run(with_groups=['external'])
```

Pass `skip_required=True` to run the requested groups alone:

```python
await probirka.run(with_groups='external', skip_required=True)
```

This separates cheap liveness checks from expensive dependency checks — one `Probirka` instance can back both Kubernetes endpoints:

```python
probirka = Probirka()


@probirka.add(name='self')
async def liveness():
    return True


probirka.add_probes(
    PostgresAsyncpgProbe(lambda: app.state.pool, name='postgres', timeout=2),
    RedisProbe(lambda: app.state.redis, name='redis', timeout=1),
    groups='readiness',
)

app.add_api_route('/livez', make_fastapi_endpoint(probirka))
app.add_api_route('/readyz', make_fastapi_endpoint(probirka, with_groups='readiness'))
```

Groups that were never registered are ignored rather than reported as failures.

## Allowing failures

Not every dependency is critical. A cache or a metrics backend may be down while the service still serves traffic, and a health check that reports `503` in that case only causes restarts. Mark such probes with `allow_failure=True`, named after the same option in GitLab CI:

```python
@probirka.add(name='cache', allow_failure=True)
async def check_cache():
    return await redis.ping()


probirka.add_probes(
    TcpProbe('smtp.internal', 25, name='smtp', allow_failure=True),
)
```

A probe with `allow_failure` runs and is reported like any other: its `ok`, `error` and `elapsed` are in `checks`, and its result carries `allow_failure: true`. It just does not count towards the top-level `ok`, so the HTTP integrations return `success_code` even when it fails:

```python
{
    'ok': True,
    'checks': [
        {'name': 'database', 'ok': True, 'allow_failure': False, ...},
        {'name': 'cache', 'ok': False, 'allow_failure': True, 'error': 'ConnectionError: ...', ...},
    ],
    'error': None,
}
```

The flag can also be set for a whole [group](#groups). It then overrides the probes' own setting, in both directions:

```python
probirka.add_probes(
    HttpHttpxProbe('https://partner.example/health', name='partner'),
    TcpProbe('smtp.internal', 25, name='smtp'),
    groups='external',
    allow_failure=True,
)
```

Without `allow_failure` the group leaves every probe as it is. When a probe is run through several sources at once — the required list and a group, or two groups — it is allowed to fail only if every source allows it, so a strict source always wins. `add_probes(..., allow_failure=...)` without `groups` raises `ValueError`: for required probes set the flag on the probe itself.

The overall `run(timeout=...)` follows the same rule: if only probes with `allow_failure` did not finish in time, `ok` stays `True`, while `error` still reports the timeout.

## Caching

Health checks should not necessarily hit every dependency on every request. Probirka can cache successful and failed probe results independently:

```python
probirka = Probirka(
    success_ttl=30,
    failed_ttl=5,
)
```

These defaults apply to probes registered with the `@probirka.add(...)` decorator; a probe can override them, and `success_ttl=0` or `failed_ttl=0` disables that half of the cache for one probe. Probe objects passed to `add_probes()` — including all ready-made probes — carry their own TTLs instead, so set them on the probe:

```python
probirka.add_probes(
    RedisProbe(url='redis://cache:6379/0', success_ttl=30, failed_ttl=5),
)
```

TTLs are counted with a monotonic clock, so clock adjustments do not extend or shorten them.

Cached results are marked with `cached=True`, so consumers can distinguish a fresh check from a cached result. A probe with no TTL configured reports `cached=None`.

## Timeouts

Every probe can have its own timeout:

```python
@probirka.add(
    name='database',
    timeout=2,
)
async def check_database():
    ...
```

There is also an overall timeout for the complete run:

```python
result = await probirka.run(timeout=5)
```

This prevents one slow dependency from keeping the whole health check request open indefinitely. `run()` never raises on the overall timeout: probes that did not finish in time are cancelled and reported as failed, finished ones keep their results, and the run itself gets `error` set to `'TimeoutError: probirka run timed out after 5s'`. `ok` becomes `False` unless every probe that did not finish has [`allow_failure`](#allowing-failures).

## HTTP integrations

Probirka provides thin adapters for popular Python HTTP frameworks, and a generic ASGI application for everything else. All of them run the probes, map `ok` to a status code and return `ProbirkaResult.to_dict()` as JSON, so every endpoint answers in the same format.

| Where it runs                            | Use                                     |
| ---------------------------------------- | --------------------------------------- |
| FastAPI                                  | `make_fastapi_endpoint`                 |
| aiohttp                                  | `make_aiohttp_endpoint`                 |
| Django                                   | `make_django_view`                      |
| Starlette, Litestar, Falcon, BlackSheep  | `make_asgi_app`                         |
| A port of its own                        | `make_asgi_app` served by uvicorn       |
| Sanic, Quart, Flask                      | `probirka.run()` from your own handler  |

Every factory takes the same keyword arguments:

| Argument         | Default | Meaning                                                |
| ---------------- | ------- | ------------------------------------------------------ |
| `timeout`        | `None`  | Overall timeout for the run, in seconds                |
| `with_groups`    | `''`    | Optional groups to include                             |
| `skip_required`  | `False` | Run only the requested groups                          |
| `return_results` | `True`  | Return the result as JSON; `False` sends an empty body |
| `success_code`   | `200`   | Status code when every probe passed                    |
| `error_code`     | `500`   | Status code when at least one probe failed             |

### FastAPI

```python
from fastapi import FastAPI

from probirka import Probirka, make_fastapi_endpoint

app = FastAPI()

probirka = Probirka()

# add probes...

app.add_api_route(
    '/health',
    make_fastapi_endpoint(probirka),
)
```

### aiohttp

```python
from aiohttp import web

from probirka import Probirka, make_aiohttp_endpoint

app = web.Application()

probirka = Probirka()

# add probes...

app.router.add_get(
    '/health',
    make_aiohttp_endpoint(probirka),
)
```

### Django

```python
# urls.py
from django.urls import path

from probirka import Probirka, make_django_view

probirka = Probirka()

# add probes...

urlpatterns = [
    path('health', make_django_view(probirka)),
]
```

The Django view answers `GET` and `HEAD`; other methods get `405 Method Not Allowed`.

### Any ASGI framework

`make_asgi_app` returns a plain ASGI 3 application. It is the only integration with no third-party dependency at all, so it works on a bare `pip install probirka`:

```python
from starlette.applications import Starlette
from starlette.routing import Route

from probirka import Probirka, make_asgi_app

probirka = Probirka()

# add probes...

app = Starlette(
    routes=[
        Route('/health', make_asgi_app(probirka), methods=['GET', 'HEAD']),
    ],
)
```

Mounting works too — `app.mount('/health', make_asgi_app(probirka))` in FastAPI, `asgi('/health', is_mount=True)(make_asgi_app(probirka))` in Litestar — and so does serving it separately:

```bash
uvicorn health:health_app --port 8081
```

Because a mounted app gets no help from the host router, it handles two things itself: the request path is ignored, and only `GET` and `HEAD` are served, everything else gets `405`.

> [!WARNING]
> Starlette's `Mount('/health', app)` answers on `/health/` and redirects the bare `/health` with a `307`. Kubernetes counts any status below 400 as success, so such a probe would report the service healthy without ever running the checks. Use `Route`, or point the probe at the trailing slash.

## Results

Results are typed immutable data classes. `started_at` is timezone-aware in the local zone of the host, and `elapsed` is measured with a monotonic clock, so it is unaffected by clock adjustments:

```python
result = await probirka.run()

print(result.ok)

for check in result.checks:
    print(
        check.name,
        check.ok,
        check.cached,
        check.elapsed,
        check.error,
        check.allow_failure,
    )
```

`result.to_dict()` converts it to a JSON-compatible dictionary, which is what every HTTP integration returns and what monitoring systems consume.

## Why Probirka?

Probirka deliberately keeps the core small. It does not try to manage connections, discover services or prescribe how your application should be structured. Instead, it provides three things:

1. **Probe implementations** — checks for your dependencies.
2. **Execution engine** — concurrency, timeouts, caching and groups.
3. **Integrations** — expose the same result through your HTTP framework, a mountable ASGI app, or a handler of your own.

Your application remains responsible for creating and managing its clients, pools and connections.

## Development

The project uses [uv](https://docs.astral.sh/uv/) and [just](https://github.com/casey/just):

```bash
uv sync --dev
just tests
just lint
just ty
just doc
```

## License

MIT
