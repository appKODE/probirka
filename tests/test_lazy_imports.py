import importlib.util
import subprocess
import sys
import textwrap
from importlib import import_module
from pathlib import Path

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
                raise ModuleNotFoundError(f'{fullname} is blocked', name=fullname)
            return None

    sys.meta_path.insert(0, Blocker())

    import probirka
    from probirka import *  # noqa: F403  -- must not touch lazy names
    from probirka import TcpProbe, ProbeFailure, ProbeBase, Probirka

    # nothing is installed, so no lazy name is advertised
    assert not set(probirka._LAZY) & set(probirka.__all__)
    assert not set(probirka._LAZY) & set(dir(probirka))

    for name in probirka._LAZY:
        try:
            getattr(probirka, name)
        except probirka.MissingDependencyError as exc:
            assert 'pip install' in str(exc), exc
            assert isinstance(exc.__cause__, ModuleNotFoundError)
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


def test_broken_install_keeps_the_original_error(tmp_path: Path) -> None:
    """A package that is installed but too old must not be reported as missing."""
    stub = tmp_path / 'redis' / 'asyncio'
    stub.mkdir(parents=True)
    (tmp_path / 'redis' / '__init__.py').write_text('')
    (stub / '__init__.py').write_text("raise ImportError('cannot import name Redis')")  # like redis < 4.2
    script = textwrap.dedent(
        """
        import sys
        sys.path.insert(0, %r)
        import probirka
        try:
            probirka.RedisProbe
        except probirka.MissingDependencyError:
            raise AssertionError('must not be reported as a missing package')
        except ImportError as exc:
            assert 'cannot import name Redis' in str(exc), exc
        else:
            raise AssertionError('should not be importable')
        print('OK')
        """
        % (str(tmp_path),)
    )

    proc = subprocess.run([sys.executable, '-c', script], capture_output=True, text=True, check=False)

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == 'OK'


def test_all_lists_lazy_names_whose_package_is_installed() -> None:
    for name, (_, import_name, _) in probirka._LAZY.items():
        installed = importlib.util.find_spec(import_name) is not None
        assert (name in probirka.__all__) is installed, name
        assert (name in dir(probirka)) is installed, name


def test_star_import_brings_available_adapters_and_probes() -> None:
    namespace: dict = {}  # type: ignore[type-arg]
    exec('from probirka import *', namespace)  # noqa: S102
    for name in probirka.__all__:
        assert name in namespace, name


def test_unknown_attribute_raises_attribute_error() -> None:
    with pytest.raises(AttributeError):
        probirka.no_such_thing  # noqa: B018


@pytest.mark.parametrize(('name', 'spec'), sorted(probirka._LAZY.items()))
def test_lazy_name_resolves_to_the_real_object(name: str, spec: 'tuple[str, str, str]') -> None:
    module_path, import_name, package = spec
    pytest.importorskip(import_name)
    if package == 'django':
        pytest.importorskip('tests.test_django')  # configures django settings

    assert getattr(probirka, name) is getattr(import_module(module_path), name)
