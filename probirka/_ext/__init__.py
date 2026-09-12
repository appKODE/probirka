"""
Framework adapters built on top of the probirka core (private).

``asgi`` speaks the ASGI protocol directly and needs no third-party package; every other
submodule imports its framework at module level. ``_common`` imports none of them and holds the
shared "run the probes, render the body" step. Use the public names from the package root, the
framework-specific ones are resolved lazily::

    from probirka import make_asgi_app, make_fastapi_endpoint, make_aiohttp_endpoint, make_django_view
"""
