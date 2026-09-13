import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

project = 'Probirka'
copyright = '2025, KODE'
author = 'KODE'

# "Edit on GitHub" link of the Read the Docs theme
html_context = {
    'github_user': 'appKODE',
    'github_repo': 'probirka',
    'github_version': 'main',
    'conf_py_path': '/docs/source/',
    'display_github': True,
}

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
    'sphinx.ext.viewcode',
    'sphinx.ext.githubpages',
    'sphinx_autodoc_typehints',
]

exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
html_title = 'Probirka'
html_theme_options = {
    'navigation_depth': 3,
}

# Standard library types in signatures become links instead of bare text.
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
}

autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'undoc-members': True,
    'exclude-members': '__weakref__',
}
# Merge the ``__init__`` docstring into the class description, so probes that inherit their
# constructor (the HTTP and MongoDB ones) still document their arguments.
autoclass_content = 'both'

# Classes are documented under their public import path (``probirka.RedisProbe``),
# so module prefixes would only add noise.
add_module_names = False

always_use_bars_union = True
