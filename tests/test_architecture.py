"""Layout rules: ``__init__`` files only re-export, siblings import concrete modules, layers are one-way."""

import ast
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parents[1] / 'probirka'
MODULES = sorted(PACKAGE.rglob('*.py'))

# layer -> packages it must never import (a leaf lists the whole package)
FORBIDDEN = {
    'probirka._lazy': ('probirka',),
    'probirka._redact': ('probirka',),
    'probirka._results': ('probirka._probes', 'probirka._probirka', 'probirka._ext'),
    'probirka._probes': ('probirka._probirka', 'probirka._ext'),
    'probirka._probirka': ('probirka._ext',),
    'probirka._ext': ('probirka._probes',),
}


def module_name(path: Path) -> str:
    parts = path.relative_to(PACKAGE.parent).with_suffix('').parts
    return '.'.join(parts[:-1] if parts[-1] == '__init__' else parts)


def is_in(module: str, package: str) -> bool:
    return module == package or module.startswith(package + '.')


def package_imports(path: Path) -> list[str]:
    imported: list[str] = []
    for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
        if isinstance(node, ast.Import):
            imported += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    return [name for name in imported if is_in(name, 'probirka')]


def is_reexport(index: int, node: ast.stmt) -> bool:
    if isinstance(node, ast.Expr):  # the docstring
        return index == 0 and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)
    if isinstance(node, ast.Import | ast.ImportFrom):
        return True
    if isinstance(node, ast.If):  # ``if TYPE_CHECKING:`` with imports only
        is_type_checking = isinstance(node.test, ast.Name) and node.test.id == 'TYPE_CHECKING'
        only_imports = all(isinstance(n, ast.Import | ast.ImportFrom) for n in node.body)
        return is_type_checking and not node.orelse and only_imports
    if isinstance(node, ast.Assign | ast.AugAssign):  # ``__all__``, ``__version__``, ``__getattr__ = ...``
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        return all(isinstance(t, ast.Name) and t.id.startswith('__') and t.id.endswith('__') for t in targets)
    return False


@pytest.mark.parametrize('path', [p for p in MODULES if p.name == '__init__.py'], ids=module_name)
def test_init_files_only_reexport(path: Path) -> None:
    body = ast.parse(path.read_text(encoding='utf-8')).body
    offending = [f'line {n.lineno}: {type(n).__name__}' for i, n in enumerate(body) if not is_reexport(i, n)]
    assert not offending, offending


@pytest.mark.parametrize('path', MODULES, ids=module_name)
def test_imports_are_concrete_and_layered(path: Path) -> None:
    name = module_name(path)
    own_package = name.rpartition('.')[0]
    imports = package_imports(path)
    for imported in imports:
        assert imported != 'probirka', f'{name} imports the package root'
        if name == 'probirka':
            assert imported.count('.') == 1, f'the root reaches into {imported}; import it through its package'
        if own_package != 'probirka':
            assert imported != own_package, f'{name} imports its own package instead of a sibling module'
    forbidden = [pkg for layer, pkgs in FORBIDDEN.items() if is_in(name, layer) for pkg in pkgs]
    crossing = [imp for imp in imports if any(is_in(imp, pkg) for pkg in forbidden)]
    assert not crossing, f'{name} imports {crossing}'
