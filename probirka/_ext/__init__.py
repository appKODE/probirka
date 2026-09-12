"""
Framework adapters built on top of the probirka core (private).

Each submodule imports its framework at module level. Use the public names from the package root,
they are resolved lazily::

    from probirka import make_fastapi_endpoint, make_aiohttp_endpoint, make_django_view
"""
