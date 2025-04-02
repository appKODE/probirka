import os
import sys
sys.path.insert(0, os.path.abspath('..'))

project = 'Probirka'
copyright = '2025, KODE'
author = 'KODE'

# Ссылка на GitHub
html_context = {
    'github_user': 'appKODE',
    'github_repo': 'probirka',
    'display_github': True,
}

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'sphinx.ext.githubpages',
    'sphinx_autodoc_typehints',
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': '__weakref__'
}

add_module_names = False
