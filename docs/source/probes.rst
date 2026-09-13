Ready-made Probes
=================

Probirka ships probes for common infrastructure dependencies, importable straight from the
``probirka`` package. Every one of them is a plain :class:`probirka.ProbeBase` subclass, so it takes
the usual ``name``, ``timeout``, ``success_ttl`` and ``failed_ttl`` arguments and is registered with
``add_probes``.

``probirka`` itself has no dependencies. Each probe needs its client library, which you install
separately; the probe is resolved on first access, and a missing library raises an ``ImportError``
naming the package:

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
   from probirka import PostgresAsyncpgProbe, RedisProbe

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
``expected_status`` (``(200,)`` by default; a single code is accepted too). ``method`` and
``headers`` are optional. Without a ``client`` a temporary one is created for each check, with the
probe ``timeout`` as its request timeout, so the client library's own default (5 s in httpx) never
cuts a check short. When you pass your own client, its timeout settings apply as well:

.. code-block:: python

   import httpx
   from probirka import HttpHttpxProbe

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

Security policy
~~~~~~~~~~~~~~~

An HTTP probe requests whatever URL it was configured with. When that URL comes from a config file
or an admin UI, or when the target answers with a redirect, the probe can be pointed at an internal
service or at a cloud metadata endpoint such as ``http://169.254.169.254/``, the classic
server-side request forgery. :class:`HttpProbePolicy` limits what the HTTP probes will contact:

.. code-block:: python

   from probirka import HttpHttpxProbe, HttpProbePolicy

   policy = HttpProbePolicy(
       allowed_hosts=("api.example.com", "*.example.com"),
       block_private_networks=True,
       allowed_networks=("10.20.0.0/16",),  # our own service mesh
       follow_redirects=True,
       max_redirects=3,
   )

   probirka.add_probes(HttpHttpxProbe("https://api.example.com/health", policy=policy, timeout=3))

The defaults are deliberately soft, because health checks usually target internal services: any
``http`` or ``https`` URL is accepted, no network is blocked, and redirects are not followed (a
``302`` is an ordinary status code compared with ``expected_status``). Everything stricter is
opt-in:

``allowed_schemes``
   ``("http", "https")`` by default; ``("https",)`` also refuses a redirect that downgrades to
   plain HTTP.
``allowed_hosts``
   Host names the probe may request, exactly or as ``*.example.com`` for any subdomain (not
   ``example.com`` itself). ``None``, the default, allows any host.
``block_private_networks``
   Refuses every address that is not globally routable: loopback, the RFC 1918 and ``fc00::/7``
   private ranges, link-local including ``169.254.169.254``, carrier-grade NAT, multicast,
   unspecified and reserved ranges.
``blocked_networks`` and ``allowed_networks``
   Your own CIDR lists. ``allowed_networks`` wins, so "no private networks except our mesh" is
   ``block_private_networks=True, allowed_networks=("10.20.0.0/16",)``.
``follow_redirects`` and ``max_redirects``
   See below.

The URL is checked when the probe is created; a refused URL is a :class:`ValueError`, so a
misconfiguration surfaces at startup rather than in the health output. Before every request the
URL is checked again, and when a network rule is set the host name is resolved first: the request
is refused if *any* resolved address is blocked, reported as
``'HttpProbePolicyViolation: internal.svc resolves to 10.0.0.5, which is not a global address'``.
:class:`HttpProbePolicyViolation` is a :class:`ProbeFailure`, so ``allow_failure`` applies as usual.

Redirects are never left to the client library. Every request is sent with automatic following
disabled, and with ``follow_redirects=True`` the probe follows ``301``, ``302``, ``303``, ``307``
and ``308`` itself: each target is checked against the policy before it is requested, ``POST``
becomes ``GET`` on ``301``, ``302`` and ``303`` as browsers do, and the request ``headers`` are
dropped when the target is another origin, so an ``Authorization`` header meant for your API never
reaches a third party. More than ``max_redirects`` hops is a failure. This is the same for httpx,
httpx2 and aiohttp, which means ``HttpAiohttpProbe`` no longer follows redirects unless asked to.

Limitations: the probe resolves the name and then the client library resolves it again, so a
resolver that answers differently the second time (DNS rebinding) can still reach a blocked
address; a proxy configured on your own client is not inspected. The policy narrows what a probe
does, it does not replace network-level controls.

TCP probe
---------

``TcpProbe`` only checks that a connection can be established. Its default name is ``TcpProbe``,
so give it a meaningful one when you add several:

.. code-block:: python

   from probirka import TcpProbe

   probirka.add_probes(TcpProbe("smtp.example.com", 25, name="smtp", timeout=2))

How failures are reported
-------------------------

A probe fails in two ways, both ending up in :attr:`ProbeResult.error`:

* the client library raises: the error is ``'<ExceptionType>: <message>'``, e.g.
  ``'ConnectionRefusedError: [Errno 61] Connect call failed'``;
* the service answered but not in a healthy way: the probe raises
  :class:`probirka.ProbeFailure`, e.g. ``'ProbeFailure: unexpected status 503'`` or
  ``'ProbeFailure: PING failed'``.

The probe ``timeout`` covers the whole check, including connecting when a connection string is used.

Secrets never make it into ``error``. Every ready-made probe registers the password of its
connection string (as written, URL-decoded, and as the ``Basic`` credentials httpx and aiohttp
derive from ``user:pass@`` in a URL) and the values of its request headers; wherever a client
library echoes them in an exception message, the result has ``'***'`` instead:

.. code-block:: text

   InvalidPasswordError: password authentication failed for user "app"
   ConnectError: http://app:***@svc/health rejected Basic ***

The user name, host, port and database are kept. A custom probe registers what it hands to a
client library with ``self._register_secrets(value, ...)`` in its ``__init__``. On top of that,
:meth:`ProbeResult.to_dict` masks passwords in URL-like strings and values under sensitive-looking
keys in ``info``; see :mod:`probirka._redact` for the details and ``to_dict(redact=False)`` to skip it.
