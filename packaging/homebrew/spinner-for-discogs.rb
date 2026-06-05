# Homebrew Cask formula for Spinner for Discogs
#
# BEFORE SUBMITTING a PR to homebrew/homebrew-cask:
# 1. Complete macOS notarization (Gatekeeper must accept the .dmg without prompts).
# 2. Replace the placeholder sha256 values below with the actual checksums:
#      shasum -a 256 Discogs.Spinner_0.2.0_aarch64.dmg
#      shasum -a 256 Discogs.Spinner_0.2.0_x64.dmg
# 3. Place this file at Casks/s/spinner-for-discogs.rb in your homebrew-cask fork.
# 4. Run: brew audit --cask --new spinner-for-discogs
#
cask "spinner-for-discogs" do
  version "0.2.0"

  on_arm do
    url "https://github.com/edonahue/Discogs_Spinner/releases/download/v#{version}/Discogs.Spinner_#{version}_aarch64.dmg",
        verified: "github.com/edonahue/Discogs_Spinner/"
    sha256 "PLACEHOLDER_SHA256_AARCH64_REPLACE_BEFORE_PR_SUBMISSION"
  end

  on_intel do
    url "https://github.com/edonahue/Discogs_Spinner/releases/download/v#{version}/Discogs.Spinner_#{version}_x64.dmg",
        verified: "github.com/edonahue/Discogs_Spinner/"
    sha256 "PLACEHOLDER_SHA256_X64_REPLACE_BEFORE_PR_SUBMISSION"
  end

  name "Spinner for Discogs"
  desc "Unofficial third-party Discogs collection browser and Spotify playback controller"
  homepage "https://github.com/edonahue/Discogs_Spinner"

  auto_updates true
  depends_on macos: ">= :ventura"

  app "Discogs Spinner.app"

  zap trash: [
    "~/Library/Application Support/com.discogs-spinner.app",
    "~/Library/Logs/com.discogs-spinner.app",
    "~/Library/Preferences/com.discogs-spinner.app.plist",
    "~/Library/Saved Application State/com.discogs-spinner.app.savedState",
  ]
end
