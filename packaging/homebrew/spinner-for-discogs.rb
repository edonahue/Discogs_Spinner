# Homebrew Cask formula for Spinner for Discogs
#
# BEFORE SUBMITTING a PR to homebrew/homebrew-cask:
# 1. Confirm macOS notarization is active (Gatekeeper must accept the .dmg without prompts).
# 2. Place this file at Casks/s/spinner-for-discogs.rb in your homebrew-cask fork.
# 3. Run locally: brew install --cask ./Casks/s/spinner-for-discogs.rb
# 4. Run: brew audit --cask --new spinner-for-discogs
#
cask "spinner-for-discogs" do
  version "0.2.3"

  on_arm do
    url "https://github.com/edonahue/Discogs_Spinner/releases/download/v#{version}/Discogs.Spinner_#{version}_aarch64.dmg",
        verified: "github.com/edonahue/Discogs_Spinner/"
    sha256 "73e9aa70874d28a8b8eed736ccf4143a238e5359d13eaae251993787f02301de"
  end

  on_intel do
    url "https://github.com/edonahue/Discogs_Spinner/releases/download/v#{version}/Discogs.Spinner_#{version}_x64.dmg",
        verified: "github.com/edonahue/Discogs_Spinner/"
    sha256 "74dd23f7c8a2f345f740c95684312357433280942088a8e6580bd028b4364817"
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
