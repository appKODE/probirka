from contextlib import suppress

from probirka._probes import Probe, ProbeBase
from probirka._probirka import Probirka
from probirka._results import HealthCheckResult, ProbeResult

__title__ = 'probirka'
__version__ = '0.0.0'
__url__ = 'https://github.com/appKODE/probirka'
__author__ = 'KODE'
__author_email__ = 'slurm@kode.ru'
__license__ = 'MIT'
__description__ = 'A health check library for Python applications'
__all__ = [
    'HealthCheckResult',
    # types
    'Probe',
    'ProbeBase',
    # results
    'ProbeResult',
    'Probirka',
]

with suppress(ImportError):
    from probirka._aiohttp import make_aiohttp_endpoint  # noqa

    __all__.append('make_aiohttp_endpoint')

with suppress(ImportError):
    from probirka._fastapi import make_fastapi_endpoint  # noqa

    __all__.append('make_fastapi_endpoint')
