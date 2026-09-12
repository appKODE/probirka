"""
Ready-made probes for common infrastructure dependencies.

Every probe is a plain :class:`probirka.ProbeBase` subclass. ``probirka`` itself has no
dependencies: each probe needs its client library installed separately, and accessing a probe whose
library is missing raises an ``ImportError`` that names the package to install::

    from probirka.probes import RedisProbe  # needs: pip install redis
    from probirka.probes import PostgresAsyncpgProbe  # needs: pip install asyncpg
"""

from importlib import import_module
from typing import TYPE_CHECKING, Any, Dict, List, Tuple

from probirka.probes._common import ClientOrFactory, ProbeFailure
from probirka.probes._tcp import TcpProbe

if TYPE_CHECKING:
    from probirka.probes._http_aiohttp import HttpAiohttpProbe as HttpAiohttpProbe
    from probirka.probes._http_httpx import HttpHttpxProbe as HttpHttpxProbe
    from probirka.probes._http_httpx2 import HttpHttpx2Probe as HttpHttpx2Probe
    from probirka.probes._kafka_aiokafka import KafkaAiokafkaProbe as KafkaAiokafkaProbe
    from probirka.probes._mongo_motor import MongoMotorProbe as MongoMotorProbe
    from probirka.probes._mongo_pymongo import MongoPymongoProbe as MongoPymongoProbe
    from probirka.probes._postgres_asyncpg import PostgresAsyncpgProbe as PostgresAsyncpgProbe
    from probirka.probes._rabbitmq_aiopika import RabbitmqAiopikaProbe as RabbitmqAiopikaProbe
    from probirka.probes._redis import RedisProbe as RedisProbe

__all__ = [
    'ClientOrFactory',
    'HttpAiohttpProbe',
    'HttpHttpx2Probe',
    'HttpHttpxProbe',
    'KafkaAiokafkaProbe',
    'MongoMotorProbe',
    'MongoPymongoProbe',
    'PostgresAsyncpgProbe',
    'ProbeFailure',
    'RabbitmqAiopikaProbe',
    'RedisProbe',
    'TcpProbe',
]

# name -> (module, pip package). Resolved lazily so that importing ``probirka.probes``
# never requires any client library to be installed.
_LAZY: Dict[str, Tuple[str, str]] = {
    'HttpAiohttpProbe': ('probirka.probes._http_aiohttp', 'aiohttp'),
    'HttpHttpx2Probe': ('probirka.probes._http_httpx2', 'httpx2'),
    'HttpHttpxProbe': ('probirka.probes._http_httpx', 'httpx'),
    'KafkaAiokafkaProbe': ('probirka.probes._kafka_aiokafka', 'aiokafka'),
    'MongoMotorProbe': ('probirka.probes._mongo_motor', 'motor'),
    'MongoPymongoProbe': ('probirka.probes._mongo_pymongo', 'pymongo'),
    'PostgresAsyncpgProbe': ('probirka.probes._postgres_asyncpg', 'asyncpg'),
    'RabbitmqAiopikaProbe': ('probirka.probes._rabbitmq_aiopika', 'aio-pika'),
    'RedisProbe': ('probirka.probes._redis', 'redis'),
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
    return getattr(module, name)


def __dir__() -> List[str]:
    return sorted(set(globals()) | set(__all__))
