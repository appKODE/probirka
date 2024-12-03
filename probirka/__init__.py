from contextlib import suppress

from probirka._probes import Probe, ProbeBase
from probirka._probirka import Probirka
from probirka._results import HealthCheckResult, ProbeResult

__version__ = '0.1.0'
__all__ = [
    'Probirka',
    'ProbeBase',
    # results
    'ProbeResult',
    'HealthCheckResult',
    # types
    'Probe',
]

with suppress(ImportError):
    from probirka._aiohttp import make_aiohttp_endpoint  # noqa

    __all__.append('make_aiohttp_endpoint')


with suppress(ImportError):
    from probirka._fastapi import make_fastapi_endpoint  # noqa

    __all__.append('make_fastapi_endpoint')
