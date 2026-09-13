"""
Ready-made probes (private), built on the core in :mod:`probirka._probe`.

Only the names that need no third-party package are re-exported at runtime. The probes that need
a client library live in their own modules and are resolved lazily from the package root; they
are re-exported here for type checkers only, so ``probirka._probes.RedisProbe`` does not exist at
runtime::

    from probirka import RedisProbe
"""

from typing import TYPE_CHECKING

from probirka._probes._common import ClientOrFactory
from probirka._probes._http_policy import HttpProbePolicy, HttpProbePolicyViolation
from probirka._probes._tcp import TcpProbe

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

__all__ = [
    'ClientOrFactory',
    'HttpProbePolicy',
    'HttpProbePolicyViolation',
    'TcpProbe',
]
