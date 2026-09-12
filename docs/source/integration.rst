Framework Integration
=====================

The adapters live in ``probirka.ext`` and are thin wrappers over :meth:`probirka.Probirka.run`:
they run the probes, map ``ok`` to a status code and return :meth:`probirka.ProbirkaResult.to_dict`
as JSON. Import them from ``probirka.ext.<framework>``; the framework itself must be installed.
For backward compatibility the same functions are also available as
``probirka.make_fastapi_endpoint``, ``probirka.make_aiohttp_endpoint`` and
``probirka.make_django_view``.

FastAPI
-------

Here's an example of FastAPI integration:

.. code-block:: python

   from fastapi import FastAPI
   from probirka import Probirka
   from probirka.ext.fastapi import make_fastapi_endpoint

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

After running, you can get the check results by sending a GET request to `/health`. The response will be in JSON format:

.. code-block:: json

   {
     "ok": true,
     "started_at": "2024-04-02T10:00:00.000123",
     "elapsed": 0.001,
     "info": null,
     "checks": [
       {
         "name": "api",
         "ok": true,
         "cached": null,
         "started_at": "2024-04-02T10:00:00.000123",
         "elapsed": 0.001,
         "info": null,
         "error": null
       }
     ],
     "error": null
   }

``started_at`` is an ISO 8601 timestamp and ``elapsed`` is the duration in seconds. The body is
:meth:`probirka.ProbirkaResult.to_dict`, so every integration returns the same format.

aiohttp
-------

Here's an example of aiohttp integration:

.. code-block:: python

   from aiohttp import web
   from probirka import Probirka
   from probirka.ext.aiohttp import make_aiohttp_endpoint

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

After running, you can get the check results by sending a GET request to `/health`. The response will be in the same JSON format as for FastAPI.

Django
------

Here's an example of Django integration:

.. code-block:: python

   # urls.py
   from django.urls import path
   from probirka import Probirka
   from probirka.ext.django import make_django_view

   probirka_instance = Probirka()

   # Define health checks
   @probirka_instance.add(name="api")
   async def check_api():
       return True

   urlpatterns = [
       path("health", make_django_view(probirka_instance)),
   ]

After running, you can get the check results by sending a GET request to `/health`. The response will be in the same JSON format as for FastAPI.
Other HTTP methods get ``405 Method Not Allowed``.
