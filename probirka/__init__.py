from importlib import import_module
from typing import TYPE_CHECKING, Any, Dict, List, Tuple

from probirka._probes import CallableProbe, Probe, ProbeBase
from probirka._probirka import Probirka
from probirka._results import ProbirkaResult, ProbeResult

if TYPE_CHECKING:
    from probirka.ext.aiohttp import make_aiohttp_endpoint as make_aiohttp_endpoint
    from probirka.ext.django import make_django_view as make_django_view
    from probirka.ext.fastapi import make_fastapi_endpoint as make_fastapi_endpoint

__title__ = 'probirka'
__version__ = '0.0.0'
__url__ = 'https://github.com/appKODE/probirka'
__author__ = 'KODE'
__author_email__ = 'slurm@kode.ru'
__license__ = 'MIT'
__description__ = 'A health check library for Python applications'
__all__ = [
    'CallableProbe',
    'Probe',
    'ProbeBase',
    'ProbeResult',
    'Probirka',
    'ProbirkaResult',
    'make_aiohttp_endpoint',
    'make_django_view',
    'make_fastapi_endpoint',
]

# name -> (module, pip package). Resolved lazily so that importing ``probirka``
# never requires any framework to be installed.
_LAZY: Dict[str, Tuple[str, str]] = {
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
    return getattr(module, name)


def __dir__() -> List[str]:
    return sorted(set(globals()) | set(__all__))
