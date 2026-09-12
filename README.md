# PROB🧪RKA

Framework-agnostic library for running health probes in Python applications.

Probirka provides a small async engine for running checks concurrently, handling timeouts, caching results and exposing them through HTTP frameworks.

It also includes ready-made probes for common infrastructure such as PostgreSQL, Redis, HTTP, Kafka, RabbitMQ and MongoDB.

* 🚫 no runtime dependencies in the core
* ⚡ async execution
* ⏱ per-probe and global timeouts
* 💾 success and failure result caching
* 🧩 optional probe groups
* 🔌 ready-made probes for common infrastructure
* 🌐 FastAPI, aiohttp and Django integrations
* 🐍 fully typed

[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![PyPI](https://img.shields.io/pypi/v/probirka.svg)](https://pypi.python.org/pypi/probirka)
[![PyPI](https://img.shields.io/pypi/dm/probirka.svg)](https://pypi.python.org/pypi/probirka)
[![Coverage Status](https://coveralls.io/repos/github/appKODE/probirka/badge.svg?branch=main)](https://coveralls.io/github/appKODE/probirka?branch=main)

[Documentation](https://appkode.github.io/probirka/)

## Installation

```bash
pip install probirka
```

Requires Python 3.11 or newer. The core has no runtime dependencies.

Ready-made probes and framework integrations use client libraries that you install alongside. Install only what you need:

```bash
pip install probirka asyncpg redis fastapi
```

If a library is missing, accessing the corresponding probe or adapter raises an `ImportError` that names the package to install.

See the [documentation](https://appkode.github.io/probirka/) for the complete list of probes and their dependencies.

## How it works

A **probe** is a single check of some application dependency or subsystem.

`Probirka` is responsible for running probes and aggregating their results into a single health-check result.

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

Probes are executed concurrently.

A probe succeeds when it returns `True` or `None` and fails when it returns `False`.

Exceptions and timeouts are captured in the result:

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
        },
        ...
    ],
    'error': None,
}
```

## Ready-made probes

Probirka includes probes for common infrastructure.

| Probe                  | Dependency |
| ---------------------- | ---------- |
| `TcpProbe`             | —          |
| `PostgresAsyncpgProbe` | `asyncpg`  |
| `RedisProbe`           | `redis`    |
| `HttpHttpxProbe`       | `httpx`    |
| `HttpHttpx2Probe`      | `httpx2`   |
| `HttpAiohttpProbe`     | `aiohttp`  |
| `KafkaAiokafkaProbe`   | `aiokafka` |
| `RabbitmqAiopikaProbe` | `aio-pika` |
| `MongoPymongoProbe`    | `pymongo`  |
| `MongoMotorProbe`      | `motor`    |

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

Ready-made probes can use either an existing client from the application (or a function returning it, for clients created later in a lifespan) or create their own connection from a connection string.

This makes it possible to reuse application connection pools instead of creating additional connections just for health checks.

## Custom probes

Ready-made probes are just regular `Probe` implementations.

For application-specific checks, use a function:

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

## Groups

Some checks may be too expensive or too slow to run on every health request.

Put them into an optional group:

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

This can be useful for separating cheap liveness checks from more expensive dependency checks.

## Caching

Health checks should not necessarily hit every dependency on every request.

Probirka can cache successful and failed probe results independently:

```python
probirka = Probirka(
    success_ttl=30,
    failed_ttl=5,
)
```

Individual probes can override these values.

Cached results are marked with `cached=True`, so consumers can distinguish a fresh check from a cached result.

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

This prevents one slow dependency from keeping the whole health check request open indefinitely. Probes that did not finish in time are reported as failed; finished ones keep their results.

## HTTP integrations

Probirka provides thin adapters for popular Python HTTP frameworks.

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

The adapter returns:

* `200` when all probes succeed
* `500` when at least one probe fails

Both status codes are configurable.

The response body contains `ProbirkaResult.to_dict()` by default; pass `return_results=False` for an empty body.

Adapters are also available for aiohttp (`make_aiohttp_endpoint`) and Django (`make_django_view`).

## Results

Results are represented by typed immutable data classes. `started_at` is timezone-aware in the local
zone of the host, and `elapsed` is measured with a monotonic clock, so it is unaffected by clock
adjustments:

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
    )
```

The result can be converted to a JSON-compatible dictionary:

```python
data = result.to_dict()
```

This makes the same result format usable from custom integrations, HTTP endpoints and monitoring systems.

## Why Probirka?

Probirka deliberately keeps the core small.

It does not try to manage connections, discover services or prescribe how your application should be structured.

Instead, it provides three things:

1. **Probe implementations** — checks for your dependencies.
2. **Execution engine** — concurrency, timeouts, caching and groups.
3. **Integrations** — expose the same result through your HTTP framework.

Your application remains responsible for creating and managing its clients, pools and connections.

## License

MIT
