# Code Signing

Signing for macOS, Windows, and Debian distributions of Discogs Spinner.
Signing was optional for the pilot / `v0.2.0` line. For the `v1.0.0` bar, Windows
signing and macOS signing + notarization are release requirements (see
`docs/RELEASE_TARGET_v1.0.md`).

## How it's already wired

**`installer_build.yml` is already set up to sign — there is no workflow code to
uncomment or change.** Its "Configure optional code-signing env" step reads the
signing secrets and exports each one to `$GITHUB_ENV` *only when it is non-empty*.
When the secrets are unset, the vars stay truly absent and Tauri produces clean
**unsigned** bundles; when they're set, the macOS keychain-import step runs and
Tauri signs (and, for macOS, notarizes). So enabling signing is entirely a matter
of **adding the GitHub Actions secrets below and re-running a tagged build** —
`tauri.conf.json` can keep `signingIdentity: null` because CI drives it via env.

Add secrets under **Settings → Secrets and variables → Actions → New repository
secret**, then push a `v*` tag (or re-run `installer_build.yml`).

---

## macOS

**Requires:** Apple Developer Program membership (~$99/yr).

### Secrets (exact names consumed by CI)

| Secret | Value |
|---|---|
| `APPLE_CERTIFICATE` | base64 of the exported Developer ID Application `.p12` |
| `APPLE_CERTIFICATE_PASSWORD` | password set when exporting the `.p12` |
| `APPLE_SIGNING_IDENTITY` | the identity string, e.g. `Developer ID Application: Eric Donahue (XXXXXXXXXX)` |
| `APPLE_ID` | your Apple ID email |
| `APPLE_TEAM_ID` | 10-character team ID (developer.apple.com → Membership) |
| `APPLE_APP_SPECIFIC_PASSWORD` | app-specific password (appleid.apple.com → Sign-In & Security) |

### Steps

1. In Xcode → Settings → Accounts → Manage Certificates, create a **Developer ID
   Application** certificate.
2. In Keychain Access, find that certificate and **File → Export Items** as a
   password-protected `.p12`.
3. Get the exact identity string for `APPLE_SIGNING_IDENTITY`:
   ```bash
   security find-identity -v -p codesigning
   # → "Developer ID Application: Eric Donahue (XXXXXXXXXX)"
   ```
4. Base64-encode the `.p12` for `APPLE_CERTIFICATE`:
   ```bash
   base64 -i certificate.p12 | pbcopy   # macOS, copies to clipboard
   ```
5. Add all six secrets above. CI imports the cert into a temporary keychain and
   Tauri runs `xcrun notarytool submit` + `xcrun stapler staple` automatically.

### Verify a signed + notarized build

```bash
spctl --assess --type install --verbose=4 "/Applications/Discogs Spinner.app"   # → "accepted ... source=Notarized Developer ID"
codesign --verify --deep --strict --verbose=2 "/Applications/Discogs Spinner.app"
```

### Unsigned workaround (until signing is on)

```bash
xattr -dr com.apple.quarantine "/Applications/Discogs Spinner.app"
```

---

## Windows

### Choosing a certificate path

`installer_build.yml` consumes `WINDOWS_CERTIFICATE` (base64 `.pfx`) and
`WINDOWS_CERTIFICATE_PASSWORD`. The open question is *which kind of certificate* —
the trade-offs:

| Option | SmartScreen | Cost / yr | Notes |
|---|---|---|---|
| **Unsigned** (current) | "Unknown publisher" warning; user clicks **More info → Run anyway** | $0 | Fine for `0.x`; not the `1.0` default experience |
| **OV** (Organization Validation) | Warning persists until the binary builds download "reputation," then clears | ~$200–400 | Cheapest signed path; reputation can take weeks/many installs |
| **EV** (Extended Validation) | Cleared **immediately** (no reputation wait) | ~$250–500 + hardware token / HSM | Strongest trust; requires a FIPS token or cloud HSM, more identity vetting |
| **Azure Trusted Signing** | Cleared quickly (Microsoft-run) | ~$10/mo | Modern managed option; needs a verified Azure account + an eligible org/individual identity |

**Recommendation for this project:** since `1.0` is being approached gradually and
the cost/instant-trust trade-off is the deciding factor, the pragmatic order is
**Azure Trusted Signing** (cheapest path to fast SmartScreen trust if you can pass
its identity verification) → **EV** (if you want a classic cert and accept the
token) → **OV** (only if EV/Azure are unavailable; accept the reputation lag). Stay
**unsigned** for any pre-`1.0` build — just keep the SmartScreen "Run anyway"
workaround documented in the Windows quickstart. Revisit once a path is chosen;
this doc currently lays out options rather than committing to one.

### Secrets (once a `.pfx` is in hand)

| Secret | Value |
|---|---|
| `WINDOWS_CERTIFICATE` | base64 of the password-protected `.pfx` |
| `WINDOWS_CERTIFICATE_PASSWORD` | the `.pfx` password |

```bash
base64 -w0 certificate.pfx   # Linux; on macOS use `base64 -i certificate.pfx`
```

### Verify a signed installer

```powershell
Get-AuthenticodeSignature ".\Discogs.Spinner_x.y.z_x64-setup.exe" | Format-List
# Status should be "Valid"; or: signtool verify /pa /v <installer>.exe
```

> **Not the same as updater signing.** `TAURI_SIGNING_PRIVATE_KEY` /
> `TAURI_SIGNING_PRIVATE_KEY_PASSWORD` are the **minisign** keys Tauri's updater
> uses to sign `latest.json`/`.sig` artifacts — they are unrelated to Authenticode
> code signing and do **not** remove SmartScreen warnings.

---

## Debian / Linux

**Cost:** $0 — GPG signing only; an unsigned `.deb` installs fine and is not a
`1.0` blocker.

```bash
sudo apt install dpkg-sig
dpkg-sig --sign builder discogs-spinner-gtk4_<version>_amd64.deb
dpkg-sig --verify discogs-spinner-gtk4_<version>_amd64.deb
```

Distribute the public key so users can verify:

```bash
gpg --export --armor YOUR_KEY_ID > discogs-spinner-pubkey.asc
# user side:
sudo gpg --dearmor -o /usr/share/keyrings/discogs-spinner.gpg < discogs-spinner-pubkey.asc
```

---

## Status / next steps

- ✅ CI is wired to consume all signing secrets (`installer_build.yml`); unsigned
  by default, signed when secrets are present.
- ⬜ **macOS:** enroll in Apple Developer Program, add the six `APPLE_*` secrets,
  tag a build, verify with `spctl --assess`.
- ⬜ **Windows:** choose a certificate path (see matrix above), add the two
  `WINDOWS_CERTIFICATE*` secrets, verify with `Get-AuthenticodeSignature`.
- ⬜ Once signed builds ship, add a user-facing Gatekeeper/SmartScreen
  troubleshooting note to the OS quickstarts and flip the two signing gates in
  `docs/V1_READINESS_TRACKER.md` to done.
