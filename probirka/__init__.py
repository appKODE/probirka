from importlib import import_module
from typing import TYPE_CHECKING, Any, Dict, List, Tuple

from probirka._probes import CallableProbe, Probe, ProbeBase
from probirka._probes._common import ClientOrFactory, ProbeFailure
from probirka._probes._tcp import TcpProbe
from probirka._probirka import Probirka
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
    from probirka.ext.aiohttp import make_aiohttp_endpoint as make_aiohttp_endpoint
    from probirka.ext.django import make_django_view as make_django_view
    from probirka.ext.fastapi import make_fastapi_endpoint as make_fastapi_endpoint

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

# Names that need no third-party package. The lazily resolved names below are deliberately
# not listed here, so ``from probirka import *`` works with nothing but probirka installed.
__all__ = [
    'CallableProbe',
    'ClientOrFactory',
    'Probe',
    'ProbeBase',
    'ProbeFailure',
    'ProbeResult',
    'Probirka',
    'ProbirkaResult',
    'TcpProbe',
]

# name -> (module, pip package). Resolved on first access so that importing ``probirka``
# never requires any client library or framework; a missing one raises an ``ImportError``
# that names the package to install.
_LAZY: Dict[str, Tuple[str, str]] = {
    'HttpAiohttpProbe': ('probirka._probes._http_aiohttp', 'aiohttp'),
    'HttpHttpx2Probe': ('probirka._probes._http_httpx2', 'httpx2'),
    'HttpHttpxProbe': ('probirka._probes._http_httpx', 'httpx'),
    'KafkaAiokafkaProbe': ('probirka._probes._kafka_aiokafka', 'aiokafka'),
    'MongoMotorProbe': ('probirka._probes._mongo_motor', 'motor'),
    'MongoPymongoProbe': ('probirka._probes._mongo_pymongo', 'pymongo'),
    'PostgresAsyncpgProbe': ('probirka._probes._postgres_asyncpg', 'asyncpg'),
    'RabbitmqAiopikaProbe': ('probirka._probes._rabbitmq_aiopika', 'aio-pika'),
    'RedisProbe': ('probirka._probes._redis', 'redis'),
    'make_aiohttp_endpoint': ('probirka.ext.aiohttp', 'aiohttp'),
    'make_django_view': ('probirka.ext.django', 'django'),
    'make_fastapi_endpoint': ('probirka.ext.fastapi', 'fastapi'),
}


def __getattr__(name: str) -> Any:
    try:
        module_name, package = _LAZY[name]
    except KeyError:
        raise AttributeError(f'module {__name__!r} has no attribute {name!r}') from None
    try:
        module = import_module(module_name)
    except ImportError as exc:
        raise ImportError(f"{name} requires the '{package}' package, install it with: pip install {package}") from exc
    value = getattr(module, name)
    globals()[name] = value  # cache: later lookups bypass __getattr__
    return value


def __dir__() -> List[str]:
    return sorted(set(globals()) | set(__all__) | set(_LAZY))
