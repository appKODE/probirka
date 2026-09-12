import subprocess
import sys
import textwrap
from importlib import import_module

import pytest

import probirka

BLOCKED = (
    'fastapi',
    'aiohttp',
    'django',
    'redis',
    'asyncpg',
    'httpx',
    'httpx2',
    'aiokafka',
    'aio_pika',
    'pymongo',
    'motor',
)

# Runs in a subprocess so that already-imported client libraries do not leak in.
SCRIPT = textwrap.dedent(
    """
    import sys
    from importlib.abc import MetaPathFinder

    BLOCKED = %r

    class Blocker(MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if fullname.split('.')[0] in BLOCKED:
                raise ImportError(f'{fullname} is blocked')
            return None

    sys.meta_path.insert(0, Blocker())

    import probirka
    from probirka import *  # noqa: F403  -- must not touch lazy names
    from probirka import TcpProbe, ProbeFailure, ProbeBase, Probirka

    assert 'RedisProbe' in dir(probirka)
    assert 'make_fastapi_endpoint' in dir(probirka)

    for name in probirka._LAZY:
        try:
            getattr(probirka, name)
        except ImportError as exc:
            assert 'pip install' in str(exc), exc
        else:
            raise AssertionError(f'{name} should not be importable')

    try:
        probirka.NoSuchProbe
    except AttributeError:
        pass
    else:
        raise AssertionError('unknown names must raise AttributeError')

    print('OK')
    """
    % (BLOCKED,)
)


def test_core_imports_without_any_dependency() -> None:
    proc = subprocess.run([sys.executable, '-c', SCRIPT], capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == 'OK'


def test_lazy_names_are_not_in_all() -> None:
    assert not set(probirka._LAZY) & set(probirka.__all__)


def test_unknown_attribute_raises_attribute_error() -> None:
    with pytest.raises(AttributeError):
        probirka.no_such_thing  # noqa: B018


@pytest.mark.parametrize(('name', 'module_name'), sorted(probirka._LAZY.items()))
def test_lazy_name_resolves_to_the_real_object(name: str, module_name: 'tuple[str, str]') -> None:
    module_path, package = module_name
    pytest.importorskip(package.replace('-', '_'))
    if package == 'django':
        pytest.importorskip('tests.test_django')  # configures django settings

    assert getattr(probirka, name) is getattr(import_module(module_path), name)
