Contributing
============

Contribution guidelines are maintained in:

- ``CONTRIBUTING.md``

Before submitting changes, run:

.. code-block:: bash

   venv/bin/ruff check .
   venv/bin/python -m mypy src/discogs_player --show-error-codes --hide-error-context
   venv/bin/python -m pytest -q

Use ``PRODUCT_STATE.md`` to align contributions with current priorities.
