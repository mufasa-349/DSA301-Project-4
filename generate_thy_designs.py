#!/usr/bin/env python3
"""
Generate Part 2 static timetable figures for Turkish Airlines.
Outputs: images/thy-design-a.png, images/thy-design-b.png

Usage (recommended — avoids broken Python 3.14 venv on Homebrew):
    ./run_generate.sh

Or manually:
    python3.13 -m venv .venv313 && source .venv313/bin/activate
    pip install -r requirements.txt
    python generate_thy_designs.py
"""

from __future__ import annotations

import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless save to PNG
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np

OUT_DIR = Path(__file__).resolve().parent / "images"
OUT_DIR.mkdir(exist_ok=True)

# THY brand-adjacent palette
COLOR_INTL = "#1E5AA8"
COLOR_DOM = "#D4880F"
COLOR_HUB = "#C8102E"
COLOR_BG = "#F7F7F5"
COLOR_GRID = "#D8D8D4"

# (code, lat, lon) — approximate airport coordinates
CITIES = {
    "IST": (41.275, 28.752),
    "LHR": (51.470, -0.454),
    "FRA": (50.037, 8.562),
    "JFK": (40.641, -73.778),
    "DXB": (25.253, 55.364),
    "SIN": (1.364, 103.991),
    "ESB": (40.128, 32.995),
    "ADB": (38.292, 27.157),
    "AYT": (36.899, 30.801),
    "TZX": (40.995, 39.790),
    "GZT": (36.947, 37.479),
}

# Matches tables in project4.tex
ROUTES = [
    # label, dest, dep, arr, duration_min, freq_per_week, kind
    ("IST–LHR", "LHR", "08:15", "10:35", 200, 7, "intl"),
    ("IST–FRA", "FRA", "07:00", "09:15", 195, 7, "intl"),
    ("IST–JFK", "JFK", "13:30", "17:45", 675, 7, "intl"),
    ("IST–DXB", "DXB", "02:10", "07:25", 255, 14, "intl"),  # 2× daily
    ("IST–SIN", "SIN", "01:35", "17:20", 645, 7, "intl"),
    ("IST–ESB", "ESB", "06:00", "07:05", 65, 56, "dom"),   # 8× daily
    ("IST–ADB", "ADB", "07:30", "08:35", 65, 70, "dom"),
    ("IST–AYT", "AYT", "09:15", "10:25", 70, 84, "dom"),
    ("IST–TZX", "TZX", "11:00", "12:35", 95, 28, "dom"),
    ("IST–GZT", "GZT", "14:20", "16:05", 105, 21, "dom"),
]


def parse_time(t: str) -> float:
    h, m = t.split(":")
    return int(h) + int(m) / 60.0


def color_for(kind: str) -> str:
    return COLOR_INTL if kind == "intl" else COLOR_DOM


def linewidth_for(freq: int, kind: str) -> float:
    base = 1.2 if kind == "intl" else 1.0
    return base + min(freq, 84) / 28.0


def freq_label(freq: int) -> str:
    """freq = approximate weekly departures (daily × 7)."""
    per_day = max(1, round(freq / 7))
    if per_day == 1:
        return "Daily"
    return f"{per_day}×/day"


def project_map(lat: float, lon: float, lat0: float, lon0: float) -> tuple[float, float]:
    """Simple equirectangular projection centered near IST."""
    x = (lon - lon0) * math.cos(math.radians(lat0))
    y = lat - lat0
    return x, y


def great_circle_arc(lat1, lon1, lat2, lon2, n=60):
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    d = 2 * math.asin(
        math.sqrt(
            math.sin((lat2 - lat1) / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
        )
    )
    if d < 1e-9:
        return np.array([math.degrees(lat1)]), np.array([math.degrees(lon1)])
    fractions = np.linspace(0, 1, n)
    lats, lons = [], []
    for f in fractions:
        a = math.sin((1 - f) * d) / math.sin(d)
        b = math.sin(f * d) / math.sin(d)
        x = a * math.cos(lat1) * math.cos(lon1) + b * math.cos(lat2) * math.cos(lon2)
        y = a * math.cos(lat1) * math.sin(lon1) + b * math.cos(lat2) * math.sin(lon2)
        z = a * math.sin(lat1) + b * math.sin(lat2)
        lats.append(math.degrees(math.atan2(z, math.hypot(x, y))))
        lons.append(math.degrees(math.atan2(y, x)))
    return np.array(lats), np.array(lons)


def draw_design_a():
    dom_routes = [r for r in ROUTES if r[-1] == "dom"]
    intl_routes = [r for r in ROUTES if r[-1] == "intl"]
    ordered = dom_routes + intl_routes

    fig = plt.figure(figsize=(14, 10), facecolor=COLOR_BG)
    gs = fig.add_gridspec(2, 1, height_ratios=[1.15, 1], hspace=0.28)
    ax_map = fig.add_subplot(gs[0])
    ax_time = fig.add_subplot(gs[1])

    lat0, lon0 = CITIES["IST"]
    ax_map.set_facecolor("#EEF1F4")

    # faint graticule
    for lat in range(0, 55, 10):
        xs = [(lon - lon0) * math.cos(math.radians(lat0)) for lon in range(-80, 110, 5)]
        ys = [lat - lat0] * len(xs)
        ax_map.plot(xs, ys, color=COLOR_GRID, lw=0.4, zorder=0)
    for lon in range(-80, 110, 20):
        xs = [(lon - lon0) * math.cos(math.radians(lat0)) for _ in range(6)]
        ys = [la - lat0 for la in np.linspace(0, 52, 6)]
        ax_map.plot(xs, ys, color=COLOR_GRID, lw=0.4, zorder=0)

    for label, dest, dep_s, arr_s, _dur, freq, kind in ROUTES:
        lat1, lon1 = CITIES["IST"]
        lat2, lon2 = CITIES[dest]
        lats, lons = great_circle_arc(lat1, lon1, lat2, lon2)
        xs = [(lo - lon0) * math.cos(math.radians(lat0)) for lo in lons]
        ys = [la - lat0 for la in lats]
        ax_map.plot(
            xs, ys,
            color=color_for(kind),
            lw=linewidth_for(freq, kind),
            alpha=0.85,
            solid_capstyle="round",
            zorder=2,
        )

    # city nodes
    for code, (lat, lon) in CITIES.items():
        x, y = project_map(lat, lon, lat0, lon0)
        if code == "IST":
            ax_map.scatter(x, y, s=220, c=COLOR_HUB, edgecolors="white", lw=1.5, zorder=5)
            ax_map.text(x, y - 1.1, "IST", ha="center", fontsize=11, fontweight="bold", color=COLOR_HUB)
        else:
            ax_map.scatter(x, y, s=55, c="#333333", zorder=4)
            ax_map.text(x + 0.15, y + 0.12, code, fontsize=8, color="#333333")

    ax_map.set_title(
        "Design A — Hub map (map-based) · line weight ≈ weekly frequency",
        fontsize=13, fontweight="bold", pad=10,
    )
    ax_map.set_xticks([])
    ax_map.set_yticks([])
    for spine in ax_map.spines.values():
        spine.set_visible(False)

    legend_elems = [
        Line2D([0], [0], color=COLOR_DOM, lw=3, label="Domestic"),
        Line2D([0], [0], color=COLOR_INTL, lw=3, label="International"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=COLOR_HUB,
               markersize=10, label="IST hub"),
    ]
    ax_map.legend(handles=legend_elems, loc="lower left", framealpha=0.95)

    # --- timeline panel ---
    ax_time.set_facecolor("white")
    ax_time.set_xlim(0, 24)
    ax_time.set_ylim(-0.8, len(ordered) - 0.2)
    ax_time.set_xlabel("Local time (hours)", fontsize=11)
    ax_time.set_title(
        "Same-day departure window (time-based) · bars = dept → arr",
        fontsize=13, fontweight="bold", pad=8,
    )

    for hour in range(0, 25, 2):
        ax_time.axvline(hour, color=COLOR_GRID, lw=0.6, zorder=0)
    ax_time.axvspan(6, 11, color=COLOR_DOM, alpha=0.06, zorder=0)
    ax_time.text(8.5, len(ordered) - 0.05, "domestic cluster", ha="center",
                 fontsize=8, color=COLOR_DOM, alpha=0.8)

    for i, (label, _dest, dep_s, arr_s, dur, _freq, kind) in enumerate(ordered):
        dep = parse_time(dep_s)
        arr = parse_time(arr_s)
        col = color_for(kind)
        y = len(ordered) - 1 - i

        # overnight wrap marker (arr appears earlier on clock but same calendar day in table)
        if arr < dep and dur > 180:
            ax_time.barh(y, 24 - dep, left=dep, height=0.42, color=col, alpha=0.35, zorder=1)
            ax_time.barh(y, arr, left=0, height=0.42, color=col, alpha=0.35, zorder=1)
            ax_time.text(23.6, y, "†", fontsize=9, color=col, va="center")
        else:
            width = arr - dep if arr >= dep else (24 - dep) + arr
            ax_time.barh(y, width, left=dep, height=0.42, color=col, alpha=0.75, zorder=2)
            ax_time.plot([dep, arr], [y, y], "o", color="white", markeredgecolor=col,
                         markersize=6, zorder=3)

        ax_time.text(-0.35, y, label, ha="right", va="center", fontsize=9, fontweight="bold")
        ax_time.text(arr + 0.15 if arr + 0.15 < 24 else dep - 0.5, y,
                     f"{dep_s}–{arr_s}", fontsize=7, va="center", color="#444444")

    ax_time.set_yticks([])
    ax_time.set_xticks(list(range(0, 25, 2)))
    ax_time.set_xticklabels([f"{h:02d}:00" for h in range(0, 25, 2)], fontsize=8)
    ax_time.spines["top"].set_visible(False)
    ax_time.spines["right"].set_visible(False)

    fig.suptitle(
        "Turkish Airlines — Static Timetable · Design A",
        fontsize=15, fontweight="bold", y=0.98,
    )
    fig.text(0.5, 0.01, "Sample timetable data (IST hub) · verify at turkishairlines.com",
             ha="center", fontsize=8, color="#666666")

    out = OUT_DIR / "thy-design-a.png"
    fig.savefig(out, dpi=180, bbox_inches="tight", facecolor=COLOR_BG)
    plt.close(fig)
    print(f"Wrote {out}")


def draw_design_b():
    dom_routes = [r for r in ROUTES if r[-1] == "dom"]
    intl_routes = [r for r in ROUTES if r[-1] == "intl"]
    ordered = dom_routes + intl_routes

    fig = plt.figure(figsize=(14, 10), facecolor=COLOR_BG)
    gs = fig.add_gridspec(1, 2, width_ratios=[0.38, 0.62], wspace=0.12)
    ax_map = fig.add_subplot(gs[0])
    ax_sched = fig.add_subplot(gs[1])

    # --- left: route strip (schematic Turkey + spokes) ---
    ax_map.set_facecolor("#E8EDE8")
    ax_map.set_xlim(-0.5, 10.5)
    ax_map.set_ylim(-1, 11)

    # simplified Turkey blob
    turkey_x = np.array([2, 4, 6.5, 7.5, 6, 4.5, 3, 2])
    turkey_y = np.array([3, 2, 2.5, 5, 8, 9.5, 8.5, 3])
    ax_map.fill(turkey_x, turkey_y, color="#C5D4C0", ec="#8FA88A", lw=1, zorder=0)
    ax_map.text(4.5, 5.5, "Türkiye", ha="center", fontsize=9, color="#5A6B55", style="italic")

    # schematic positions (x east, y north) for strip layout
    strip_pos = {
        "IST": (4.5, 5.0),
        "ESB": (5.8, 6.2),
        "ADB": (3.2, 4.0),
        "AYT": (4.8, 3.0),
        "TZX": (7.2, 7.5),
        "GZT": (8.0, 4.5),
        "FRA": (1.0, 8.5),
        "LHR": (0.5, 9.2),
        "JFK": (0.2, 5.5),
        "DXB": (9.0, 2.5),
        "SIN": (9.5, 0.5),
    }

    ist = strip_pos["IST"]
    ax_map.scatter(*ist, s=200, c=COLOR_HUB, edgecolors="white", lw=1.5, zorder=5)
    ax_map.text(ist[0], ist[1] - 0.55, "IST", ha="center", fontweight="bold", color=COLOR_HUB)

    for label, dest, dep_s, arr_s, dur, freq, kind in ROUTES:
        end = strip_pos[dest]
        col = color_for(kind)
        lw = 1.5 + min(freq, 84) / 35
        # curved domestic / long-haul intl
        if kind == "dom":
            mx, my = (ist[0] + end[0]) / 2, (ist[1] + end[1]) / 2 + 0.3
            t = np.linspace(0, 1, 40)
            xs = (1 - t) ** 2 * ist[0] + 2 * (1 - t) * t * mx + t ** 2 * end[0]
            ys = (1 - t) ** 2 * ist[1] + 2 * (1 - t) * t * my + t ** 2 * end[1]
        else:
            t = np.linspace(0, 1, 40)
            mx = (ist[0] + end[0]) / 2 + (0.8 if end[0] > ist[0] else -0.8)
            my = (ist[1] + end[1]) / 2 + 1.2
            xs = (1 - t) ** 2 * ist[0] + 2 * (1 - t) * t * mx + t ** 2 * end[0]
            ys = (1 - t) ** 2 * ist[1] + 2 * (1 - t) * t * my + t ** 2 * end[1]

        ax_map.plot(xs, ys, color=col, lw=lw, alpha=0.8, zorder=2)
        ax_map.scatter(*end, s=40, c=col, zorder=3)
        ax_map.text(end[0] + 0.12, end[1] + 0.1, dest, fontsize=7, color=col)

    ax_map.set_title("Route strip (map-based)", fontsize=12, fontweight="bold")
    ax_map.set_xticks([])
    ax_map.set_yticks([])
    for spine in ax_map.spines.values():
        spine.set_visible(False)

    # --- right: per-route mini timelines ---
    ax_sched.set_facecolor("#EEEEEE")
    n = len(ordered)
    ax_sched.set_xlim(6, 24.5)
    ax_sched.set_ylim(-0.5, n - 0.5)
    ax_sched.set_title("Per-route mini schedule (time-based)", fontsize=12, fontweight="bold")
    ax_sched.set_xlabel("Local time", fontsize=10)

    t_min, t_max = 6.0, 24.0
    for i, (label, _dest, dep_s, arr_s, dur, freq, kind) in enumerate(ordered):
        dep = parse_time(dep_s)
        arr = parse_time(arr_s)
        col = color_for(kind)
        y = n - 1 - i

        if i % 2 == 0:
            ax_sched.axhspan(y - 0.45, y + 0.45, color="white", zorder=0)

        ax_sched.axhline(y, xmin=0, xmax=1, color=COLOR_GRID, lw=0.5, zorder=0)
        for tick in np.arange(6, 25, 3):
            ax_sched.axvline(tick, ymin=(y - 0.35) / n, ymax=(y + 0.35) / n,
                             color=COLOR_GRID, lw=0.35, zorder=0)

        # scale segment: map duration to horizontal span (min 0.8h, max 8h visible width)
        span = max(0.8, min(8.0, dur / 60.0 * 1.15))
        start = max(t_min, min(dep, 22.0))
        end_x = min(t_max, start + span)

        ax_sched.plot([start, end_x], [y, y], color=col, lw=5, solid_capstyle="round", zorder=2)
        ax_sched.scatter([start, end_x], [y, y], s=55, c=col, edgecolors="white", lw=1, zorder=3)
        ax_sched.text(start - 0.1, y + 0.32, dep_s, fontsize=7, ha="right", color=col)
        ax_sched.text(end_x + 0.1, y + 0.32, arr_s, fontsize=7, ha="left", color=col)

        ax_sched.text(5.85, y, label, ha="right", va="center", fontsize=9, fontweight="bold")
        # frequency ticks
        per_day = max(1, freq // 7)
        n_ticks = min(8, per_day)
        for k in range(n_ticks):
            ax_sched.plot(5.5 - k * 0.12, y - 0.28, "|", color=col, ms=6, mew=1.2)
        ax_sched.text(
            5.35, y - 0.28, freq_label(freq),
            fontsize=6, ha="right", va="top", color="#555555",
        )

    ax_sched.set_yticks([])
    ax_sched.set_xticks(list(range(6, 25, 3)))
    ax_sched.set_xticklabels([f"{h:02d}" for h in range(6, 25, 3)], fontsize=8)
    ax_sched.spines["top"].set_visible(False)
    ax_sched.spines["right"].set_visible(False)
    ax_sched.spines["left"].set_visible(False)

    fig.suptitle(
        "Turkish Airlines — Static Timetable · Design B",
        fontsize=15, fontweight="bold", y=0.98,
    )
    fig.text(0.5, 0.01, "Left: schematic geography · Right: one row per route (06:00–24:00)",
             ha="center", fontsize=8, color="#666666")

    out = OUT_DIR / "thy-design-b.png"
    fig.savefig(out, dpi=180, bbox_inches="tight", facecolor=COLOR_BG)
    plt.close(fig)
    print(f"Wrote {out}")


def main():
    draw_design_a()
    draw_design_b()
    print("Done. Recompile project4.tex to embed figures.")


if __name__ == "__main__":
    main()
