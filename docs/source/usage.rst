Usage
=====

Basic Example
-------------

.. code-block:: python

   import asyncio
   from dataclasses import asdict
   from pprint import pprint
   from probirka import Probirka

   # Create a Probirka instance
   probirka = Probirka()

   # Add custom information
   probirka.add_info("version", "1.0.0")
   probirka.add_info("environment", "production")

   # Define checks using decorators
   @probirka.add(name="database")  # This check will always run
   async def check_database():
       # Simulate database check
       await asyncio.sleep(1)
       return True

   @probirka.add(groups=["cache"])  # This check will only run when cache group is requested
   async def check_cache():
       # Simulate cache check
       await asyncio.sleep(1)
       return False  # Simulate failed check

   @probirka.add(groups=["external"])  # This check will only run when external group is requested
   def check_external_service():
       # Example of synchronous check
       return True

   async def main():
       print("-"*64)
       # Run only required checks (without groups)
       basic_results = await probirka.run()
       print("Basic check results:")
       print()
       pprint(asdict(basic_results))

       print("-"*64)
       # Run only cache group checks
       cache_results = await probirka.run(with_groups="cache", skip_required=True)
       print("Cache check results:")
       print()
       pprint(asdict(cache_results))

       print("-"*64)
       # Run required checks + several groups
       full_results = await probirka.run(with_groups=["cache", "external"])
       print("Full check results:")
       print()
       pprint(asdict(full_results))

   if __name__ == "__main__":
       asyncio.run(main())

Health Check Orchestrator
-------------------------

The `Probirka` class serves as the central hub for managing all health checks in your application. It provides a simple yet powerful API for:

1. Registering health checks
2. Adding global metadata
3. Executing checks with flexible configurations
4. Caching results for performance optimization

.. code-block:: python

   from probirka import Probirka

   # Create a Probirka instance with custom settings
   probirka = Probirka(
       success_ttl=60,  # Cache successful results for 60 seconds
       failed_ttl=10,   # Cache failed results for 10 seconds
   )

   # Add global application metadata
   probirka.add_info("version", "1.0.0")
   probirka.add_info("environment", "production")
   probirka.add_info("service_name", "user-api")

   # Run checks
   results = await probirka.run(
       with_groups=["cache"],  # Run specific groups
       skip_required=False,    # Include required checks
   )

Adding Probes
~~~~~~~~~~~~~

There are multiple ways to add probes to a Probirka instance:

1. Using the decorator pattern:

.. code-block:: python

   @probirka.add(name="database", groups=["core"])
   async def check_database():
       await asyncio.sleep(0.5)
       return True

2. Using the `add_probe` method with a function:

.. code-block:: python

   async def check_redis():
       # Redis check logic
       return True
       
   probirka.add_probe(name="redis", check=check_redis, groups=["cache"])

3. Using custom probe classes:

.. code-block:: python

   from probirka import ProbeBase
   
   class DatabaseProbe(ProbeBase):
       async def _check(self):
           # Database check logic
           return True
   
   # Add the probe instance
   probirka.add_probe(DatabaseProbe(name="database"))

Creating Custom Checks
----------------------

You can create custom checks by inheriting from the `ProbeBase` class:

.. code-block:: python

   from probirka import ProbeBase
   import asyncio

   class CustomProbe(ProbeBase):
       def __init__(self, name="CustomProbe"):
           super().__init__(name=name)
           
       async def _check(self):
           # Implement your check logic here
           return True

Adding Metadata to Checks
-------------------------

You can add metadata to your checks:

.. code-block:: python

   from probirka import ProbeBase
   import asyncio

   class DatabaseProbe(ProbeBase):
       async def _check(self):
           await asyncio.sleep(1)
           self.add_info("connection_pool_size", 10)
           self.add_info("active_connections", 5)
           return True

The added information will be included in the check results and can be accessed through the `info` field of each check result. This is useful for providing additional context about the state or performance metrics of the check.

Grouping Checks
---------------

Checks can be organized into required and optional groups. Checks without groups always run, while checks with groups only run when explicitly requested:

.. code-block:: python

   import asyncio
   from probirka import Probirka

   # Create a Probirka instance
   probirka = Probirka()

   # Required check (will always run)
   @probirka.add(name="database")
   async def check_database():
       await asyncio.sleep(1)
       return True

   # Optional checks (will only run when their groups are requested)
   @probirka.add(groups=["cache"])
   async def check_cache():
       await asyncio.sleep(1)
       return True

   @probirka.add(groups=["external"])
   async def check_external_service():
       return True

   async def main():
       # Run only required checks (database)
       basic_results = await probirka.run()
       print("Basic check results:", basic_results)

       # Run required checks + cache group
       cache_results = await probirka.run(with_groups=["cache"])
       print("Cache check results:", cache_results)

       # Run required checks + multiple groups
       full_results = await probirka.run(with_groups=["cache", "external"])
       print("Full check results:", full_results)

   if __name__ == "__main__":
       asyncio.run(main())

Setting Timeouts
----------------

You can set timeouts for individual checks:

.. code-block:: python

   from probirka import ProbeBase
   import asyncio

   class SlowProbe(ProbeBase):
       async def _check(self):
           await asyncio.sleep(2)  # This will cause a timeout
           return True

   probe = SlowProbe(timeout=1.0)  # 1 second timeout

Caching Results
---------------

.. code-block:: python

   from typing import Optional
   from probirka import Probirka, ProbeBase
   import asyncio

   # Create a Probirka instance with global caching settings
   probirka = Probirka(success_ttl=60, failed_ttl=10)  # Cache successful results for 60s, failed for 10s

   # Add a check with custom caching settings
   @probirka.add(success_ttl=300)  # Cache successful results for 5 minutes
   async def check_database():
       # Simulate database check
       await asyncio.sleep(1)
       return True

   # Or create a custom check with caching
   class DatabaseProbe(ProbeBase):
       def __init__(self, success_ttl: Optional[int] = None, failed_ttl: Optional[int] = None):
           super().__init__(success_ttl=success_ttl, failed_ttl=failed_ttl)
           
       async def _check(self) -> bool:
           # Simulate database check
           await asyncio.sleep(1)
           return True

The caching mechanism works as follows:
- If `success_ttl` is set, successful results will be cached for the specified number of seconds
- If `failed_ttl` is set, failed results will be cached for the specified number of seconds
- If both are set to `None` (default), no caching will be performed
- Global settings in the `Probirka` instance can be overridden by individual check settings
