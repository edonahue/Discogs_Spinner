GUI Usage
=========

The desktop UI is a thin interface over shared use-cases.

Main sections:

- Browse
- Wantlist
- Market Value

Browse and Wantlist modes:

- Carousel
- Text Menu
- Gallery

Run GUI smoke test:

.. code-block:: bash

   xvfb-run -a python -m discogs_player.ui_main --smoke-test --limit 12

For full runtime behavior and controls, use ``README.md`` and
``docs/TESTING_PERFORMED_2026-02-23.md``.
