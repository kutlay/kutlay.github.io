#!/usr/bin/env python3
"""
Datacenter Single Rack Visualization
Renders a single rack with hosts and VMs, minimal styling.
Run: python rack_simple.py
"""

import subprocess, sys, os

# ── COLORS ────────────────────────────────────────────────────────────────────
C = {
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
}

# ── DATA ──────────────────────────────────────────────────────────────────────
RACK = {
    "name": "RACK-01",
    "hosts": [
        {"name": "host-01", "online": True, "vms": ["web-1", "grafana"]},
    ],
}

# ── LAYOUT ────────────────────────────────────────────────────────────────────
RACK_W = 180
RACK_LABEL_H = 26
HOST_H = 24
VM_H = 16
VM_INDENT = 14
HOST_GAP = 5
HOST_MARGIN = 8
PADDING = 20


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
    return sum(host_block_h(h) + HOST_GAP for h in rack["hosts"]) - HOST_GAP + 16


def rack_total_h(rack):
    return RACK_LABEL_H + rack_inner_h(rack)


# ── DRAW RACK ─────────────────────────────────────────────────────────────────
def draw_rack(rack):
    lines = []
    rx = PADDING
    cy = PADDING

    rh = rack_total_h(rack)

    # Frame
    lines.append(rect(rx, cy, RACK_W, rh, C["rack_bg"], C["rack_border"], rx=4, sw=2))
    # Label bar
    lines.append(
        rect(
            rx,
            cy,
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
            cy + 17,
            rack["name"],
            C["rack_text"],
            size=11,
            anchor="middle",
            weight="bold",
        )
    )

    cy += RACK_LABEL_H + 8

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


# ── BUILD SVG ─────────────────────────────────────────────────────────────────
def build_svg():
    rh = rack_total_h(RACK)
    total_w = RACK_W + PADDING * 2
    total_h = rh + PADDING * 2

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total_w} {total_h}" '
        f'width="{total_w}" height="{total_h}" font-family="monospace">',
        draw_rack(RACK),
        "</svg>",
    ]
    return "\n".join(parts)


# ── MAIN ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    out = "rack_simple_out.svg"
    svg = build_svg()
    with open(out, "w") as f:
        f.write(svg)
    print(f"✓ Saved {out}")
