"""
Lazy resolution of the public names that need a third-party package (private).

The package root binds :func:`module_getattr` and :func:`module_dir` as its PEP 562 hooks, so that
``import probirka`` never imports a client library or a framework: a probe or an adapter is
imported on first access, and :class:`MissingDependencyError` tells which package to install
when that fails.
"""

from __future__ import annotations

import sys
from importlib import import_module
from importlib.util import find_spec
from typing import Any

ROOT = __name__.rpartition('.')[0]
"""The package whose namespace caches the resolved names (``probirka``)."""


class MissingDependencyError(ImportError):
    """
    Raised when a lazily loaded name needs a package that is not installed.

    Deliberately an ``ImportError`` rather than an ``AttributeError``: ``from probirka import X``
    turns an ``AttributeError`` into a bare "cannot import name", dropping the install hint.
    The consequence is that ``hasattr(probirka, 'RedisProbe')`` raises on a bare install; use
    ``importlib.util.find_spec`` to feature-detect a client library instead.
    """


# name -> (module, import name, pip package). Resolved on first access so that importing
# ``probirka`` never requires any client library or framework.
LAZY: dict[str, tuple[str, str, str]] = {
    'HttpAiohttpProbe': ('probirka._probes._http_aiohttp', 'aiohttp', 'aiohttp'),
    'HttpHttpx2Probe': ('probirka._probes._http_httpx2', 'httpx2', 'httpx2'),
    'HttpHttpxProbe': ('probirka._probes._http_httpx', 'httpx', 'httpx'),
    'KafkaAiokafkaProbe': ('probirka._probes._kafka_aiokafka', 'aiokafka', 'aiokafka'),
    'MongoMotorProbe': ('probirka._probes._mongo_motor', 'motor', 'motor'),
    'MongoPymongoProbe': ('probirka._probes._mongo_pymongo', 'pymongo', 'pymongo'),
    'PostgresAsyncpgProbe': ('probirka._probes._postgres_asyncpg', 'asyncpg', 'asyncpg'),
    'RabbitmqAiopikaProbe': ('probirka._probes._rabbitmq_aiopika', 'aio_pika', 'aio-pika'),
    'RedisProbe': ('probirka._probes._redis', 'redis', 'redis'),
    'make_aiohttp_endpoint': ('probirka._ext.aiohttp', 'aiohttp', 'aiohttp'),
    'make_django_view': ('probirka._ext.django', 'django', 'django'),
    'make_fastapi_endpoint': ('probirka._ext.fastapi', 'fastapi', 'fastapi'),
}


def installed(import_name: str) -> bool:
    """
    Report whether a package can be imported, without importing it.

    :param import_name: The top-level import name of the package.
    :return: ``True`` if an import spec is found.
    """
    try:
        return find_spec(import_name) is not None
    except ImportError:
        return False


def available() -> list[str]:
    """
    List the lazily resolved names whose package is installed.

    The package root appends them to ``__all__``, so ``from probirka import *`` brings the adapters
    and probes you can actually use and still works with nothing but probirka installed.

    :return: The names, sorted.
    """
    return [name for name, (_, import_name, _) in sorted(LAZY.items()) if installed(import_name)]


def module_getattr(name: str) -> Any:
    """
    Resolve a lazily loaded name of the package root (its PEP 562 ``__getattr__``).

    :param name: The attribute looked up on the package.
    :return: The probe class or adapter factory.
    :raises AttributeError: If the name is not a lazily loaded one.
    :raises MissingDependencyError: If the package the name needs is not installed.
    """
    try:
        module_name, import_name, package = LAZY[name]
    except KeyError:
        msg = f'module {ROOT!r} has no attribute {name!r}'
        raise AttributeError(msg) from None
    try:
        module = import_module(module_name)
    except ModuleNotFoundError as exc:
        # only "the package itself is not installed" gets the install hint; a too-old or broken
        # install (e.g. ``redis`` without ``redis.asyncio``) keeps its original error
        if exc.name == import_name:
            msg = f"{name} requires the '{package}' package, install it with: pip install {package}"
            raise MissingDependencyError(msg) from exc
        raise
    value = getattr(module, name)
    setattr(sys.modules[ROOT], name, value)  # cache: later lookups bypass __getattr__
    return value


def module_dir() -> list[str]:
    """
    List the attributes of the package root, lazily loaded names included (its PEP 562 ``__dir__``).

    :return: The attribute names, sorted.
    """
    root = sys.modules[ROOT]
    return sorted(set(vars(root)) | set(root.__all__))
