#!/usr/bin/env bash
# capture_readme_media.sh — Capture real screenshots and GIF from the running GTK4 app
#
# Usage:
#   bash scripts/capture_readme_media.sh
#
# Output:
#   docs/media/screenshots/01-browse-gallery.png
#   docs/media/screenshots/02-spin-result.png
#   docs/media/screenshots/03-market-value-dashboard.png
#   docs/media/screenshots/04-wantlist-view.png
#   docs/media/gif/product-demo.gif
#
# Supports both X11 and Wayland (Pop!OS / COSMIC).
# Falls back to guided semi-automated mode if input simulation is unavailable.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SCREENSHOTS_DIR="$REPO_ROOT/docs/media/screenshots"
GIF_DIR="$REPO_ROOT/docs/media/gif"
TMP_DIR="$(mktemp -d)"
WINDOW_TITLE="Discogs Player"
WINDOW_W=1440
WINDOW_H=900

# ── Detect display server ────────────────────────────────────────────────────

detect_display_server() {
    if [[ "${WAYLAND_DISPLAY:-}" != "" ]]; then
        DISPLAY_SERVER="wayland"
    elif [[ "${DISPLAY:-}" != "" ]]; then
        DISPLAY_SERVER="x11"
    else
        echo "ERROR: No display server detected (WAYLAND_DISPLAY and DISPLAY are both unset)."
        echo "Run this script inside a graphical session."
        exit 1
    fi
    echo "Detected display server: $DISPLAY_SERVER"
}

# ── Dependency checks ────────────────────────────────────────────────────────

dep_check() {
    MISSING=()
    SEMI_AUTO=false

    if [[ "$DISPLAY_SERVER" == "wayland" ]]; then
        command -v grim    &>/dev/null || MISSING+=("grim (sudo apt install grim)")
        command -v slurp   &>/dev/null || true   # optional, used for region selection
        command -v wf-recorder &>/dev/null || true  # optional, for GIF recording
        if ! command -v ydotool &>/dev/null; then
            echo "WARN: ydotool not found — falling back to guided semi-automated mode."
            echo "      To enable full automation: sudo apt install ydotool && sudo systemctl enable --now ydotool"
            SEMI_AUTO=true
        fi
    else
        command -v scrot   &>/dev/null || MISSING+=("scrot (sudo apt install scrot)")
        command -v xdotool &>/dev/null || MISSING+=("xdotool (sudo apt install xdotool)")
        command -v byzanz-record &>/dev/null || true  # optional, for GIF recording
    fi

    command -v ffmpeg &>/dev/null || MISSING+=("ffmpeg (sudo apt install ffmpeg)")

    if [[ "${#MISSING[@]}" -gt 0 ]]; then
        echo "ERROR: Missing required tools:"
        for dep in "${MISSING[@]}"; do
            echo "  - $dep"
        done
        exit 1
    fi

    # Check for GIF optimizer (optional)
    command -v gifsicle &>/dev/null || echo "WARN: gifsicle not found — GIF will not be optimized. Install with: sudo apt install gifsicle"
}

# ── App launch ───────────────────────────────────────────────────────────────

launch_app() {
    echo "Launching dplayer-gui..."
    dplayer-gui &
    APP_PID=$!

    echo "Waiting for window to appear..."
    local waited=0
    while [[ $waited -lt 15 ]]; do
        if [[ "$DISPLAY_SERVER" == "x11" ]]; then
            WID=$(xdotool search --name "$WINDOW_TITLE" 2>/dev/null | head -1 || true)
            [[ -n "$WID" ]] && break
        else
            # On Wayland we can't query window IDs directly; just wait a fixed time
            sleep 3
            break
        fi
        sleep 1
        (( waited++ )) || true
    done

    if [[ "$DISPLAY_SERVER" == "x11" && -z "${WID:-}" ]]; then
        echo "ERROR: Window '$WINDOW_TITLE' did not appear within 15 seconds."
        kill "$APP_PID" 2>/dev/null || true
        exit 1
    fi

    echo "App launched (PID $APP_PID)."
}

# ── Window positioning ───────────────────────────────────────────────────────

position_window() {
    if [[ "$DISPLAY_SERVER" == "x11" && -n "${WID:-}" ]]; then
        echo "Positioning window to ${WINDOW_W}x${WINDOW_H}..."
        xdotool windowsize "$WID" "$WINDOW_W" "$WINDOW_H"
        xdotool windowmove "$WID" 0 0
        xdotool windowfocus "$WID"
        sleep 0.5
    else
        echo "NOTE: Resize the app window to ~${WINDOW_W}x${WINDOW_H} for consistent screenshots."
    fi
}

# ── Screenshot helpers ───────────────────────────────────────────────────────

take_screenshot() {
    local output_path="$1"
    if [[ "$DISPLAY_SERVER" == "wayland" ]]; then
        grim "$output_path"
    else
        if [[ -n "${WID:-}" ]]; then
            import -window "$WID" "$output_path" 2>/dev/null \
                || scrot --window "$WID" "$output_path" 2>/dev/null \
                || scrot "$output_path"
        else
            scrot "$output_path"
        fi
    fi
    echo "  Saved: $output_path"
}

click_button() {
    # Click at absolute screen coordinates. Used only when automation is available.
    local x="$1"
    local y="$2"
    if [[ "$DISPLAY_SERVER" == "wayland" ]]; then
        # Move mouse then click with ydotool
        ydotool mousemove --absolute -x "$x" -y "$y"
        ydotool click 0x1
    else
        xdotool mousemove "$x" "$y"
        xdotool click 1
    fi
    sleep 0.3
}

# ── GIF recording ────────────────────────────────────────────────────────────

start_recording() {
    RECORD_PID=""
    RECORD_FILE="$TMP_DIR/demo.mp4"

    if command -v wf-recorder &>/dev/null && [[ "$DISPLAY_SERVER" == "wayland" ]]; then
        echo "Starting screen recording with wf-recorder..."
        wf-recorder -f "$RECORD_FILE" &
        RECORD_PID=$!
    elif command -v byzanz-record &>/dev/null && [[ "$DISPLAY_SERVER" == "x11" ]]; then
        RECORD_FILE="$TMP_DIR/demo.gif"
        echo "Starting screen recording with byzanz-record..."
        if [[ -n "${WID:-}" ]]; then
            GEOM=$(xdotool getwindowgeometry --shell "$WID")
            eval "$GEOM"
            byzanz-record --duration=30 -x "$X" -y "$Y" -w "$WIDTH" -h "$HEIGHT" "$RECORD_FILE" &
        else
            byzanz-record --duration=30 "$RECORD_FILE" &
        fi
        RECORD_PID=$!
    else
        echo "WARN: No screen recorder found (wf-recorder / byzanz-record). GIF will be assembled from screenshots."
        RECORD_FILE=""
    fi
}

stop_recording() {
    if [[ -n "${RECORD_PID:-}" ]]; then
        echo "Stopping screen recording..."
        kill "$RECORD_PID" 2>/dev/null || true
        wait "$RECORD_PID" 2>/dev/null || true
    fi
}

# ── Navigation: automated vs. guided ────────────────────────────────────────

guided_wait() {
    local instruction="$1"
    echo ""
    echo "  >>> $instruction"
    echo "  Press ENTER when ready..."
    read -r
}

navigate_and_capture() {
    mkdir -p "$SCREENSHOTS_DIR"

    if [[ "$SEMI_AUTO" == "true" || "$DISPLAY_SERVER" == "wayland" ]]; then
        echo ""
        echo "=== Guided capture mode ==="
        echo "The app is running. Follow the prompts below to navigate, then press Enter."
        echo ""

        # Screenshot 1: Browse > Gallery
        guided_wait "Navigate to the Browse tab and select Gallery mode."
        sleep 1.5
        take_screenshot "$SCREENSHOTS_DIR/01-browse-gallery.png"

        # Screenshot 2: Spin result
        guided_wait "Click the Spin button and wait for the result to appear."
        sleep 2
        take_screenshot "$SCREENSHOTS_DIR/02-spin-result.png"

        # Screenshot 3: Market Value tab
        guided_wait "Navigate to the Market Value tab."
        sleep 1.5
        take_screenshot "$SCREENSHOTS_DIR/03-market-value-dashboard.png"

        # Screenshot 4: Wantlist > Gallery
        guided_wait "Navigate to the Wantlist tab and select Gallery mode."
        sleep 1.5
        take_screenshot "$SCREENSHOTS_DIR/04-wantlist-view.png"

    else
        # Automated X11 path via xdotool
        echo ""
        echo "=== Automated capture mode (X11 + xdotool) ==="
        echo "NOTE: Button coordinates below are approximate. Edit COORD_* variables in this"
        echo "      script to match your actual window layout if clicks miss their targets."
        echo ""

        # These coordinates are relative to a 1440×900 window at 0,0.
        # Adjust as needed after a first dry run.
        local TAB_BROWSE_X=120   TAB_BROWSE_Y=50
        local TAB_MARKET_X=360   TAB_MARKET_Y=50
        local TAB_WANTLIST_X=240 TAB_WANTLIST_Y=50
        local BTN_GALLERY_X=900  BTN_GALLERY_Y=50
        local BTN_SPIN_X=1340    BTN_SPIN_Y=50

        xdotool windowfocus "$WID"

        # Browse > Gallery
        echo "  Clicking Browse tab..."
        click_button "$TAB_BROWSE_X" "$TAB_BROWSE_Y"
        echo "  Clicking Gallery mode button..."
        click_button "$BTN_GALLERY_X" "$BTN_GALLERY_Y"
        sleep 1.5
        take_screenshot "$SCREENSHOTS_DIR/01-browse-gallery.png"

        # Spin result
        echo "  Clicking Spin button..."
        click_button "$BTN_SPIN_X" "$BTN_SPIN_Y"
        sleep 2
        take_screenshot "$SCREENSHOTS_DIR/02-spin-result.png"

        # Market Value tab
        echo "  Clicking Market Value tab..."
        click_button "$TAB_MARKET_X" "$TAB_MARKET_Y"
        sleep 1.5
        take_screenshot "$SCREENSHOTS_DIR/03-market-value-dashboard.png"

        # Wantlist > Gallery
        echo "  Clicking Wantlist tab..."
        click_button "$TAB_WANTLIST_X" "$TAB_WANTLIST_Y"
        echo "  Clicking Gallery mode button..."
        click_button "$BTN_GALLERY_X" "$BTN_GALLERY_Y"
        sleep 1.5
        take_screenshot "$SCREENSHOTS_DIR/04-wantlist-view.png"
    fi
}

# ── GIF assembly ─────────────────────────────────────────────────────────────

assemble_gif() {
    mkdir -p "$GIF_DIR"
    local output="$GIF_DIR/product-demo.gif"

    if [[ -n "${RECORD_FILE:-}" && -f "$RECORD_FILE" ]]; then
        echo "Assembling GIF from recording: $RECORD_FILE"

        if [[ "$RECORD_FILE" == *.gif ]]; then
            # byzanz produced a GIF directly
            cp "$RECORD_FILE" "$output"
        else
            # Convert MP4 to GIF via ffmpeg with palette
            local palette="$TMP_DIR/palette.png"
            ffmpeg -y -i "$RECORD_FILE" \
                -vf "fps=12,scale=1280:720:flags=lanczos,palettegen" \
                "$palette" 2>/dev/null
            ffmpeg -y -i "$RECORD_FILE" -i "$palette" \
                -vf "fps=12,scale=1280:720:flags=lanczos,paletteuse" \
                "$output" 2>/dev/null
        fi
    else
        echo "Assembling GIF from screenshots (fallback — no motion)..."
        # Use ffmpeg to create a slideshow GIF from the 4 screenshots
        ffmpeg -y \
            -framerate 1/3 \
            -i "$SCREENSHOTS_DIR/01-browse-gallery.png" \
            -framerate 1/3 \
            -i "$SCREENSHOTS_DIR/02-spin-result.png" \
            -framerate 1/3 \
            -i "$SCREENSHOTS_DIR/03-market-value-dashboard.png" \
            -framerate 1/3 \
            -i "$SCREENSHOTS_DIR/04-wantlist-view.png" \
            -filter_complex "
                [0:v]scale=1280:720:flags=lanczos,setsar=1[v0];
                [1:v]scale=1280:720:flags=lanczos,setsar=1[v1];
                [2:v]scale=1280:720:flags=lanczos,setsar=1[v2];
                [3:v]scale=1280:720:flags=lanczos,setsar=1[v3];
                [v0][v1][v2][v3]concat=n=4:v=1:a=0[out]
            " \
            -map "[out]" \
            -r 1/3 \
            "$TMP_DIR/slideshow.mp4" 2>/dev/null

        local palette="$TMP_DIR/palette.png"
        ffmpeg -y -i "$TMP_DIR/slideshow.mp4" \
            -vf "fps=1/3,palettegen" \
            "$palette" 2>/dev/null
        ffmpeg -y -i "$TMP_DIR/slideshow.mp4" -i "$palette" \
            -vf "fps=1/3,paletteuse" \
            "$output" 2>/dev/null
    fi

    # Optimize if gifsicle is available
    if command -v gifsicle &>/dev/null; then
        echo "Optimizing GIF with gifsicle..."
        gifsicle -O3 --colors 256 "$output" -o "$output" 2>/dev/null || true
    fi

    echo "  GIF saved: $output"
}

# ── Cleanup ───────────────────────────────────────────────────────────────────

close_app() {
    if [[ -n "${APP_PID:-}" ]]; then
        echo "Closing app (PID $APP_PID)..."
        kill "$APP_PID" 2>/dev/null || true
        wait "$APP_PID" 2>/dev/null || true
    fi
    rm -rf "$TMP_DIR"
}

# ── Report ────────────────────────────────────────────────────────────────────

report() {
    echo ""
    echo "=== Output files ==="
    for f in \
        "$SCREENSHOTS_DIR/01-browse-gallery.png" \
        "$SCREENSHOTS_DIR/02-spin-result.png" \
        "$SCREENSHOTS_DIR/03-market-value-dashboard.png" \
        "$SCREENSHOTS_DIR/04-wantlist-view.png" \
        "$GIF_DIR/product-demo.gif"; do
        if [[ -f "$f" ]]; then
            local size
            size=$(du -sh "$f" | cut -f1)
            echo "  $size  $f"
        else
            echo "  MISSING: $f"
        fi
    done
    echo ""
    echo "Done. Update README.md image references if filenames changed."
}

# ── Main ──────────────────────────────────────────────────────────────────────

trap close_app EXIT

detect_display_server
dep_check
launch_app
position_window
start_recording
navigate_and_capture
stop_recording
assemble_gif
report
