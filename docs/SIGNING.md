# Code Signing Checklist

This document covers signing for macOS, Windows, and Debian distributions of Discogs Spinner.
Signing is optional for the pilot cohort; activate it when certs are in hand.

---

## macOS

**Requirement:** Apple Developer Program membership (~$99/yr at developer.apple.com)

### Certificates

1. Open Xcode → Settings → Accounts → Manage Certificates → create a "Developer ID Application" cert.
2. Export the `.p12` from Keychain Access (File → Export Items), set a strong password.
3. Base64-encode the file:
   ```bash
   base64 -i certificate.p12 | pbcopy
   ```
4. Add GitHub secrets (Settings → Secrets and variables → Actions):
   - `APPLE_CERTIFICATE_BASE64` — base64-encoded `.p12`
   - `APPLE_CERTIFICATE_PASSWORD` — password you set on export
   - `APPLE_ID` — your Apple ID email
   - `APPLE_TEAM_ID` — 10-character team ID (visible in developer.apple.com → Membership)
   - `APPLE_ID_PASSWORD` — app-specific password (appleid.apple.com → Sign-In & Security → App-Specific Passwords)

### Tauri configuration

In `desktop_shell/src-tauri/tauri.conf.json`, the `bundle.macOS` section should reference:

```json
"macOS": {
  "signingIdentity": "Developer ID Application: Your Name (TEAMID)",
  "notarizationCredentials": {
    "appleId": "your@apple.id",
    "appleIdPassword": { "appleIdPassword": "xxxx-xxxx-xxxx-xxxx" },
    "teamId": "XXXXXXXXXX"
  }
}
```

Tauri handles `xcrun notarytool submit` and `xcrun stapler staple` automatically when these values are set.

### CI integration

Uncomment the following env vars in the Tauri build step of `installer_build.yml`:

```yaml
env:
  APPLE_CERTIFICATE: ${{ secrets.APPLE_CERTIFICATE_BASE64 }}
  APPLE_CERTIFICATE_PASSWORD: ${{ secrets.APPLE_CERTIFICATE_PASSWORD }}
  APPLE_SIGNING_IDENTITY: "Developer ID Application: Your Name (TEAMID)"
  APPLE_ID: ${{ secrets.APPLE_ID }}
  APPLE_TEAM_ID: ${{ secrets.APPLE_TEAM_ID }}
  APPLE_ID_PASSWORD: ${{ secrets.APPLE_ID_PASSWORD }}
```

### Unsigned workaround for pilot users

Until signing is activated, macOS users can bypass Gatekeeper with:

```bash
xattr -dr com.apple.quarantine "/Applications/Discogs Spinner.app"
```

---

## Windows

### Option A: Unsigned (current — fine for pilot)

The NSIS installer produced by `cargo tauri build` works without a cert. Users will see a
SmartScreen "Unknown publisher" warning. They click **More info → Run anyway** to proceed.

### Option B: EV Code Signing Certificate (future)

EV certificates eliminate SmartScreen warnings and are required for Windows kernel drivers.

1. Obtain a certificate from DigiCert or Sectigo (~$300–500/yr for OV; EV requires extra identity verification).
2. Export as a password-protected `.pfx` file, then base64-encode:
   ```bash
   base64 -i certificate.pfx
   ```
3. Add GitHub secrets:
   - `TAURI_SIGNING_PRIVATE_KEY` — base64-encoded `.pfx`
   - `TAURI_SIGNING_PRIVATE_KEY_PASSWORD` — password

### CI integration (Windows)

Uncomment in `installer_build.yml`:

```yaml
env:
  TAURI_SIGNING_PRIVATE_KEY: ${{ secrets.TAURI_SIGNING_PRIVATE_KEY }}
  TAURI_SIGNING_PRIVATE_KEY_PASSWORD: ${{ secrets.TAURI_SIGNING_PRIVATE_KEY_PASSWORD }}
```

---

## Debian / Linux

**Cost:** $0 — GPG signing only.

### Sign a `.deb` with dpkg-sig

```bash
# Install dpkg-sig if needed
sudo apt install dpkg-sig

# Sign the package
dpkg-sig --sign builder discogs-spinner_0.2.0_amd64.deb

# Verify
dpkg-sig --verify discogs-spinner_0.2.0_amd64.deb
```

### Distribute your public key

Publish your GPG public key so users can verify:

```bash
gpg --export --armor YOUR_KEY_ID > discogs-spinner-pubkey.asc
```

Users add it:

```bash
sudo gpg --dearmor -o /usr/share/keyrings/discogs-spinner.gpg < discogs-spinner-pubkey.asc
```

### Unsigned `.deb` for pilot

An unsigned `.deb` installs fine via:

```bash
sudo dpkg -i discogs-spinner_0.2.0_amd64.deb
```

No blocker for the pilot cohort.

---

## Adding Secrets to GitHub

1. Navigate to the repository on GitHub.
2. Go to **Settings → Secrets and variables → Actions**.
3. Click **New repository secret** for each secret listed above.
4. After adding secrets, re-run the `installer_build.yml` workflow to produce signed artifacts.

---

## macOS Signing/Notarization TODOs

1. Define signing identity and certificate storage policy for CI.
2. Add a codesign step for macOS release artifacts in tagged-release workflow.
3. Add notarization submission + staple workflow and failure handling.
4. Publish user-facing Gatekeeper troubleshooting section once signed builds ship.
