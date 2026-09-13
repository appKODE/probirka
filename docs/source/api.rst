API Reference
=============

Core Classes
------------

.. automodule:: probirka._probes._base
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: probirka._probirka
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: probirka._results
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: probirka._lazy
   :members: MissingDependencyError
   :show-inheritance:

Secrets
-------

``MASK``, ``mask_url`` and ``redact_value`` are importable from the ``probirka`` package.

.. automodule:: probirka._redact
   :members:
   :undoc-members:

Ready-made Probes
-----------------

All probes below are importable from the ``probirka`` package, e.g. ``from probirka import RedisProbe``,
and so are ``HttpProbePolicy`` and ``HttpProbePolicyViolation``.

.. automodule:: probirka._probes._common
   :members: ProbeFailure, resolve
   :show-inheritance:

.. automodule:: probirka._probes._client_base
   :members:
   :show-inheritance:

.. automodule:: probirka._probes._tcp
   :members:
   :show-inheritance:

.. automodule:: probirka._probes._postgres_asyncpg
   :members:
   :show-inheritance:

.. automodule:: probirka._probes._redis
   :members:
   :show-inheritance:

.. automodule:: probirka._probes._http_policy
   :members:
   :show-inheritance:

.. automodule:: probirka._probes._http_base
   :members:
   :show-inheritance:

.. automodule:: probirka._probes._http_httpx
   :members:
   :show-inheritance:

.. automodule:: probirka._probes._http_httpx2
   :members:
   :show-inheritance:

.. automodule:: probirka._probes._http_aiohttp
   :members:
   :show-inheritance:

.. automodule:: probirka._probes._kafka_aiokafka
   :members:
   :show-inheritance:

.. automodule:: probirka._probes._rabbitmq_aiopika
   :members:
   :show-inheritance:

.. automodule:: probirka._probes._mongo_base
   :members:
   :show-inheritance:

.. automodule:: probirka._probes._mongo_pymongo
   :members:
   :show-inheritance:

.. automodule:: probirka._probes._mongo_motor
   :members:
   :show-inheritance:

Serving the result
------------------

Importable from the ``probirka`` package, e.g. ``from probirka import make_fastapi_endpoint``.

Generic ASGI app
~~~~~~~~~~~~~~~~

.. automodule:: probirka._ext.asgi
   :members: make_asgi_app
   :show-inheritance:

FastAPI
~~~~~~~

.. automodule:: probirka._ext.fastapi
   :members:
   :undoc-members:
   :show-inheritance:

AIOHTTP
~~~~~~~

.. automodule:: probirka._ext.aiohttp
   :members:
   :undoc-members:
   :show-inheritance:

Django
~~~~~~

.. automodule:: probirka._ext.django
   :members:
   :undoc-members:
   :show-inheritance:
