API Reference
=============

Core Classes
------------

.. automodule:: probirka._probes
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

Ready-made Probes
-----------------

All probes below are importable from the ``probirka`` package, e.g. ``from probirka import RedisProbe``.

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

Framework Adapters
------------------

Importable from the ``probirka`` package, e.g. ``from probirka import make_fastapi_endpoint``.

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
