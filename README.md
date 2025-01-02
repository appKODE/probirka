# PROB🧪RKA

Python 3 library to write simple asynchronous health checks (probes).

[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![PyPI](https://img.shields.io/pypi/v/probirka.svg)](https://pypi.python.org/pypi/probirka)
[![PyPI](https://img.shields.io/pypi/dm/probirka.svg)](https://pypi.python.org/pypi/probirka)

## Overview

Probirka is a Python library designed to facilitate the creation of simple asynchronous health checks, also known as probes. It allows you to define custom probes to monitor the health of various services and components in your application.

## Features

- Simple API for defining asynchronous health checks
- Support for custom probes
- Integration with FastAPI and aiohttp
- Ability to add custom information to health check results
- Grouping of probes for selective execution
- Timeout support for probes

## Installation

Install Probirka using pip:

```shell
pip install probirka
```

## Usage

Here is a simple example of how to use Probirka to create an asynchronous health check:

```python
import asyncio
from probirka import Probe, HealthCheck

class DatabaseProbe(Probe):
    async def check(self):
        # Simulate a database check
        await asyncio.sleep(1)
        return True

class CacheProbe(Probe):
    async def check(self):
        # Simulate a cache check
        await asyncio.sleep(1)
        return False  # Simulate a failed check

async def main():
    health_check = HealthCheck(probes=[DatabaseProbe(), CacheProbe()])
    health_check.add_info("version", "1.0.0")
    health_check.add_info("environment", "production")
    results = await health_check.run()
    print(results)

if __name__ == "__main__":
    asyncio.run(main())
```

This example defines two probes, `DatabaseProbe` and `CacheProbe`, and runs them as part of a health check. The `CacheProbe` simulates a failed check. Additionally, it adds custom user data using the `add_info` method.

Example output:

```python
HealthCheckResult(
    ok=False,
    info={'version': '1.0.0', 'environment': 'production'},
    started_at=datetime.datetime(2023, 10, 10, 10, 0, 0),
    total_elapsed=datetime.timedelta(seconds=1),
    checks=[
        ProbeResult(name='DatabaseProbe', ok=True, elapsed=datetime.timedelta(seconds=1)),
        ProbeResult(name='CacheProbe', ok=False, elapsed=datetime.timedelta(seconds=1))
    ]
)
```

## Integration with FastAPI

You can integrate Probirka with FastAPI as follows:

```python
from fastapi import FastAPI
from probirka import Probirka
from probirka._fastapi import make_fastapi_endpoint

app = FastAPI()

probirka_instance = Probirka()
fastapi_endpoint = make_fastapi_endpoint(probirka_instance)

app.add_api_route("/run", fastapi_endpoint)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## Integration with aiohttp

You can integrate Probirka with aiohttp as follows:

```python
from aiohttp import web
from probirka import Probirka
from probirka._aiohttp import make_aiohttp_endpoint

app = web.Application()

probirka_instance = Probirka()
aiohttp_endpoint = make_aiohttp_endpoint(probirka_instance)

app.router.add_get('/run', aiohttp_endpoint)

if __name__ == '__main__':
    web.run_app(app)
```

## Contributing

Contributions are welcome! Please open an issue or submit a pull request on GitHub.

## License

This project is licensed under the MIT License.
