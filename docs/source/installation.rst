Installation
============

Probirka requires Python 3.11 or newer.

You can install Probirka using pip:

.. code-block:: bash

   pip install probirka

Using uv:

.. code-block:: bash

   uv pip install probirka

Or using poetry:

.. code-block:: bash

   poetry add probirka


Probirka has no dependencies of its own. The ready-made probes (:doc:`probes`) and the framework
adapters (:doc:`integration`) use client libraries that you install alongside, for example:

.. code-block:: bash

   pip install probirka redis asyncpg fastapi

If a library is missing, the corresponding name raises an ``ImportError`` that says which package
to install.
