# PROB🧪RKA

Python 3 library to write simple asynchronous health checks (probes).

[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![PyPI](https://img.shields.io/pypi/v/probirka.svg)](https://pypi.python.org/pypi/probirka)
[![PyPI](https://img.shields.io/pypi/dm/probirka.svg)](https://pypi.python.org/pypi/probirka)
[![Coverage Status](https://coveralls.io/repos/github/appKODE/probirka/badge.svg?branch=polish-docs)](https://coveralls.io/github/appKODE/probirka?branch=polish-docs)

## Overview

Probirka is a lightweight and flexible Python library for implementing asynchronous health checks in your applications. It provides a simple yet powerful API for monitoring the health of various components and services, making it ideal for microservices architectures, containerized applications, and distributed systems.

## Installation

Install Probirka using pip:

```shell
pip install probirka
```

## Quick Start

Here is a simple example of how to use Probirka to create health checks using decorators:

```python
import asyncio
from probirka import Probirka

# Create a Probirka instance
probirka = Probirka()

# Add some custom information
probirka.add_info("version", "1.0.0")
probirka.add_info("environment", "production")

# Define health checks using decorators
@probirka.add(name="database")  # This probe will always run
async def check_database():
    # Simulate a database check
    await asyncio.sleep(1)
    return True

@probirka.add(groups=["cache"])  # This probe will only run when cache group is requested
async def check_cache():
    # Simulate a cache check
    await asyncio.sleep(1)
    return False  # Simulate a failed check

@probirka.add(groups=["external"])  # This probe will only run when external group is requested
def check_external_service():
    # Synchronous check example
    return True

async def main():
    # Run only required probes (without groups)
    basic_results = await probirka.run()
    print("Basic check results:", basic_results)
    
    # Run required probes + cache group probes
    cache_results = await probirka.run(with_groups=["cache"])
    print("Cache check results:", cache_results)
    
    # Run required probes + multiple groups
    full_results = await probirka.run(with_groups=["cache", "external"])
    print("Full check results:", full_results)

if __name__ == "__main__":
    asyncio.run(main())
```

Alternatively, you can create custom probes by inheriting from the `ProbeBase` class:

```python
from probirka import Probirka, ProbeBase
import asyncio

class DatabaseProbe(ProbeBase):
    async def _check(self):
        # Simulate a database check
        await asyncio.sleep(1)
        return True

class CacheProbe(ProbeBase):
    async def _check(self):
        # Simulate a cache check
        await asyncio.sleep(1)
        return False  # Simulate a failed check

async def main():
    probirka = Probirka(probes=[DatabaseProbe(), CacheProbe()])
    probirka.add_info("version", "1.0.0")
    probirka.add_info("environment", "production")
    results = await probirka.run()
    print(results)

if __name__ == "__main__":
    asyncio.run(main())
```

## Advanced Usage

### Creating Custom Probes

You can create custom probes by inheriting from the `ProbeBase` class:

```python
from probirka import ProbeBase
import asyncio

class CustomProbe(ProbeBase):
    def __init__(self, name="CustomProbe"):
        super().__init__(name=name)
        
    async def _check(self):
        # Implement your health check logic here
        return True
```

### Adding Metadata to Probes

You can add metadata to your probes:

```python
from probirka import ProbeBase
import asyncio

class DatabaseProbe(ProbeBase):
    async def _check(self):
        await asyncio.sleep(1)
        self.add_info("connection_pool_size", 10)
        self.add_info("active_connections", 5)
        return True
```

The added information will be included in the probe results and can be accessed through the `info` field of each probe result. This is useful for providing additional context about the probe's state or performance metrics.

### Grouping Probes

Probes can be organized into required and optional groups. Probes without groups are always executed, while probes with groups are only executed when explicitly requested:

```python
import asyncio
from probirka import Probirka

# Create a Probirka instance
probirka = Probirka()

# Required probe (will always run)
@probirka.add(name="database")
async def check_database():
    await asyncio.sleep(1)
    return True

# Optional probes (will only run when their groups are requested)
@probirka.add(groups=["cache"])
async def check_cache():
    await asyncio.sleep(1)
    return True

@probirka.add(groups=["external"])
async def check_external_service():
    return True

async def main():
    # Run only required probes (database)
    basic_results = await probirka.run()
    print("Basic check results:", basic_results)

    # Run required probes + cache group
    cache_results = await probirka.run(with_groups=["cache"])
    print("Cache check results:", cache_results)

    # Run required probes + multiple groups
    full_results = await probirka.run(with_groups=["cache", "external"])
    print("Full check results:", full_results)

if __name__ == "__main__":
    asyncio.run(main())
```

### Setting Timeouts

You can set timeouts for individual probes:

```python
from probirka import ProbeBase
import asyncio

class SlowProbe(ProbeBase):
    async def _check(self):
        await asyncio.sleep(2)  # This will timeout
        return True

probe = SlowProbe(timeout=1.0)  # 1 second timeout
```

### Caching Results

```python
from typing import Optional
from probirka import Probirka, ProbeBase
import asyncio

# Create a Probirka instance with global caching settings
probirka = Probirka(success_ttl=60, failed_ttl=10)  # Cache successful results for 60s, failed for 10s

# Add a probe with custom caching settings
@probirka.add(success_ttl=300)  # Cache successful results for 5 minutes
async def check_database():
    # Simulate a database check
    await asyncio.sleep(1)
    return True

# Or create a custom probe with caching
class DatabaseProbe(ProbeBase):
    def __init__(self, success_ttl: Optional[int] = None, failed_ttl: Optional[int] = None):
        super().__init__(success_ttl=success_ttl, failed_ttl=failed_ttl)
        
    async def _check(self) -> bool:
        # Simulate a database check
        await asyncio.sleep(1)
        return True
```

The caching mechanism works as follows:
- If `success_ttl` is set, successful results will be cached for the specified number of seconds
- If `failed_ttl` is set, failed results will be cached for the specified number of seconds
- If both are set to `None` (default), no caching will be performed
- Global settings in `Probirka` instance can be overridden by individual probe settings

## Integration Examples

### FastAPI Integration

```python
from fastapi import FastAPI
from probirka import Probirka, make_fastapi_endpoint

app = FastAPI()
probirka_instance = Probirka()

# Define some health checks
@probirka_instance.add(name="api")
async def check_api():
    return True


# Create and add the endpoint
fastapi_endpoint = make_fastapi_endpoint(probirka_instance)
app.add_route("/health", fastapi_endpoint)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### aiohttp Integration

```python
from aiohttp import web
from probirka import Probirka, make_aiohttp_endpoint

app = web.Application()
probirka_instance = Probirka()

# Define some health checks
@probirka_instance.add(name="api")
async def check_api():
    return True

# Create and add the endpoint
aiohttp_endpoint = make_aiohttp_endpoint(probirka_instance)
app.router.add_get('/health', aiohttp_endpoint)

if __name__ == '__main__':
    web.run_app(app)
```
