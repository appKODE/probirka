Ready-made Probes
=================

``probirka.probes`` ships probes for common infrastructure dependencies. Every one of them is a
plain :class:`probirka.ProbeBase` subclass, so it takes the usual ``name``, ``timeout``,
``success_ttl`` and ``failed_ttl`` arguments and is registered with ``add_probes``.

``probirka`` itself has no dependencies. Each probe needs its client library, which you install
separately; accessing a probe whose library is missing raises an ``ImportError`` naming the package:

.. code-block:: text

   ImportError: RedisProbe requires the 'redis' package, install it with: pip install redis

.. list-table::
   :header-rows: 1
   :widths: 24 20 56

   * - Probe
     - Requires
     - What it does
   * - ``TcpProbe``
     - nothing
     - Opens and closes a TCP connection to ``host:port``.
   * - ``PostgresAsyncpgProbe``
     - ``asyncpg``
     - Runs ``SELECT 1`` on a pool/connection or a fresh connection from ``dsn``.
   * - ``RedisProbe``
     - ``redis``
     - Sends ``PING`` with ``redis.asyncio``.
   * - ``HttpHttpxProbe``
     - ``httpx``
     - Sends a request and checks the status code.
   * - ``HttpHttpx2Probe``
     - ``httpx2``
     - Same, with `httpx2 <https://github.com/pydantic/httpx2>`_.
   * - ``HttpAiohttpProbe``
     - ``aiohttp``
     - Same, with ``aiohttp.ClientSession``.
   * - ``KafkaAiokafkaProbe``
     - ``aiokafka``
     - Fetches cluster metadata via a producer, consumer or admin client.
   * - ``RabbitmqAiopikaProbe``
     - ``aio-pika``
     - Opens and closes a channel.
   * - ``MongoPymongoProbe``
     - ``pymongo`` >= 4.9
     - Runs the ``ping`` command with ``pymongo.AsyncMongoClient``.
   * - ``MongoMotorProbe``
     - ``motor``
     - Runs the ``ping`` command with ``AsyncIOMotorClient``.

Client or connection string
---------------------------

Every probe that talks to a service accepts either an existing client of your application, or a
connection string (``dsn``, ``url``, ``bootstrap_servers``). Exactly one of them is required.

Passing the client reuses your pool and its configuration, and the probe never closes it:

.. code-block:: python

   import asyncpg
   from redis.asyncio import Redis
   from probirka import Probirka
   from probirka.probes import PostgresAsyncpgProbe, RedisProbe

   pool = await asyncpg.create_pool(dsn="postgresql://app@db/app")
   redis = Redis.from_url("redis://cache:6379/0")

   probirka = Probirka()
   probirka.add_probes(
       PostgresAsyncpgProbe(pool, name="postgres", timeout=2),
       RedisProbe(redis, name="redis", timeout=1),
   )

With a connection string the probe opens a short-lived connection on every check and closes it
afterwards. This is handy when the application has no client of its own for that service:

.. code-block:: python

   probirka.add_probes(
       PostgresAsyncpgProbe(dsn="postgresql://app@db/app", timeout=2),
       RedisProbe(url="redis://cache:6379/0", timeout=1),
       KafkaAiokafkaProbe(bootstrap_servers="kafka:9092", timeout=5),
       RabbitmqAiopikaProbe(url="amqp://guest:guest@rabbit/", timeout=2),
       MongoPymongoProbe(url="mongodb://mongo:27017", timeout=2),
   )

Late-bound clients
------------------

If the client is created after the probes are registered (a FastAPI lifespan, an aiohttp startup
signal), pass a zero-argument function instead of the client. It is called on every check:

.. code-block:: python

   probirka.add_probes(PostgresAsyncpgProbe(lambda: app.state.pool, name="postgres"))

Only functions, methods, lambdas and ``functools.partial`` objects are treated as factories; a client
object that happens to be callable is used as is.

HTTP probes
-----------

The HTTP probes take the URL as the first argument and compare the response status code with
``expected_status`` (``(200,)`` by default). ``method`` and ``headers`` are optional. Without a
``client`` a temporary one is created for each check:

.. code-block:: python

   import httpx
   from probirka.probes import HttpHttpxProbe

   probirka.add_probes(
       HttpHttpxProbe("https://api.example.com/health", name="api", timeout=3),
       HttpHttpxProbe(
           "https://auth.example.com/ping",
           method="HEAD",
           expected_status={200, 204},
           headers={"X-Token": "..."},
           client=httpx.AsyncClient(),
       ),
   )

TCP probe
---------

``TcpProbe`` only checks that a connection can be established. Its default name is ``TcpProbe``,
so give it a meaningful one when you add several:

.. code-block:: python

   from probirka.probes import TcpProbe

   probirka.add_probes(TcpProbe("smtp.example.com", 25, name="smtp", timeout=2))

How failures are reported
-------------------------

A probe fails in two ways, both ending up in :attr:`ProbeResult.error`:

* the client library raises: the error is ``'<ExceptionType>: <message>'``, e.g.
  ``'ConnectionRefusedError: [Errno 61] Connect call failed'``;
* the service answered but not in a healthy way: the probe raises
  :class:`probirka.probes.ProbeFailure`, e.g. ``'ProbeFailure: unexpected status 503'`` or
  ``'ProbeFailure: PING failed'``.

The probe ``timeout`` covers the whole check, including connecting when a connection string is used.
