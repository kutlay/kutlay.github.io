#!/usr/bin/env python3
"""
Datacenter SVG Generator
Configure racks, hosts, and VMs below, then run:  python datacenter.py
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
    "led_on": "#44ff88",
    "led_off": "#333355",
    "vm_bg": "#1a3a2a",
    "vm_border": "#338855",
    "vm_text": "#66cc88",
    "empty_text": "#2a2a44",
    "legend_text": "#666688",
}

# ── DATA ──────────────────────────────────────────────────────────────────────
# Each host: {"name": str, "online": bool, "vms": [str, ...]}
# vms list can be empty []

RACKS = [
    {
        "name": "RACK-01",
        "hosts": [
            {"name": "host-01", "online": True, "vms": ["web-1", "grafana"]},
            {"name": "host-02", "online": True, "vms": ["db-primary"]},
            {
                "name": "host-03",
                "online": True,
                "vms": ["cache-1"],
            },
            {"name": "host-04", "online": True, "vms": ["cache-2"]},
        ],
    },
    {
        "name": "RACK-02",
        "hosts": [
            {"name": "host-05", "online": True, "vms": ["web-2", "logs-1"]},
            {"name": "host-06", "online": True, "vms": ["cache-3"]},
            {"name": "host-07", "online": True, "vms": ["monitor", "logs-2"]},
            {"name": "host-08", "online": True, "vms": []},
        ],
    },
    {
        "name": "RACK-03",
        "hosts": [
            {"name": "host-9", "online": True, "vms": ["web-3", "build-2"]},
            {"name": "host-10", "online": True, "vms": []},
            {"name": "host-11", "online": True, "vms": ["db-replica-2"]},
        ],
    },
]

RACKS_2 = [
    {
        "name": "RACK-01",
        "hosts": [
            {"name": "host-01", "online": True, "vms": []},
            {"name": "host-02", "online": True, "vms": []},
            {"name": "host-03", "online": True, "vms": []},
            {"name": "host-04", "online": True, "vms": []},
            {"name": "host-05", "online": True, "vms": []},
        ],
    },
    {
        "name": "RACK-02",
        "hosts": [
            {"name": "host-06", "online": True, "vms": []},
            {"name": "host-07", "online": True, "vms": []},
            {"name": "host-08", "online": True, "vms": []},
            {"name": "host-09", "online": True, "vms": []},
            {"name": "host-10", "online": True, "vms": []},
            {"name": "host-11", "online": True, "vms": []},
        ],
    },
    {
        "name": "RACK-03",
        "hosts": [
            {"name": "host-12", "online": True, "vms": []},
            {"name": "host-13", "online": True, "vms": []},
            {"name": "host-14", "online": True, "vms": []},
        ],
    },
]

# ── LAYOUT ────────────────────────────────────────────────────────────────────
RACK_W = 180  # rack width
RACK_PADDING = 40  # gap between racks
MARGIN = 50  # outer margin
RACK_TOP = 60  # y offset for racks
RACK_LABEL_H = 26  # height of rack label bar

HOST_H = 24  # host row height (no VMs)
VM_H = 16  # height of each VM row
VM_INDENT = 14  # left indent for VMs inside host
HOST_GAP = 5  # vertical gap between hosts
HOST_MARGIN = 8  # left/right margin inside rack

TITLE = "DATACENTER — RACK VIEW"


# ── SVG HELPERS ───────────────────────────────────────────────────────────────
def rect(x, y, w, h, fill, stroke, rx=2, sw=1, dash=""):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>'


def text(x, y, s, fill, size=9, anchor="start", weight="normal"):
    return f'<text x="{x}" y="{y}" text-anchor="{anchor}" fill="{fill}" font-size="{size}" font-weight="{weight}">{s}</text>'


# ── RACK HEIGHT CALCULATION ───────────────────────────────────────────────────
def host_block_h(host):
    """Total height of one host block including its VMs."""
    vm_count = len(host["vms"]) if host["online"] else 0
    return HOST_H + vm_count * VM_H


def rack_inner_h(rack):
    return (
        sum(host_block_h(h) + HOST_GAP for h in rack["hosts"]) - HOST_GAP + 16
    )  # +16 bottom pad


def rack_total_h(rack):
    return RACK_LABEL_H + rack_inner_h(rack)


# ── DRAW RACK ─────────────────────────────────────────────────────────────────
def draw_rack(rack, rx, max_h):
    lines = []
    rh = max_h  # all racks same height

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

    cy = RACK_TOP + RACK_LABEL_H + 8  # current y inside rack

    for host in rack["hosts"]:
        hx = rx + HOST_MARGIN
        hw = RACK_W - HOST_MARGIN * 2
        vm_count = len(host["vms"]) if host["online"] else 0
        total_h = HOST_H + vm_count * VM_H

        if host["online"]:
            lines.append(rect(hx, cy, hw, total_h, C["host_bg"], C["host_border"]))
            # LED
            lines.append(rect(hx + 4, cy + 5, 6, 14, C["led_on"], "none", rx=1))
            # Host name
            lines.append(text(hx + 16, cy + 16, host["name"], C["host_text"]))

            # VMs
            for i, vm in enumerate(host["vms"]):
                vy = cy + HOST_H + i * VM_H
                lines.append(
                    rect(
                        hx + VM_INDENT,
                        vy,
                        hw - VM_INDENT - 2,
                        VM_H - 2,
                        C["vm_bg"],
                        C["vm_border"],
                    )
                )
                lines.append(
                    text(hx + VM_INDENT + 5, vy + 11, f"▸ {vm}", C["vm_text"], size=8)
                )
        else:
            lines.append(
                rect(
                    hx, cy, hw, HOST_H, C["host_off_bg"], C["host_off_bdr"], dash="4,2"
                )
            )
            lines.append(rect(hx + 4, cy + 5, 6, 14, C["led_off"], "none", rx=1))
            lines.append(text(hx + 16, cy + 16, host["name"], C["host_off_txt"]))

        cy += total_h + HOST_GAP

    return "\n".join(lines)


# ── LEGEND ────────────────────────────────────────────────────────────────────
def draw_legend(total_w, legend_y):
    items = [
        (C["host_bg"], C["host_border"], "1", "host (online)"),
        (C["host_off_bg"], C["host_off_bdr"], "1", "host (offline)"),
        (C["vm_bg"], C["vm_border"], "1", "virtual machine"),
    ]
    lines = []
    lx = MARGIN
    for fill, stroke, sw, label in items:
        lines.append(rect(lx, legend_y, 14, 10, fill, stroke, sw=sw))
        lines.append(text(lx + 18, legend_y + 9, label, C["legend_text"], size=9))
        lx += 130
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

    # parts.append(draw_legend(total_w, legend_y))
    parts.append("</svg>")
    return "\n".join(parts)


# ── MAIN ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    out = "datacenter_out.svg"
    svg = build_svg()
    with open(out, "w") as f:
        f.write(svg)
    print(f"✓ Saved {out}")
