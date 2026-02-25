Getting Started
===============

Platform target: Pop!_OS/Linux.

Install core system packages:

.. code-block:: bash

   sudo apt update
   sudo apt install -y \
     python3 python3-venv python3-pip python3-setuptools \
     libsecret-1-0 build-essential python3-dev

Create and activate environment:

.. code-block:: bash

   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   pip install -e .

Optional Spotify addon:

.. code-block:: bash

   pip install -e ".[spotify]"

Set Discogs token:

.. code-block:: bash

   export DISCOGS_TOKEN="your_discogs_personal_token"

First sync:

.. code-block:: bash

   dplayer sync
   dplayer status

For full setup details, use ``README.md``.
