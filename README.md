# PROB🧪RKA

Framework-agnostic library for running health probes in Python applications, with built-in probes and integrations for popular HTTP frameworks.

[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![PyPI](https://img.shields.io/pypi/v/probirka.svg)](https://pypi.python.org/pypi/probirka)
[![PyPI](https://img.shields.io/pypi/dm/probirka.svg)](https://pypi.python.org/pypi/probirka)
[![Coverage Status](https://coveralls.io/repos/github/appKODE/probirka/badge.svg?branch=main)](https://coveralls.io/github/appKODE/probirka?branch=main)

Documentation: https://appkode.github.io/probirka/

## Installation

```shell
pip install probirka
```

Probirka has no dependencies. Ready-made probes and framework adapters use client libraries that you install alongside (`redis`, `asyncpg`, `fastapi`, ...); a missing one raises an `ImportError` naming the package.

## Quick Start

```python
import asyncio
from probirka import Probirka, TcpProbe

probirka = Probirka(success_ttl=30)
probirka.add_info("version", "1.0.0")

@probirka.add(name="database", timeout=2)
async def check_database():
    return True

@probirka.add(groups=["external"])  # runs only when the group is requested
def check_external_service():
    return True

probirka.add_probes(TcpProbe("smtp.example.com", 25, name="smtp", timeout=2))

async def main():
    result = await probirka.run(with_groups=["external"], timeout=5)
    print(result.ok, result.to_dict())

asyncio.run(main())
```

Probes return `True`/`None` on success and `False` on failure; exceptions and timeouts are reported in `error`. Custom probes subclass `ProbeBase` and implement `async def _check(self)`.

## Ready-made Probes

Importable from `probirka`: `TcpProbe`, `PostgresAsyncpgProbe`, `RedisProbe`, `HttpHttpxProbe`, `HttpHttpx2Probe`, `HttpAiohttpProbe`, `KafkaAiokafkaProbe`, `RabbitmqAiopikaProbe`, `MongoPymongoProbe`, `MongoMotorProbe`. Each takes an existing client of your application (or a function returning it) or a connection string. See [the docs](https://appkode.github.io/probirka/probes.html).

## Framework Adapters

`probirka.ext.fastapi`, `probirka.ext.aiohttp` and `probirka.ext.django` turn a `Probirka` instance into a `/health` endpoint: `200` when all checks pass, `500` otherwise, body is `ProbirkaResult.to_dict()` as JSON.

```python
from fastapi import FastAPI
from probirka.ext.fastapi import make_fastapi_endpoint

app = FastAPI()
app.add_api_route("/health", make_fastapi_endpoint(probirka))
```

See [the docs](https://appkode.github.io/probirka/integration.html) for aiohttp and Django.
