from __future__ import annotations

from importlib import import_module
from importlib.util import find_spec
from typing import TYPE_CHECKING, Any

from probirka._ext.asgi import make_asgi_app
from probirka._probes import CallableProbe, Probe, ProbeBase
from probirka._probes._common import ClientOrFactory, ProbeFailure
from probirka._probes._tcp import TcpProbe
from probirka._probirka import Probirka
from probirka._redact import MASK, mask_url, redact_value
from probirka._results import ProbirkaResult, ProbeResult

if TYPE_CHECKING:
    from probirka._probes._http_aiohttp import HttpAiohttpProbe as HttpAiohttpProbe
    from probirka._probes._http_httpx import HttpHttpxProbe as HttpHttpxProbe
    from probirka._probes._http_httpx2 import HttpHttpx2Probe as HttpHttpx2Probe
    from probirka._probes._kafka_aiokafka import KafkaAiokafkaProbe as KafkaAiokafkaProbe
    from probirka._probes._mongo_motor import MongoMotorProbe as MongoMotorProbe
    from probirka._probes._mongo_pymongo import MongoPymongoProbe as MongoPymongoProbe
    from probirka._probes._postgres_asyncpg import PostgresAsyncpgProbe as PostgresAsyncpgProbe
    from probirka._probes._rabbitmq_aiopika import RabbitmqAiopikaProbe as RabbitmqAiopikaProbe
    from probirka._probes._redis import RedisProbe as RedisProbe
    from probirka._ext.aiohttp import make_aiohttp_endpoint as make_aiohttp_endpoint
    from probirka._ext.django import make_django_view as make_django_view
    from probirka._ext.fastapi import make_fastapi_endpoint as make_fastapi_endpoint

__title__ = 'probirka'
__version__ = '0.0.0'
__url__ = 'https://github.com/appKODE/probirka'
__author__ = 'KODE'
__author_email__ = 'slurm@kode.ru'
__license__ = 'MIT'
__description__ = (
    'Framework-agnostic library for running health probes in Python applications, '
    'with built-in probes and integrations for popular HTTP frameworks.'
)


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
_LAZY: dict[str, tuple[str, str, str]] = {
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


def _installed(import_name: str) -> bool:
    try:
        return find_spec(import_name) is not None
    except ImportError:
        return False


# Names that need no third-party package, plus the lazily resolved names whose package is
# installed. So ``from probirka import *`` brings the adapters and probes you can actually use
# and still works with nothing but probirka installed. ``make_asgi_app`` is in the first group:
# it speaks the ASGI protocol directly, so it needs no framework to be installed.
__all__ = [
    'MASK',
    'CallableProbe',
    'ClientOrFactory',
    'MissingDependencyError',
    'Probe',
    'ProbeBase',
    'ProbeFailure',
    'ProbeResult',
    'Probirka',
    'ProbirkaResult',
    'TcpProbe',
    'make_asgi_app',
    'mask_url',
    'redact_value',
]
__all__ += [name for name, (_, import_name, _) in sorted(_LAZY.items()) if _installed(import_name)]


def __getattr__(name: str) -> Any:
    try:
        module_name, import_name, package = _LAZY[name]
    except KeyError:
        raise AttributeError(f'module {__name__!r} has no attribute {name!r}') from None
    try:
        module = import_module(module_name)
    except ModuleNotFoundError as exc:
        # only "the package itself is not installed" gets the install hint; a too-old or broken
        # install (e.g. ``redis`` without ``redis.asyncio``) keeps its original error
        if exc.name == import_name:
            raise MissingDependencyError(
                f"{name} requires the '{package}' package, install it with: pip install {package}"
            ) from exc
        raise
    value = getattr(module, name)
    globals()[name] = value  # cache: later lookups bypass __getattr__
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
