#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
import random
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
MEDIA_DIR = ROOT / "docs" / "media"
SCREENSHOT_DIR = MEDIA_DIR / "screenshots"
GIF_DIR = MEDIA_DIR / "gif"
GIF_PATH = GIF_DIR / "product-demo.gif"

WIDTH = 1440
HEIGHT = 900
DEMO_WIDTH = 1280
DEMO_HEIGHT = 720


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = []
    if bold:
        candidates.extend(
            [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
            ]
        )
    else:
        candidates.extend(
            [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
            ]
        )
    for path in candidates:
        p = Path(path)
        if p.exists():
            return ImageFont.truetype(str(p), size=size)
    return ImageFont.load_default()


def gradient(size: tuple[int, int], c1: tuple[int, int, int], c2: tuple[int, int, int]) -> Image.Image:
    w, h = size
    img = Image.new("RGB", size, c1)
    draw = ImageDraw.Draw(img)
    for y in range(h):
        t = y / max(h - 1, 1)
        r = int(c1[0] + (c2[0] - c1[0]) * t)
        g = int(c1[1] + (c2[1] - c1[1]) * t)
        b = int(c1[2] + (c2[2] - c1[2]) * t)
        draw.line([(0, y), (w, y)], fill=(r, g, b))
    return img


def redact_text(raw: str) -> str:
    tokens = raw.split()
    redacted: list[str] = []
    for token in tokens:
        stripped = "".join(ch for ch in token if ch.isalnum())
        if not stripped:
            continue
        if len(stripped) == 1:
            redacted.append("*")
        else:
            redacted.append(stripped[0] + "*" * (len(stripped) - 1))
    if not redacted:
        return "Unknown"
    return " ".join(redacted)


def color_from_text(text: str) -> tuple[int, int, int]:
    digest = hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()
    r = 80 + int(digest[0:2], 16) % 130
    g = 90 + int(digest[2:4], 16) % 130
    b = 100 + int(digest[4:6], 16) % 130
    return r, g, b


def load_records(limit: int = 12) -> list[dict[str, object]]:
    cli_candidates = [
        [str(ROOT / "venv" / "bin" / "python"), "-m", "discogs_player.main", "list", "--limit", str(limit), "--json"],
        ["python3", "-m", "discogs_player.main", "list", "--limit", str(limit), "--json"],
    ]
    raw: list[dict[str, object]] = []
    for cmd in cli_candidates:
        try:
            proc = subprocess.run(cmd, cwd=ROOT, check=True, capture_output=True, text=True)
            parsed = json.loads(proc.stdout)
            if isinstance(parsed, list) and parsed:
                raw = parsed
                break
        except Exception:
            continue

    if not raw:
        fallback = [
            ("Atlantic Highway", "Night Drive", 2019),
            ("Signal Garden", "Soft Voltage", 2020),
            ("Neon Current", "Chrome Echo", 2021),
            ("Fjord Club", "Polar Groove", 2018),
            ("Tape Assembly", "Open Channel", 2017),
            ("Bright Parallax", "Signal Bloom", 2022),
            ("Mono Arcade", "City Shapes", 2016),
            ("Velvet Transit", "Late Station", 2015),
        ]
        random.shuffle(fallback)
        records = []
        for i, (artist, title, year) in enumerate(fallback, start=1):
            records.append(
                {
                    "artist": redact_text(artist),
                    "title": redact_text(title),
                    "year": year,
                    "discogs_release_id": 100000 + i,
                }
            )
        return records

    records = []
    for item in raw[:limit]:
        artist = str(item.get("artist") or "Unknown Artist")
        title = str(item.get("title") or "Unknown Title")
        year = int(item.get("year") or 0)
        records.append(
            {
                "artist": redact_text(artist),
                "title": redact_text(title),
                "year": year,
                "discogs_release_id": int(item.get("discogs_release_id") or random.randint(100000, 999999)),
            }
        )
    return records


def draw_shell(draw: ImageDraw.ImageDraw, active_tab: str) -> tuple[int, int, int, int]:
    outer = (24, 20, WIDTH - 24, HEIGHT - 20)
    draw.rounded_rectangle(outer, radius=26, fill=(14, 20, 33), outline=(59, 82, 106), width=2)

    header = (44, 40, WIDTH - 44, 122)
    draw.rounded_rectangle(header, radius=18, fill=(20, 31, 48))
    draw.text((66, 64), "Spinner for Discogs", font=font(32, bold=True), fill=(236, 247, 255))
    draw.text((360, 72), "Collect  •  Explore  •  External Playback", font=font(19), fill=(145, 194, 211))

    tabs = ["Browse", "Wantlist", "Market Value"]
    x = 66
    for tab in tabs:
        active = tab == active_tab
        tw = int(draw.textlength(tab, font=font(18, bold=True))) + 38
        fill = (49, 171, 165) if active else (28, 43, 64)
        text_fill = (6, 22, 26) if active else (174, 203, 220)
        draw.rounded_rectangle((x, 132, x + tw, 166), radius=14, fill=fill)
        draw.text((x + 19, 141), tab, font=font(17, bold=True), fill=text_fill)
        x += tw + 12

    sidebar = (44, 184, 306, HEIGHT - 42)
    draw.rounded_rectangle(sidebar, radius=16, fill=(18, 28, 45))
    draw.text((66, 206), "Collection", font=font(18, bold=True), fill=(208, 228, 245))
    draw.text((66, 236), "2,486 active releases", font=font(16), fill=(130, 168, 194))
    draw.text((66, 282), "Quick Actions", font=font(15, bold=True), fill=(171, 201, 218))

    actions = ["Sync Collection", "Spin", "Play --open", "Match Audit", "Value Refresh"]
    y = 312
    for action in actions:
        draw.rounded_rectangle((64, y, 286, y + 42), radius=12, fill=(31, 47, 71))
        draw.text((78, y + 11), action, font=font(15), fill=(218, 237, 249))
        y += 52

    return (326, 184, WIDTH - 44, HEIGHT - 42)


def draw_album_card(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], record: dict[str, object]) -> None:
    x1, y1, x2, y2 = box
    draw.rounded_rectangle(box, radius=14, fill=(23, 35, 54), outline=(60, 87, 111), width=1)
    art_color = color_from_text(str(record["title"]))
    draw.rounded_rectangle((x1 + 12, y1 + 12, x2 - 12, y1 + 126), radius=10, fill=art_color)

    draw.text((x1 + 14, y1 + 136), str(record["title"]), font=font(16, bold=True), fill=(235, 246, 255))
    draw.text((x1 + 14, y1 + 162), str(record["artist"]), font=font(14), fill=(150, 190, 214))
    year = int(record.get("year") or 0)
    year_text = str(year) if year > 0 else "Unknown"
    draw.text((x1 + 14, y1 + 186), f"Year {year_text}", font=font(13), fill=(118, 167, 191))


def screenshot_browse(records: list[dict[str, object]]) -> Image.Image:
    img = gradient((WIDTH, HEIGHT), (9, 23, 40), (7, 67, 74))
    draw = ImageDraw.Draw(img)
    main = draw_shell(draw, "Browse")
    x1, y1, x2, y2 = main

    draw.text((x1 + 12, y1 + 14), "Browse Gallery", font=font(24, bold=True), fill=(232, 245, 255))
    modes = [("Carousel", False), ("Text Menu", False), ("Gallery", True)]
    mx = x1 + 12
    for label, active in modes:
        w = int(draw.textlength(label, font=font(15, bold=True))) + 30
        fill = (68, 190, 178) if active else (34, 52, 75)
        txt = (12, 34, 38) if active else (173, 205, 225)
        draw.rounded_rectangle((mx, y1 + 50, mx + w, y1 + 82), radius=11, fill=fill)
        draw.text((mx + 14, y1 + 59), label, font=font(15, bold=True), fill=txt)
        mx += w + 8

    grid_x1 = x1 + 12
    grid_y1 = y1 + 100
    grid_x2 = x2 - 286
    grid_y2 = y2 - 12

    cols, rows = 3, 2
    card_w = (grid_x2 - grid_x1 - 16 * (cols - 1)) // cols
    card_h = (grid_y2 - grid_y1 - 16 * (rows - 1)) // rows

    idx = 0
    for r in range(rows):
        for c in range(cols):
            rx = grid_x1 + c * (card_w + 16)
            ry = grid_y1 + r * (card_h + 16)
            draw_album_card(draw, (rx, ry, rx + card_w, ry + card_h), records[idx % len(records)])
            idx += 1

    detail = (grid_x2 + 12, y1 + 100, x2 - 12, y2 - 12)
    draw.rounded_rectangle(detail, radius=16, fill=(21, 33, 52), outline=(60, 87, 111), width=1)
    selected = records[0]
    draw.text((detail[0] + 16, detail[1] + 18), "Selected Release", font=font(16, bold=True), fill=(177, 208, 225))
    draw.text((detail[0] + 16, detail[1] + 52), str(selected["title"]), font=font(20, bold=True), fill=(239, 250, 255))
    draw.text((detail[0] + 16, detail[1] + 84), str(selected["artist"]), font=font(16), fill=(155, 193, 214))
    draw.text((detail[0] + 16, detail[1] + 122), "Actions", font=font(14, bold=True), fill=(166, 197, 216))

    btns = ["Spin", "Play --open", "View Tracklist", "Match Album"]
    by = detail[1] + 146
    for btn in btns:
        draw.rounded_rectangle((detail[0] + 16, by, detail[2] - 16, by + 40), radius=12, fill=(39, 60, 87))
        draw.text((detail[0] + 30, by + 11), btn, font=font(15, bold=True), fill=(225, 241, 251))
        by += 52

    return img


def screenshot_wantlist(records: list[dict[str, object]]) -> Image.Image:
    img = gradient((WIDTH, HEIGHT), (11, 24, 47), (45, 69, 96))
    draw = ImageDraw.Draw(img)
    main = draw_shell(draw, "Wantlist")
    x1, y1, x2, y2 = main

    draw.text((x1 + 12, y1 + 14), "Wantlist Priorities", font=font(24, bold=True), fill=(235, 246, 255))
    draw.text((x1 + 12, y1 + 46), "Filter, compare, and queue desired releases", font=font(16), fill=(150, 191, 214))

    left = (x1 + 12, y1 + 86, x1 + 500, y2 - 12)
    right = (x1 + 522, y1 + 86, x2 - 12, y2 - 12)
    draw.rounded_rectangle(left, radius=14, fill=(20, 33, 51), outline=(60, 87, 111), width=1)
    draw.rounded_rectangle(right, radius=14, fill=(20, 33, 51), outline=(60, 87, 111), width=1)

    draw.text((left[0] + 14, left[1] + 14), "Watchlist", font=font(17, bold=True), fill=(205, 230, 243))
    ry = left[1] + 48
    for i, record in enumerate(records[:7]):
        tone = (33, 52, 76) if i % 2 == 0 else (28, 44, 67)
        if i == 1:
            tone = (67, 137, 128)
        draw.rounded_rectangle((left[0] + 12, ry, left[2] - 12, ry + 54), radius=10, fill=tone)
        draw.text((left[0] + 24, ry + 10), str(record["title"]), font=font(14, bold=True), fill=(235, 246, 255))
        draw.text((left[0] + 24, ry + 30), str(record["artist"]), font=font(13), fill=(170, 206, 225))
        price = 24 + ((int(record["discogs_release_id"]) % 60) / 10)
        draw.text((left[2] - 118, ry + 18), f"${price:.2f}", font=font(15, bold=True), fill=(230, 244, 201))
        ry += 62

    focus = records[1]
    draw.text((right[0] + 16, right[1] + 14), "Detail", font=font(17, bold=True), fill=(205, 230, 243))
    draw.text((right[0] + 16, right[1] + 46), str(focus["title"]), font=font(22, bold=True), fill=(242, 252, 255))
    draw.text((right[0] + 16, right[1] + 78), str(focus["artist"]), font=font(16), fill=(166, 198, 217))

    draw.text((right[0] + 16, right[1] + 126), "Signals", font=font(14, bold=True), fill=(163, 196, 216))
    metrics = ["Price confidence: High", "Last sold trend: Up", "Supply score: Tight"]
    my = right[1] + 152
    for metric in metrics:
        draw.rounded_rectangle((right[0] + 16, my, right[2] - 16, my + 36), radius=10, fill=(34, 52, 76))
        draw.text((right[0] + 28, my + 10), metric, font=font(14), fill=(224, 241, 251))
        my += 46

    draw.text((right[0] + 16, my + 4), "Actions", font=font(14, bold=True), fill=(163, 196, 216))
    my += 30
    for action in ["Open Listing", "Refresh Price", "Move To Queue"]:
        draw.rounded_rectangle((right[0] + 16, my, right[2] - 16, my + 40), radius=12, fill=(52, 110, 131))
        draw.text((right[0] + 30, my + 11), action, font=font(15, bold=True), fill=(236, 250, 255))
        my += 52

    return img


def screenshot_value(records: list[dict[str, object]]) -> Image.Image:
    img = gradient((WIDTH, HEIGHT), (17, 25, 45), (68, 55, 90))
    draw = ImageDraw.Draw(img)
    main = draw_shell(draw, "Market Value")
    x1, y1, x2, y2 = main

    draw.text((x1 + 12, y1 + 14), "Market Value Dashboard", font=font(24, bold=True), fill=(240, 248, 255))

    metrics = [
        ("Collection Value", "$26,482", "+4.7%"),
        ("Median Record", "$18.20", "+1.2%"),
        ("Tracked Movers", "112", "Today"),
    ]
    mx = x1 + 12
    for label, value, delta in metrics:
        card = (mx, y1 + 56, mx + 286, y1 + 158)
        draw.rounded_rectangle(card, radius=16, fill=(23, 35, 54), outline=(66, 92, 116), width=1)
        draw.text((mx + 16, y1 + 74), label, font=font(14, bold=True), fill=(169, 198, 218))
        draw.text((mx + 16, y1 + 102), value, font=font(30, bold=True), fill=(238, 249, 255))
        draw.text((mx + 206, y1 + 121), delta, font=font(14, bold=True), fill=(160, 236, 188))
        mx += 300

    chart = (x1 + 12, y1 + 178, x2 - 322, y2 - 12)
    draw.rounded_rectangle(chart, radius=16, fill=(21, 33, 52), outline=(66, 92, 116), width=1)
    draw.text((chart[0] + 16, chart[1] + 14), "30 Day Value Trend", font=font(16, bold=True), fill=(202, 226, 241))

    cx1, cy1, cx2, cy2 = chart[0] + 28, chart[1] + 52, chart[2] - 20, chart[3] - 20
    draw.rectangle((cx1, cy1, cx2, cy2), outline=(58, 81, 105), width=1)
    pts = []
    steps = 14
    for i in range(steps):
        x = cx1 + int((cx2 - cx1) * (i / (steps - 1)))
        y = cy2 - int((cy2 - cy1) * (0.30 + 0.16 * math.sin(i / 2.0) + i * 0.025))
        pts.append((x, y))
    draw.line(pts, fill=(95, 222, 213), width=4)
    for p in pts:
        draw.ellipse((p[0] - 4, p[1] - 4, p[0] + 4, p[1] + 4), fill=(220, 248, 255))

    movers = (x2 - 302, y1 + 56, x2 - 12, y2 - 12)
    draw.rounded_rectangle(movers, radius=16, fill=(21, 33, 52), outline=(66, 92, 116), width=1)
    draw.text((movers[0] + 16, movers[1] + 14), "Top Movers", font=font(16, bold=True), fill=(202, 226, 241))

    yy = movers[1] + 48
    for rec in records[:7]:
        draw.rounded_rectangle((movers[0] + 12, yy, movers[2] - 12, yy + 48), radius=10, fill=(35, 52, 75))
        draw.text((movers[0] + 20, yy + 9), str(rec["title"]), font=font(13, bold=True), fill=(235, 247, 255))
        delta = 2 + (int(rec["discogs_release_id"]) % 13)
        draw.text((movers[2] - 86, yy + 15), f"+{delta}%", font=font(14, bold=True), fill=(158, 236, 188))
        yy += 56

    return img


def screenshot_cli(records: list[dict[str, object]], browse: Image.Image) -> Image.Image:
    img = gradient((WIDTH, HEIGHT), (17, 27, 35), (25, 59, 85))
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle((24, 20, WIDTH - 24, HEIGHT - 20), radius=26, fill=(13, 21, 31), outline=(59, 82, 106), width=2)
    draw.text((50, 42), "CLI + GUI Handshake", font=font(30, bold=True), fill=(238, 247, 255))
    draw.text((50, 80), "Fast command flow with instant visual follow-through", font=font(17), fill=(154, 197, 218))

    terminal = (50, 130, 760, HEIGHT - 50)
    draw.rounded_rectangle(terminal, radius=16, fill=(8, 14, 20), outline=(70, 96, 120), width=1)
    draw.text((72, 150), "$ dplayer setup --json", font=font(18), fill=(103, 232, 167))
    draw.text((72, 184), "$ dplayer sync", font=font(18), fill=(103, 232, 167))
    draw.text((72, 218), "$ dplayer list --limit 5", font=font(18), fill=(103, 232, 167))
    draw.text((72, 252), "$ dplayer spin --json", font=font(18), fill=(103, 232, 167))
    draw.text((72, 286), "$ dplayer play --open", font=font(18), fill=(103, 232, 167))

    yy = 334
    for record in records[:5]:
        draw.text((72, yy), f"- {record['artist']} / {record['title']}", font=font(16), fill=(194, 218, 235))
        yy += 30

    preview = browse.resize((570, 660), Image.Resampling.LANCZOS)
    img.paste(preview, (810, 170))
    draw.rounded_rectangle((810, 170, 1380, 830), radius=16, outline=(98, 215, 205), width=3)
    draw.text((830, 188), "Live UI Follow-Up", font=font(18, bold=True), fill=(229, 248, 255))

    return img


def compose_scene(title: str, subtitle: str, screenshot: Image.Image, accent: tuple[int, int, int]) -> Image.Image:
    scene = gradient((DEMO_WIDTH, DEMO_HEIGHT), (10, 26, 43), (9, 64, 82))
    draw = ImageDraw.Draw(scene)

    draw.ellipse((930, -120, 1410, 360), fill=(accent[0], accent[1], accent[2], 60))
    draw.rounded_rectangle((34, 28, DEMO_WIDTH - 34, DEMO_HEIGHT - 28), radius=28, fill=(13, 22, 35), outline=(74, 101, 126), width=2)

    draw.text((68, 62), title, font=font(38, bold=True), fill=(239, 248, 255))
    draw.text((68, 110), subtitle, font=font(20), fill=(164, 201, 221))

    preview = screenshot.resize((1132, 520), Image.Resampling.LANCZOS)
    scene.paste(preview, (74, 156))
    draw.rounded_rectangle((74, 156, 1206, 676), radius=18, outline=(accent[0], accent[1], accent[2]), width=3)
    return scene


def compose_hero_scene(browse: Image.Image, wantlist: Image.Image, value: Image.Image) -> Image.Image:
    scene = gradient((DEMO_WIDTH, DEMO_HEIGHT), (9, 24, 40), (16, 74, 82))
    draw = ImageDraw.Draw(scene)
    draw.rounded_rectangle((34, 28, DEMO_WIDTH - 34, DEMO_HEIGHT - 28), radius=28, fill=(12, 22, 36), outline=(74, 101, 126), width=2)

    draw.text((72, 66), "Spinner for Discogs Product Tour", font=font(44, bold=True), fill=(241, 249, 255))
    draw.text((72, 122), "Browse, wantlist, value intel, and command-first speed", font=font(21), fill=(166, 206, 223))

    b = browse.resize((350, 214), Image.Resampling.LANCZOS)
    w = wantlist.resize((350, 214), Image.Resampling.LANCZOS)
    v = value.resize((350, 214), Image.Resampling.LANCZOS)
    scene.paste(b, (72, 210))
    scene.paste(w, (464, 210))
    scene.paste(v, (856, 210))

    for x in (72, 464, 856):
        draw.rounded_rectangle((x, 210, x + 350, 424), radius=14, outline=(87, 216, 203), width=2)

    draw.text((72, 468), "Discogs-first and local-first", font=font(26, bold=True), fill=(224, 243, 251))
    draw.text((72, 506), "Optional Spotify control in external apps (no in-app streaming)", font=font(18), fill=(157, 198, 219))
    draw.text((72, 552), "Ready to explore in under a minute", font=font(24, bold=True), fill=(142, 239, 194))
    return scene


def compose_outro_scene() -> Image.Image:
    scene = gradient((DEMO_WIDTH, DEMO_HEIGHT), (13, 23, 38), (36, 68, 92))
    draw = ImageDraw.Draw(scene)
    draw.rounded_rectangle((34, 28, DEMO_WIDTH - 34, DEMO_HEIGHT - 28), radius=28, fill=(12, 22, 34), outline=(74, 101, 126), width=2)

    draw.text((98, 196), "Spinner for Discogs", font=font(70, bold=True), fill=(241, 250, 255))
    draw.text((102, 286), "Sync your catalog. Surface value. Stay in flow.", font=font(34), fill=(171, 209, 228))
    draw.text((102, 356), "Start: dplayer setup -> dplayer sync -> dplayer spin", font=font(26, bold=True), fill=(147, 236, 192))
    draw.text((102, 412), "See README quick start and OS guides for full walkthroughs.", font=font(21), fill=(165, 203, 223))

    draw.rounded_rectangle((98, 510, 540, 578), radius=16, fill=(60, 185, 172))
    draw.text((130, 532), "Collection Explorer", font=font(26, bold=True), fill=(10, 34, 39))
    draw.rounded_rectangle((566, 510, 986, 578), radius=16, fill=(56, 96, 146))
    draw.text((600, 532), "Market Insight", font=font(26, bold=True), fill=(223, 239, 251))
    draw.rounded_rectangle((1012, 510, 1182, 578), radius=16, fill=(49, 132, 110))
    draw.text((1042, 532), "CLI", font=font(26, bold=True), fill=(225, 248, 237))

    return scene


def save_screenshot(img: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, format="PNG", optimize=True)


def make_demo_gif(scene_images: list[Image.Image], accents: list[tuple[int, int, int]]) -> None:
    frames: list[Image.Image] = []
    durations: list[int] = []

    for scene_index, scene in enumerate(scene_images):
        accent = accents[scene_index % len(accents)]
        scene_frames = 14
        for i in range(scene_frames):
            t = i / max(scene_frames - 1, 1)
            frame = scene.copy()
            draw = ImageDraw.Draw(frame)

            pulse = 28 + int(10 * math.sin(t * math.pi * 2))
            cx = 120 + int(t * (DEMO_WIDTH - 240))
            cy = 660
            draw.ellipse((cx - pulse, cy - pulse, cx + pulse, cy + pulse), outline=accent, width=2)

            draw.rounded_rectangle((72, 682, DEMO_WIDTH - 72, 698), radius=8, fill=(67, 91, 116))
            progress = 72 + int((DEMO_WIDTH - 144) * ((i + 1) / scene_frames))
            draw.rounded_rectangle((72, 682, progress, 698), radius=8, fill=accent)

            frames.append(frame)
            durations.append(95 if i < scene_frames - 1 else 240)

        if scene_index < len(scene_images) - 1:
            nxt = scene_images[scene_index + 1]
            for step in range(4):
                alpha = (step + 1) / 4.0
                blend = Image.blend(scene, nxt, alpha)
                frames.append(blend)
                durations.append(70)

    palette_frames = [frame.convert("P", palette=Image.ADAPTIVE, colors=128) for frame in frames]
    GIF_DIR.mkdir(parents=True, exist_ok=True)
    palette_frames[0].save(
        GIF_PATH,
        save_all=True,
        append_images=palette_frames[1:],
        duration=durations,
        loop=0,
        optimize=True,
        disposal=2,
    )


def main() -> None:
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    GIF_DIR.mkdir(parents=True, exist_ok=True)

    records = load_records(limit=12)
    browse = screenshot_browse(records)
    wantlist = screenshot_wantlist(records)
    value = screenshot_value(records)
    cli = screenshot_cli(records, browse)

    shots = [
        ("01-browse-gallery.png", browse),
        ("02-spin-result.png", wantlist),
        ("03-market-value-dashboard.png", value),
        ("04-wantlist-view.png", cli),
    ]
    for name, img in shots:
        save_screenshot(img, SCREENSHOT_DIR / name)

    hero = compose_hero_scene(browse, wantlist, value)
    scene_browse = compose_scene(
        "Browse Fast",
        "Switch modes and inspect details without losing momentum",
        browse,
        accent=(88, 214, 204),
    )
    scene_wantlist = compose_scene(
        "Prioritize Wantlist",
        "Rank targets, review signals, and queue next actions",
        wantlist,
        accent=(137, 202, 112),
    )
    scene_value = compose_scene(
        "Track Market Value",
        "Monitor value trendlines and top movers in one dashboard",
        value,
        accent=(242, 195, 110),
    )
    scene_cli = compose_scene(
        "Command-First Control",
        "Run setup, sync, spin, and play from the terminal",
        cli,
        accent=(116, 178, 245),
    )
    outro = compose_outro_scene()

    make_demo_gif(
        [hero, scene_browse, scene_wantlist, scene_value, scene_cli, outro],
        accents=[(88, 214, 204), (137, 202, 112), (242, 195, 110), (116, 178, 245)],
    )

    print("Generated media assets:")
    for path in sorted(SCREENSHOT_DIR.glob("*.png")):
        print(f"- {path.relative_to(ROOT)} ({path.stat().st_size / 1024:.1f} KB)")
    print(f"- {GIF_PATH.relative_to(ROOT)} ({GIF_PATH.stat().st_size / (1024 * 1024):.2f} MB)")


if __name__ == "__main__":
    main()
