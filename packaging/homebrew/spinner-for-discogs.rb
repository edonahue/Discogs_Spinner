# Homebrew Cask formula for Spinner for Discogs
#
# BEFORE SUBMITTING a PR to homebrew/homebrew-cask:
# 1. Confirm macOS notarization is active (Gatekeeper must accept the .dmg without prompts).
# 2. Place this file at Casks/s/spinner-for-discogs.rb in your homebrew-cask fork.
# 3. Run locally: brew install --cask ./Casks/s/spinner-for-discogs.rb
# 4. Run: brew audit --cask --new spinner-for-discogs
#
cask "spinner-for-discogs" do
  version "0.2.2"

  on_arm do
    url "https://github.com/edonahue/Discogs_Spinner/releases/download/v#{version}/Discogs.Spinner_#{version}_aarch64.dmg",
        verified: "github.com/edonahue/Discogs_Spinner/"
    sha256 "122b8d29aee2bd5c3988239bcd1c7a42858a1fc2e061acf960086635c3e3a088"
  end

  on_intel do
    url "https://github.com/edonahue/Discogs_Spinner/releases/download/v#{version}/Discogs.Spinner_#{version}_x64.dmg",
        verified: "github.com/edonahue/Discogs_Spinner/"
    sha256 "a4ed2b0e08bf4ddeffcd14bdb68bc56e62fab58211c4d8f1d78a859567f3befa"
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
