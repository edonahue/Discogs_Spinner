# Friend Trial Checklist

Use this short checklist when someone is trying Spinner for Discogs cold for the first time.

## 10-Minute Validation Flow

1. Install the recommended artifact for the OS.
2. Launch the app and confirm it reaches setup (if token missing) or collection home.
3. Add Discogs token and confirm setup state advances.
4. Run first sync and wait for collection items to appear.
5. Trigger one spin action (UI or CLI) and confirm a release is selected.
6. Open value or hidden-gems surface and confirm data is visible (or clearly explained if empty).
7. Confirm optional provider messaging is understandable when Spotify is not connected.
8. Confirm no blank/ambiguous blocking state remains after setup + sync.

## Pass Criteria

- User can understand what the app is for in under 60 seconds.
- User can complete token setup + first sync without external help.
- User can browse and pick a record in one flow.
- User can identify at least one discovery signal (value, gems, health, or queue).

## Report If Any Fail

Capture:

- OS and version
- installer filename used
- exact warning/error text
- screenshot
- whether setup completed
- whether first sync completed

Issue templates:

- Install failure: <https://github.com/edonahue/spinner-for-discogs/issues/new?template=install_failure.yml>
- Auth/setup failure: <https://github.com/edonahue/spinner-for-discogs/issues/new?template=auth_failure.yml>
- Playback failure: <https://github.com/edonahue/spinner-for-discogs/issues/new?template=playback_failure.yml>

