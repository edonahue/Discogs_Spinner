.. Discogs Player documentation master file

Discogs Player Documentation
============================

A local Pop!_OS app that syncs your Discogs record collection into a local cache,
provides a CLI mode usable over SSH, and includes a desktop UI (GTK4/libadwaita).

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   getting_started
   cli_commands
   gui_usage
   architecture
   contributing
   product_state
   stabilization_backlog
   api_reference
   changelog

Quick Start
-----------

Install dependencies::

   sudo apt update
   sudo apt install -y \
     python3 python3-venv python3-pip python3-setuptools \
     libsecret-1-0 build-essential python3-dev

Set up the environment::

   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   pip install -e .

Optional Spotify addon::

   pip install -e ".[spotify]"

Configure your Discogs token::

   export DISCOGS_TOKEN="your_discogs_personal_token"

Sync your collection::

   dplayer sync

Browse your collection::

   dplayer list --limit 25

Spin for a random album::

   dplayer spin --genre Rock --year 1990:1999

Features
--------

- **Discogs Sync**: Incremental sync with soft-delete and image caching
- **CLI Mode**: Full functionality over SSH with JSON output
- **Spotify Addon (Optional)**: OAuth, device management, album playback
- **Desktop UI**: GTK4/libadwaita with cover grid and iPod-style text menu
- **Market Value Tracking**: Min/median/max prices with historical snapshots
- **Wantlist Support**: Full wantlist browsing with spin feature
- **Collection Analytics**: Year/genre/style distributions
- **Export/Import**: JSON backup with conflict resolution

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
