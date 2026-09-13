Serving the health endpoint
===========================

Probirka computes the result; publishing it over HTTP is a separate step. There are three ways to
do it, and all of them return the same body and take the same options:

* a **generic ASGI application** — :func:`probirka.make_asgi_app`, registered as a route, mounted
  into any ASGI framework, or served on its own port;
* a **framework adapter** — one factory per framework, registered the way that framework registers
  routes;
* **your own handler** — three lines around :meth:`probirka.Probirka.run`, for everything else.

The adapters are thin wrappers over :meth:`probirka.Probirka.run`: they run the probes, map ``ok``
to a status code and return :meth:`probirka.ProbirkaResult.to_dict` as JSON. They are importable
from the ``probirka`` package and resolved on first access; the framework itself must be installed,
otherwise an ``ImportError`` names the package. :func:`probirka.make_asgi_app` is the exception —
it speaks the ASGI protocol directly and needs nothing but probirka.

Choosing an integration
-----------------------

.. list-table::
   :header-rows: 1
   :widths: 22 34 44

   * - Where it runs
     - Use
     - Notes
   * - FastAPI
     - ``make_fastapi_endpoint``
     - the ASGI app mounts into FastAPI too, but a mount stays out of ``/docs``
   * - Starlette
     - ``make_asgi_app`` as a ``Route``
     - nothing Starlette-specific to gain from a dedicated adapter
   * - Litestar
     - ``make_asgi_app`` via ``asgi(..., is_mount=True)``
     - Litestar answers the mount path itself, no redirect
   * - aiohttp
     - ``make_aiohttp_endpoint``
     - not an ASGI framework
   * - Django
     - ``make_django_view``
     - not mountable from ``urls.py``
   * - Falcon, BlackSheep, Esmerald
     - ``make_asgi_app``
     - anything that mounts an ASGI application
   * - Sanic, Quart, Flask
     - your own handler
     - these cannot mount an ASGI application; see `Without an adapter`_
   * - A port of its own
     - ``make_asgi_app`` under uvicorn
     - answers even while the main application is saturated

Common options
--------------

Every factory on this page takes the same keyword arguments:

.. list-table::
   :header-rows: 1
   :widths: 22 14 64

   * - Option
     - Default
     - Meaning
   * - ``timeout``
     - ``None``
     - Overall timeout of the run, in seconds. Probes that do not finish in time are reported as
       failed and the whole result gets ``ok=False``; nothing is raised.
   * - ``with_groups``
     - ``''``
     - Which optional groups to run, on top of the required probes.
   * - ``skip_required``
     - ``False``
     - Skip the probes registered without a group, running only ``with_groups``.
   * - ``return_results``
     - ``True``
     - Whether to send the result as the response body. ``False`` gives an empty body, which is
       enough for a liveness probe that only reads the status code.
   * - ``success_code``
     - ``200``
     - Status code when every probe passed.
   * - ``error_code``
     - ``500``
     - Status code when at least one probe failed or the run timed out.

Response format
---------------

The body is :meth:`probirka.ProbirkaResult.to_dict`, the same for every integration:

.. code-block:: json

   {
     "ok": true,
     "started_at": "2024-04-02T10:00:00.000123+03:00",
     "elapsed": 0.001,
     "info": null,
     "checks": [
       {
         "name": "api",
         "ok": true,
         "cached": null,
         "started_at": "2024-04-02T10:00:00.000123+03:00",
         "elapsed": 0.001,
         "info": null,
         "error": null,
         "allow_failure": false
       }
     ],
     "error": null
   }

``started_at`` is a timezone-aware ISO 8601 timestamp and ``elapsed`` is the duration in seconds.

Every integration renders the body the same way: ``json.dumps`` over
:meth:`ProbirkaResult.to_dict`, with values of ``info`` that are not JSON types written as their
``str()``. Secrets are masked on the way out — values under keys like ``password`` or ``api_key``
become ``'***'``, passwords inside URLs and sensitive query parameters are masked in every string,
``error`` included — and the adapters do not offer a way to turn that off. When you need the raw
data, run the probes from your own handler with ``to_dict(redact=False)``.

Generic ASGI app
----------------

:func:`probirka.make_asgi_app` returns a plain ASGI 3 application with no third-party
dependencies — the only integration that works on a bare ``pip install probirka``.

.. warning::

   A mounted application gets no help from the host router, so the app takes care of two things
   itself, and both are visible from the outside:

   * **The request path is ignored.** Whatever reaches the application is answered, so an app
     mounted at ``/health`` also answers ``/health/anything``.
   * **Only** ``GET`` **and** ``HEAD`` **are served.** Every other method gets ``405`` with an
     ``allow: GET, HEAD`` header. ``HEAD`` returns the status and headers of the matching ``GET``
     with an empty body.

Starlette
~~~~~~~~~

Register it as a route, so that the path is matched exactly:

.. code-block:: python

   from starlette.applications import Starlette
   from starlette.routing import Route
   from probirka import Probirka, make_asgi_app

   probirka_instance = Probirka()

   @probirka_instance.add(name="api")
   async def check_api():
       return True

   app = Starlette(
       routes=[
           Route("/health", make_asgi_app(probirka_instance), methods=["GET", "HEAD"]),
       ],
   )

.. warning::

   ``Mount("/health", app)`` works as well, but it answers on ``/health/`` and redirects the bare
   ``/health`` with a ``307``. A Kubernetes ``httpGet`` probe treats every status below 400 as
   success, so it would report the service healthy without the probes ever running. Use ``Route``,
   or point the probe at the trailing slash.

FastAPI
~~~~~~~

.. code-block:: python

   app.mount("/health", make_asgi_app(probirka_instance))

.. note::

   A mounted application is invisible to OpenAPI: it does not appear in ``/docs`` or in
   ``openapi.json``. Prefer :func:`probirka.make_fastapi_endpoint` when the route should be
   documented.

Litestar
~~~~~~~~

.. code-block:: python

   from litestar import Litestar, asgi
   from probirka import Probirka, make_asgi_app

   probirka_instance = Probirka()

   app = Litestar(
       route_handlers=[
           asgi("/health", is_mount=True)(make_asgi_app(probirka_instance)),
       ],
   )

On its own port
~~~~~~~~~~~~~~~

The application is a valid ASGI app by itself, so it can be served separately from the one it
watches — useful when the health port must not be exposed next to the public one, or when the
answer should arrive even while the main application is saturated:

.. code-block:: python

   # health.py
   from probirka import Probirka, make_asgi_app

   probirka_instance = Probirka()

   # add probes...

   health_app = make_asgi_app(probirka_instance)

.. code-block:: bash

   uvicorn health:health_app --port 8081

The lifespan protocol is acknowledged, so servers start it without warnings. The application keeps
no state of its own, so there is nothing to set up or tear down.

Native adapters
---------------

FastAPI
~~~~~~~

.. code-block:: python

   from fastapi import FastAPI
   from probirka import Probirka, make_fastapi_endpoint

   app = FastAPI()
   probirka_instance = Probirka()

   # Define health checks
   @probirka_instance.add(name="api")
   async def check_api():
       return True

   # Create and add the endpoint
   fastapi_endpoint = make_fastapi_endpoint(probirka_instance)
   app.add_api_route("/health", fastapi_endpoint)

   if __name__ == "__main__":
       import uvicorn
       uvicorn.run(app, host="0.0.0.0", port=8000)

A complete example with liveness, readiness and startup probes and an authenticated report is in
`Kubernetes probes`_ below.

aiohttp
~~~~~~~

.. code-block:: python

   from aiohttp import web
   from probirka import Probirka, make_aiohttp_endpoint

   app = web.Application()
   probirka_instance = Probirka()

   # Define health checks
   @probirka_instance.add(name="api")
   async def check_api():
       return True

   # Create and add the endpoint
   app.router.add_get("/health", make_aiohttp_endpoint(probirka_instance))

   if __name__ == "__main__":
       web.run_app(app, host="0.0.0.0", port=8000)

Django
~~~~~~

.. code-block:: python

   # urls.py
   from django.urls import path
   from probirka import Probirka, make_django_view

   probirka_instance = Probirka()

   # Define health checks
   @probirka_instance.add(name="api")
   async def check_api():
       return True

   urlpatterns = [
       path("health", make_django_view(probirka_instance)),
   ]

The view accepts ``GET`` and ``HEAD``; other HTTP methods get ``405 Method Not Allowed``.

.. _kubernetes-probes:

Kubernetes probes
-----------------

:func:`probirka.make_fastapi_endpoint` returns a plain endpoint function, so it is registered with
``add_api_route`` and takes everything that call accepts — a path, ``dependencies``, ``tags``,
``include_in_schema``. That is enough to serve the three probes of a pod and a report for operators
from one ``Probirka`` instance: probes registered without a group are the liveness check and run on
every endpoint, optional groups hold what each of the other endpoints adds.

.. code-block:: python

   import os
   import secrets
   from contextlib import asynccontextmanager
   from typing import Annotated

   import asyncpg
   from fastapi import Depends, FastAPI, HTTPException, status
   from fastapi.security import HTTPBasic, HTTPBasicCredentials
   from redis.asyncio import Redis

   from probirka import PostgresAsyncpgProbe, Probirka, RedisProbe, make_fastapi_endpoint

   HEALTH_USER = os.environ["HEALTH_USER"]
   HEALTH_PASSWORD = os.environ["HEALTH_PASSWORD"]


   @asynccontextmanager
   async def lifespan(app: FastAPI):
       app.state.pool = await asyncpg.create_pool(os.environ["DATABASE_DSN"])
       app.state.redis = Redis.from_url(os.environ["REDIS_URL"])
       yield
       await app.state.redis.aclose()
       await app.state.pool.close()


   app = FastAPI(lifespan=lifespan)

   probirka_instance = Probirka()
   probirka_instance.add_info("name", "orders-api")
   probirka_instance.add_info("version", "1.4.0")


   # Liveness: the process answers. Probes without a group run on every endpoint.
   @probirka_instance.add(name="self")
   async def check_self():
       return True


   # Readiness: the dependencies needed to serve traffic.
   probirka_instance.add_probes(
       PostgresAsyncpgProbe(lambda: app.state.pool, name="postgres", timeout=2),
       RedisProbe(lambda: app.state.redis, name="redis", timeout=1),
       groups="readiness",
   )


   # Startup: checks that must pass once and are too slow to repeat every few seconds.
   @probirka_instance.add(name="migrations", groups="startup", timeout=5)
   async def check_migrations():
       return await migrations_are_applied(app.state.pool)


   # Kubernetes reads only the status code, so send no body: nothing to leak.
   app.add_api_route("/livez", make_fastapi_endpoint(probirka_instance, return_results=False))
   app.add_api_route(
       "/readyz",
       make_fastapi_endpoint(probirka_instance, with_groups="readiness", return_results=False, error_code=503),
   )
   app.add_api_route(
       "/startupz",
       make_fastapi_endpoint(probirka_instance, with_groups="startup", return_results=False, error_code=503),
   )

   # The full report — every probe, error messages, metadata — is for operators, behind authentication.
   basic = HTTPBasic()


   def require_operator(credentials: Annotated[HTTPBasicCredentials, Depends(basic)]) -> None:
       user_ok = secrets.compare_digest(credentials.username.encode(), HEALTH_USER.encode())
       password_ok = secrets.compare_digest(credentials.password.encode(), HEALTH_PASSWORD.encode())
       if not (user_ok and password_ok):
           raise HTTPException(status.HTTP_401_UNAUTHORIZED, headers={"WWW-Authenticate": "Basic"})


   app.add_api_route(
       "/info",
       make_fastapi_endpoint(probirka_instance, with_groups=["readiness", "startup"]),
       dependencies=[Depends(require_operator)],
   )

* ``/livez`` runs only ``self``: it passes as long as the process serves requests. Dependencies
  stay out of it, because a liveness probe that fails when the database blips restarts the pod
  instead of fixing the database.
* ``/readyz`` adds the ``readiness`` group. While it fails the pod is removed from the Service
  endpoints and put back when it passes; nothing is restarted.
* ``/startupz`` adds the ``startup`` group. Kubernetes holds liveness and readiness back until it
  succeeds once and never calls it again — the place for checks that must pass once and are too slow
  to repeat every ten seconds. The server accepts no connections until the lifespan has finished, so
  the startup budget covers that time too. Without such checks, point the startup probe at
  ``/livez`` and skip the group.
* ``/info`` is the full report: every group, the ``error`` messages, the metadata from
  ``add_info()``. Route-level ``dependencies`` run before the endpoint, so an unauthenticated
  request runs no probe at all, and ``HTTPBasic`` puts an Authorize button on the route in
  ``/docs``. ``require_operator`` is an ordinary FastAPI dependency: replace it with the one your
  application already has — a JWT or OAuth2 scheme, a session cookie, ``Depends(get_current_admin)``.

The three Kubernetes endpoints send no body (``return_results=False``). The kubelet reads only the
status code, and an unauthenticated URL is the last place to show an ``error`` that may quote a
connection string — the masking described under `Response format`_ is a safety net for exactly
that, and with no body there is nothing to mask. Kubernetes counts every status from 200 to 399 as
success and anything else as failure, so ``error_code=503`` is not for it: it tells load balancers
and log filters that "not ready" is unavailability, not a crashed handler like the default ``500``.

The matching probe configuration. ``timeoutSeconds`` defaults to one second, so set it above the
slowest probe timeout or the kubelet gives up before Probirka answers; the startup budget covers the
lifespan and the migrations check:

.. code-block:: yaml

   livenessProbe:
     httpGet:
       path: /livez
       port: 8000
     periodSeconds: 10
   readinessProbe:
     httpGet:
       path: /readyz
       port: 8000
     periodSeconds: 10
     timeoutSeconds: 3
   startupProbe:
     httpGet:
       path: /startupz
       port: 8000
     periodSeconds: 5
     timeoutSeconds: 6
     failureThreshold: 24

Without an adapter
------------------

An adapter saves a handful of lines, it is not a requirement. Anything that can return a status
code and a body can serve the result — this is how to expose it from Sanic, Quart, Flask, or any
framework probirka does not ship an adapter for:

.. code-block:: python

   import json

   from probirka import Probirka

   probirka_instance = Probirka()

   async def health(request):
       res = await probirka_instance.run()
       return YourFrameworkResponse(
           json.dumps(res.to_dict(), default=str),
           status=200 if res.ok else 500,
           content_type="application/json",
       )

``default=str`` matters: ``info`` may hold values that are not JSON types, and without it
``json.dumps`` raises instead of answering. To mask the ``str()`` of such objects the way the
adapters do, pass ``default=lambda obj: probirka.redact_value(str(obj))`` instead.
