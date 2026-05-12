#!/usr/bin/env python3
"""
Datacenter Host Selection View
Shows racks with hosts (no VMs), with selected hosts highlighted.
Run: python host_selection.py
"""

import subprocess, sys, os

# ── COLORS ────────────────────────────────────────────────────────────────────
C = {
    "bg": "#1a1a2e",
    "rack_bg": "#0f0f1a",
    "rack_border": "#444466",
    "rack_label": "#222244",
    "rack_text": "#aaaacc",
    "host_bg": "#2a2a5a",
    "host_border": "#5555aa",
    "host_text": "#8888cc",
    "host_off_bg": "#1a1a3a",
    "host_off_bdr": "#333355",
    "host_off_txt": "#444466",
    "host_selected_bg": "#3a5a2a",
    "host_selected_border": "#66aa55",
    "host_selected_text": "#88ff66",
    "led_on": "#44ff88",
    "led_off": "#333355",
    "led_selected": "#66ff99",
    "empty_text": "#2a2a44",
    "legend_text": "#666688",
}

# ── DATA ──────────────────────────────────────────────────────────────────────
# Each host: {"name": str, "online": bool, "selected": bool}

RACKS = [
    {
        "name": "RACK-01",
        "hosts": [
            {"name": "host-01", "online": True, "selected": False},
            {"name": "host-02", "online": True, "selected": True},
            {"name": "host-03", "online": True, "selected": True},
            {"name": "host-04", "online": True, "selected": False},
            {"name": "host-05", "online": True, "selected": False},
        ],
    },
    {
        "name": "RACK-02",
        "hosts": [
            {"name": "host-06", "online": True, "selected": False},
            {"name": "host-07", "online": True, "selected": True},
            {"name": "host-08", "online": True, "selected": True},
            {"name": "host-09", "online": True, "selected": False},
            {"name": "host-10", "online": True, "selected": False},
            {"name": "host-11", "online": True, "selected": True},
        ],
    },
    {
        "name": "RACK-03",
        "hosts": [
            {"name": "host-12", "online": True, "selected": False},
            {"name": "host-13", "online": True, "selected": True},
            {"name": "host-14", "online": True, "selected": False},
        ],
    },
]

# ── LAYOUT ────────────────────────────────────────────────────────────────────
RACK_W = 180
RACK_PADDING = 40
MARGIN = 50
RACK_TOP = 60
RACK_LABEL_H = 26

HOST_H = 32  # larger without VMs
HOST_GAP = 8
HOST_MARGIN = 8

TITLE = "DATACENTER — HOST SELECTION"


# ── SVG HELPERS ───────────────────────────────────────────────────────────────
def rect(x, y, w, h, fill, stroke, rx=2, sw=1, dash=""):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>'


def text(x, y, s, fill, size=9, anchor="start", weight="normal"):
    return f'<text x="{x}" y="{y}" text-anchor="{anchor}" fill="{fill}" font-size="{size}" font-weight="{weight}">{s}</text>'


# ── RACK HEIGHT CALCULATION ───────────────────────────────────────────────────
def rack_inner_h(rack):
    return len(rack["hosts"]) * HOST_H + (len(rack["hosts"]) - 1) * HOST_GAP + 16


def rack_total_h(rack):
    return RACK_LABEL_H + rack_inner_h(rack)


# ── DRAW RACK ─────────────────────────────────────────────────────────────────
def draw_rack(rack, rx, max_h):
    lines = []
    rh = max_h

    # Frame
    lines.append(
        rect(rx, RACK_TOP, RACK_W, rh, C["rack_bg"], C["rack_border"], rx=4, sw=2)
    )
    # Label bar
    lines.append(
        rect(
            rx,
            RACK_TOP,
            RACK_W,
            RACK_LABEL_H,
            C["rack_label"],
            C["rack_border"],
            rx=4,
            sw=0,
        )
    )
    lines.append(
        text(
            rx + RACK_W / 2,
            RACK_TOP + 17,
            rack["name"],
            C["rack_text"],
            size=11,
            anchor="middle",
            weight="bold",
        )
    )

    cy = RACK_TOP + RACK_LABEL_H + 8

    for host in rack["hosts"]:
        hx = rx + HOST_MARGIN
        hw = RACK_W - HOST_MARGIN * 2

        if host["online"]:
            if host["selected"]:
                # Selected host styling
                lines.append(
                    rect(
                        hx,
                        cy,
                        hw,
                        HOST_H,
                        C["host_selected_bg"],
                        C["host_selected_border"],
                    )
                )
                lines.append(
                    rect(hx + 4, cy + 8, 6, 16, C["led_selected"], "none", rx=1)
                )
                lines.append(
                    text(
                        hx + 16,
                        cy + 20,
                        host["name"],
                        C["host_selected_text"],
                        weight="bold",
                    )
                )
            else:
                # Normal online host
                lines.append(rect(hx, cy, hw, HOST_H, C["host_bg"], C["host_border"]))
                lines.append(rect(hx + 4, cy + 8, 6, 16, C["led_on"], "none", rx=1))
                lines.append(text(hx + 16, cy + 20, host["name"], C["host_text"]))
        else:
            # Offline host
            lines.append(
                rect(
                    hx, cy, hw, HOST_H, C["host_off_bg"], C["host_off_bdr"], dash="4,2"
                )
            )
            lines.append(rect(hx + 4, cy + 8, 6, 16, C["led_off"], "none", rx=1))
            lines.append(text(hx + 16, cy + 20, host["name"], C["host_off_txt"]))

        cy += HOST_H + HOST_GAP

    return "\n".join(lines)


# ── LEGEND ────────────────────────────────────────────────────────────────────
def draw_legend(total_w, legend_y):
    items = [
        (C["host_bg"], C["host_border"], "1", "host (online)"),
        (
            C["host_selected_bg"],
            C["host_selected_border"],
            "1",
            "host (selected for update)",
        ),
    ]
    lines = []
    lx = MARGIN
    for fill, stroke, sw, label in items:
        lines.append(rect(lx, legend_y, 14, 10, fill, stroke, sw=sw))
        lines.append(text(lx + 18, legend_y + 9, label, C["legend_text"], size=9))
        lx += 150
    return "\n".join(lines)


# ── BUILD SVG ─────────────────────────────────────────────────────────────────
def build_svg():
    max_rack_h = max(rack_total_h(r) for r in RACKS)
    total_w = MARGIN * 2 + len(RACKS) * RACK_W + (len(RACKS) - 1) * RACK_PADDING
    legend_y = RACK_TOP + max_rack_h + 20
    total_h = legend_y + 30

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total_w} {total_h}" '
        f'width="{total_w}" height="{total_h}" font-family="monospace">',
        rect(0, 0, total_w, total_h, C["bg"], "none", rx=12),
        text(total_w / 2, 38, TITLE, C["rack_border"], size=12, anchor="middle"),
    ]

    for i, rack in enumerate(RACKS):
        rx = MARGIN + i * (RACK_W + RACK_PADDING)
        parts.append(draw_rack(rack, rx, max_rack_h))

    parts.append(draw_legend(total_w, legend_y))
    parts.append("</svg>")
    return "\n".join(parts)


# ── MAIN ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    out = "host_selection_out.svg"
    svg = build_svg()
    with open(out, "w") as f:
        f.write(svg)
    print(f"✓ Saved {out}")
