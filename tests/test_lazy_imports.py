import subprocess
import sys
import textwrap

import pytest

import probirka
import probirka.probes

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
    import probirka.probes
    from probirka.probes import TcpProbe, ProbeFailure

    assert 'RedisProbe' in dir(probirka.probes)
    assert 'make_fastapi_endpoint' in dir(probirka)

    for name in ('make_fastapi_endpoint', 'make_aiohttp_endpoint', 'make_django_view'):
        try:
            getattr(probirka, name)
        except ImportError as exc:
            assert 'pip install' in str(exc), exc
        else:
            raise AssertionError(f'{name} should not be importable')

    for name in probirka.probes._LAZY:
        try:
            getattr(probirka.probes, name)
        except ImportError as exc:
            assert 'pip install' in str(exc), exc
        else:
            raise AssertionError(f'{name} should not be importable')

    try:
        probirka.probes.NoSuchProbe
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


def test_probes_lazy_names_match_all() -> None:
    assert set(probirka.probes._LAZY) < set(probirka.probes.__all__)
    assert set(probirka._LAZY) < set(probirka.__all__)


def test_unknown_attribute_raises_attribute_error() -> None:
    with pytest.raises(AttributeError):
        probirka.no_such_thing  # noqa: B018
    with pytest.raises(AttributeError):
        probirka.probes.NoSuchProbe  # noqa: B018


@pytest.mark.parametrize(
    ('name', 'module'),
    [
        ('make_fastapi_endpoint', 'fastapi'),
        ('make_aiohttp_endpoint', 'aiohttp'),
        ('make_django_view', 'django'),
    ],
)
def test_root_import_is_the_ext_function(name: str, module: str) -> None:
    pytest.importorskip(module)
    if module == 'django':
        pytest.importorskip('tests.test_django')  # configures django settings
    from importlib import import_module

    assert getattr(probirka, name) is getattr(import_module(f'probirka.ext.{module}'), name)
