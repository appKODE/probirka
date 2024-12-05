# 🧪: PROBIRKA 

Async health checks for monitoring purposes

[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![PyPI](https://img.shields.io/pypi/v/probirka.svg)](https://pypi.python.org/pypi/probirka)
[![PyPI](https://img.shields.io/pypi/dm/probirka.svg)](https://pypi.python.org/pypi/probirka)

## Installation

```shell
pip install probirka
```

## Basic usage

```python
from asyncio import sleep, run
from dataclasses import asdict
from pprint import pprint

from probirka import Probirka, make_fastapi_endpoint

checks = Probirka()
checks.add_info("project", "example")
checks.add_info("version", "0.1.0")


@checks.add()
def ok_check():
  5 / 1


@checks.add()
def error_check():
  5 / 0


@checks.add()
async def async_check():
  await sleep(1)


async def main():
  results = await checks.run()
  pprint(asdict(results))


if __name__ == "__main__":
  run(main())

# {'elapsed': datetime.timedelta(seconds=1, microseconds=1506),
#  'extra': {'project': 'example', 'version': '0.1.0'},
#  'ok': False,
#  'results': [{'elapsed': datetime.timedelta(microseconds=7),
#               'error': None,
#               'name': 'ok_check',
#               'ok': True,
#               'started_at': datetime.datetime(2024, 6, 4, 23, 1, 53, 471363)},
#              {'elapsed': datetime.timedelta(microseconds=4),
#               'error': 'division by zero',
#               'name': 'error_check',
#               'ok': False,
#               'started_at': datetime.datetime(2024, 6, 4, 23, 1, 53, 471376)},
#              {'elapsed': datetime.timedelta(seconds=1, microseconds=1259),
#               'error': None,
#               'name': 'async_check',
#               'ok': True,
#               'started_at': datetime.datetime(2024, 6, 4, 23, 1, 53, 471383)}],
#  'started_at': datetime.datetime(2024, 6, 4, 23, 1, 53, 471324)}
```

## Custom probes

```python
from asyncio import run
import os
from typing import Optional

import asyncpg
from probirka import ProbeBase, Probirka


class PGCheck(
  ProbeBase,
):
  def __init__(
    self,
    dsn: str,
    name: Optional[str] = None,
    timeout: Optional[int] = None,
    is_optional: bool = False,
  ) -> None:
    self._dsn = dsn
    super().__init__(
      name=name,
      timeout=timeout,
      is_optional=is_optional,
    )

  async def _check(
    self,
  ) -> Optional[bool]:
    conn = None
    try:
      conn = await asyncpg.connect(dsn=self._dsn)
      await conn.fetch("SELECT 1")
    finally:
      if conn:
        await conn.close()
    return True


checks = Probirka()


async def main():
  checks.add_probe(
    PGCheck(dsn=os.environ['PG_DSN']),
  )
  results = await checks.run()
  assert results.ok


if __name__ == "__main__":
  run(main())
```

## Mask your secrets

```python
from asyncio import run
from dataclasses import asdict
from pprint import pprint

from probirka import Probirka, JsonRegularTypes


def mask_sensitive_data(
    name: str,
    value: JsonRegularTypes,
) -> JsonRegularTypes:
    if "secret" in name or "secret" in value:
        return "***"
    return value


checks = Probirka(
    mask_sensitive_info_data_cb=mask_sensitive_data,
)
checks.add_info("project", "example")
checks.add_info("version", "0.1.0")
checks.add_info("top_secret_one", "wow")
checks.add_info(
    "settings",
    {
        "top_secret_two": 123456,
        "foo": "bar",
        "baz": ["top@secret", "something"],
    },
)


async def main():
    results = await checks.run()
    pprint(asdict(results))


if __name__ == "__main__":
    run(main())


# {'checks': [],
#  'info': {'project': 'example',
#           'settings': {'baz': ['***', 'something'],
#                        'foo': 'bar',
#                        'top_secret_two': '***'},
#           'top_secret_one': '***',
#           'version': '0.1.0'},
#  'ok': True,
#  'started_at': datetime.datetime(2024, 6, 5, 10, 56, 20, 736558),
#  'total_elapsed': datetime.timedelta(microseconds=10)}
```

## FastAPI endpoint

```python
from fastapi import FastAPI
from uvicorn import run

from probirka import Probirka, make_fastapi_endpoint

app = FastAPI()

checks = Probirka()
checks.add_info("project", "fastapi example")
checks.add_info("version", "0.1.0")


@checks.add()
def empty_check():
  pass


if __name__ == "__main__":
  app.add_api_route(
    "/health",
    endpoint=make_fastapi_endpoint(checks, return_results=False),
  )
  app.add_api_route(
    "/self-check",
    endpoint=make_fastapi_endpoint(checks, with_optional=True),
  )
  run(app)
```


## AIOHTTP endpoint

```python
from aiohttp import web

from probirka import Probirka, make_aiohttp_endpoint

app = web.Application()

checks = Probirka()
checks.add_info("project", "fastapi example")
checks.add_info("version", "0.1.0")


@checks.add()
def empty_check():
    pass


if __name__ == "__main__":
    app.router.add_get(
        "/health",
        handler=make_aiohttp_endpoint(checks, return_results=False),
    )
    app.router.add_get(
        "/self-check",
        handler=make_aiohttp_endpoint(checks, with_optional=True),
    )
    web.run_app(app)
```
