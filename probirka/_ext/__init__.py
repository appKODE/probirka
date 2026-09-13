"""
Framework adapters built on top of the probirka core (private).

``asgi`` speaks the ASGI protocol directly and needs no third-party package; every other
submodule imports its framework at module level. ``_common`` imports none of them and holds the
shared "run the probes, render the body" step. Use the public names from the package root, the
framework-specific ones are resolved lazily and are re-exported here for type checkers only::

    from probirka import make_asgi_app, make_fastapi_endpoint, make_aiohttp_endpoint, make_django_view
"""

from typing import TYPE_CHECKING

from probirka._ext.asgi import make_asgi_app

if TYPE_CHECKING:
    from probirka._ext.aiohttp import make_aiohttp_endpoint as make_aiohttp_endpoint
    from probirka._ext.django import make_django_view as make_django_view
    from probirka._ext.fastapi import make_fastapi_endpoint as make_fastapi_endpoint

__all__ = ['make_asgi_app']
