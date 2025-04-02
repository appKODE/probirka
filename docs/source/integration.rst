Framework Integration
=====================

FastAPI
-------

Here's an example of FastAPI integration:

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
   app.add_route("/health", fastapi_endpoint)

   if __name__ == "__main__":
       import uvicorn
       uvicorn.run(app, host="0.0.0.0", port=8000)

After running, you can get the check results by sending a GET request to `/health`. The response will be in JSON format:

.. code-block:: json

   {
     "ok": true,
     "started_at": "2024-04-02T10:00:00",
     "elapsed": "0.001s",
     "info": null,
     "checks": [
       {
         "name": "api",
         "ok": true,
         "cached": null,
         "started_at": "2024-04-02T10:00:00",
         "elapsed": "0.001s",
         "info": null,
         "error": null
       }
     ]
   }

aiohttp
-------

Here's an example of aiohttp integration:

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

After running, you can get the check results by sending a GET request to `/health`. The response will be in the same JSON format as for FastAPI. 
