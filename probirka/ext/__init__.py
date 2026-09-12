"""
Framework adapters built on top of the probirka core.

Each submodule imports its framework at module level, so import only the one you use::

    from probirka.ext.fastapi import make_fastapi_endpoint
    from probirka.ext.aiohttp import make_aiohttp_endpoint
    from probirka.ext.django import make_django_view

The same names are also reachable from the ``probirka`` package for backward compatibility.
"""
