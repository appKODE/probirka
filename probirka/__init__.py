"""
Framework-agnostic health probes for Python applications.

Every public name is importable from this package. The names that need a third-party package
(the ready-made probes, the framework adapters) are resolved on first access, see
:mod:`probirka._lazy`; ``__all__`` lists them only when their package is installed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from probirka._ext import make_asgi_app
from probirka._lazy import MissingDependencyError
from probirka._lazy import available as _available
from probirka._lazy import module_dir as _module_dir
from probirka._lazy import module_getattr as _module_getattr
from probirka._probes import (
    CallableProbe,
    ClientOrFactory,
    HttpProbePolicy,
    HttpProbePolicyViolation,
    Probe,
    ProbeBase,
    ProbeFailure,
    TcpProbe,
)
from probirka._probirka import Probirka
from probirka._redact import MASK, mask_url, redact_value
from probirka._results import ProbeResult, ProbirkaResult

if TYPE_CHECKING:
    from probirka._ext.aiohttp import make_aiohttp_endpoint as make_aiohttp_endpoint
    from probirka._ext.django import make_django_view as make_django_view
    from probirka._ext.fastapi import make_fastapi_endpoint as make_fastapi_endpoint
    from probirka._probes._http_aiohttp import HttpAiohttpProbe as HttpAiohttpProbe
    from probirka._probes._http_httpx import HttpHttpxProbe as HttpHttpxProbe
    from probirka._probes._http_httpx2 import HttpHttpx2Probe as HttpHttpx2Probe
    from probirka._probes._kafka_aiokafka import KafkaAiokafkaProbe as KafkaAiokafkaProbe
    from probirka._probes._mongo_motor import MongoMotorProbe as MongoMotorProbe
    from probirka._probes._mongo_pymongo import MongoPymongoProbe as MongoPymongoProbe
    from probirka._probes._postgres_asyncpg import PostgresAsyncpgProbe as PostgresAsyncpgProbe
    from probirka._probes._rabbitmq_aiopika import RabbitmqAiopikaProbe as RabbitmqAiopikaProbe
    from probirka._probes._redis import RedisProbe as RedisProbe

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

# PEP 562: looked up in this namespace, implemented in probirka._lazy
__getattr__ = _module_getattr
__dir__ = _module_dir

# Names that need no third-party package; the lazily resolved names whose package is installed
# follow. ``make_asgi_app`` speaks the ASGI protocol directly, so it needs no framework.
__all__ = [
    'MASK',
    'CallableProbe',
    'ClientOrFactory',
    'HttpProbePolicy',
    'HttpProbePolicyViolation',
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
__all__ += list(_available())  # list(): ruff (PLE0605) only follows list/tuple extensions of __all__
