discogs_player/
  README.md
  requirements.txt
  .env.example

  src/
    discogs_player/
      __init__.py
      main.py                 # CLI entrypoint (console_script `dplayer`)
      ui_main.py              # GTK entrypoint (later)

      core/
        models.py
        paths.py
        settings.py
        logging.py

      data/
        db.py
        repo.py

      services/
        discogs_client.py
        sync_manager.py
        image_cache.py
        matching.py

      integrations/
        player_backend.py
        null_backend.py
        spotify/
          backend.py
          spotify_client.py
          oauth.py

      use_cases/
        sync_collection.py
        list_releases.py
        spin_release.py
        ensure_mapping.py
        play_release.py
        device_management.py
        status_report.py

      cli/
        commands.py
        render.py

      ui/                     # later
        main_window.py
        widgets/
          cover_grid.py
          album_detail.py
          spin_wheel.py
          filters.py
          device_picker.py

  tests/
    test_matching.py
    test_repo_filters.py
    test_spin.py
