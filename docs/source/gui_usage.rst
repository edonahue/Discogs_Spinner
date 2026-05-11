GUI Usage
=========

The desktop UI is a thin interface over shared use-cases.

Main sections:

- Browse
- Wantlist
- Value
- Health

Browse and Wantlist modes:

- Carousel
- Text Menu
- Gallery

Browse includes collection summary context: LP count, 45 count, median value,
and the most recently added release when the data is available. Gallery mode is
scrollable and selecting a cover opens detail in the right-hand pane.

The Value tab is the market workspace. It includes top value releases, selected
release inspection, synced-release search, Hidden Gems, and value refresh
actions. There is no top-level Queue tab in the desktop UI; queue behavior is
kept inside the Value workspace and CLI workflows such as ``dplayer value
queue``.

Internal release handoffs should preserve context. A release selected in Browse
can be opened in the Value tab, and value/search results can return to the
matching collection or wantlist surface with that release focused.

Run GUI smoke test:

.. code-block:: bash

   xvfb-run -a python -m discogs_player.ui_main --smoke-test --limit 12

Run the layout-specific gallery smoke test:

.. code-block:: bash

   ./scripts/gallery_ux_smoke.sh 12

For full runtime behavior and controls, use ``README.md`` and
the latest validation note under ``docs/validation/``.
