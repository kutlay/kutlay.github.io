#!/usr/bin/env python3
"""
Datacenter VM Movement Visualization
Shows VMs moving between hosts with animated arrows indicating movement paths.
Run: python vm_movement.py
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
    "vm_moving_bg": "#3a3a1a",
    "vm_moving_border": "#ffaa44",
    "vm_moving_text": "#ffdd66",
    "arrow": "#ff6644",
    "arrow_dash": "4,2",
    "empty_text": "#2a2a44",
    "legend_text": "#666688",
}

# ── DATA ──────────────────────────────────────────────────────────────────────
# Each host: {"name": str, "online": bool, "vms": [str, ...]}
RACKS = [
    {
        "name": "RACK-01",
        "hosts": [
            {"name": "host-01", "online": True, "vms": ["web-1", "grafana"]},
            {"name": "host-02", "online": True, "vms": ["db-primary"]},
            {"name": "host-03", "online": True, "vms": ["cache-1"]},
            {"name": "host-04", "online": False, "vms": []},
            {"name": "host-05", "online": True, "vms": ["api-1"]},
        ],
    },
    {
        "name": "RACK-02",
        "hosts": [
            {"name": "host-06", "online": True, "vms": ["web-2"]},
            {"name": "host-07", "online": True, "vms": ["cache-3"]},
            {"name": "host-08", "online": True, "vms": ["monitor"]},
            {
                "name": "host-09",
                "online": True,
                "vms": ["cache-1", "logs-1"],
            },  # receiving VMs
            {"name": "host-10", "online": True, "vms": ["proxy-1"]},
            {"name": "host-11", "online": True, "vms": ["db-replica-1"]},
        ],
    },
    {
        "name": "RACK-03",
        "hosts": [
            {"name": "host-12", "online": True, "vms": ["web-3", "build-2"]},
            {
                "name": "host-13",
                "online": True,
                "vms": ["logs-1", "logs-2"],
            },  # receiving VMs
            {"name": "host-14", "online": True, "vms": ["db-replica-2"]},
        ],
    },
]

# ── MOVEMENT DEFINITION ───────────────────────────────────────────────────────
# Movement format: {"vm": str, "from_host": str, "to_host": str, "from_idx": int, "to_idx": int}
MOVEMENTS = [
    {
        "vm": "cache-1",
        "from_host": "host-03",
        "to_host": "host-09",
        "from_idx": 0,
        "to_idx": 1,
    },
    {
        "vm": "logs-1",
        "from_host": "host-06",
        "to_host": "host-13",
        "from_idx": 1,
        "to_idx": 0,
    },
    {
        "vm": "logs-2",
        "from_host": "host-08",
        "to_host": "host-13",
        "from_idx": 1,
        "to_idx": 1,
    },
]

# ── LAYOUT ────────────────────────────────────────────────────────────────────
RACK_W = 180
RACK_PADDING = 40
MARGIN = 50
RACK_TOP = 80
RACK_LABEL_H = 26

HOST_H = 24
VM_H = 16
VM_INDENT = 14
HOST_GAP = 5
HOST_MARGIN = 8

TITLE = "DATACENTER — VM MOVEMENT"


# ── SVG HELPERS ───────────────────────────────────────────────────────────────
def rect(x, y, w, h, fill, stroke, rx=2, sw=1, dash=""):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>'


def text(x, y, s, fill, size=9, anchor="start", weight="normal"):
    return f'<text x="{x}" y="{y}" text-anchor="{anchor}" fill="{fill}" font-size="{size}" font-weight="{weight}">{s}</text>'


def line(x1, y1, x2, y2, stroke, sw=1.5, dash=""):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="{sw}"{d}/>'


def arrow_head(x, y, angle, size=8):
    """Generate arrow head polygon at (x,y) pointing in direction angle (degrees)"""
    import math

    rad = math.radians(angle)

    # Arrow head points
    p1x = x - size * math.cos(rad)
    p1y = y - size * math.sin(rad)

    p2x = p1x - size * 0.5 * math.cos(rad - math.radians(150))
    p2y = p1y - size * 0.5 * math.sin(rad - math.radians(150))

    p3x = p1x - size * 0.5 * math.cos(rad + math.radians(150))
    p3y = p1y - size * 0.5 * math.sin(rad + math.radians(150))

    points = f"{x},{y} {p2x},{p2y} {p3x},{p3y}"
    return f'<polygon points="{points}" fill="{C["arrow"]}"/>'


# ── RACK HEIGHT CALCULATION ───────────────────────────────────────────────────
def host_block_h(host):
    """Total height of one host block including its VMs."""
    vm_count = len(host["vms"]) if host["online"] else 0
    return HOST_H + vm_count * VM_H


def rack_inner_h(rack):
    return sum(host_block_h(h) + HOST_GAP for h in rack["hosts"]) - HOST_GAP + 16


def rack_total_h(rack):
    return RACK_LABEL_H + rack_inner_h(rack)


# ── HOST POSITION TRACKING ────────────────────────────────────────────────────
class HostPositions:
    def __init__(self):
        self.positions = {}  # {host_name: {"x": rx, "y": cy, "h": height}}

    def set_position(self, host_name, x, y, h):
        self.positions[host_name] = {"x": x, "y": y, "h": h}

    def get_vm_center(self, host_name, vm_index):
        """Get center position of a VM within a host"""
        if host_name not in self.positions:
            return None
        pos = self.positions[host_name]
        vm_y = pos["y"] + HOST_H + vm_index * VM_H + VM_H / 2
        vm_x = pos["x"] + 90  # middle of host
        return (vm_x, vm_y)


# ── DRAW RACK ─────────────────────────────────────────────────────────────────
def draw_rack(rack, rx, max_h, host_positions, moving_vms=None):
    """Draw a rack and track host positions."""
    if moving_vms is None:
        moving_vms = {}

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
        vm_count = len(host["vms"]) if host["online"] else 0
        total_h = HOST_H + vm_count * VM_H

        # Track this host's position
        host_positions.set_position(host["name"], hx, cy, total_h)

        if host["online"]:
            lines.append(rect(hx, cy, hw, total_h, C["host_bg"], C["host_border"]))
            # LED
            lines.append(rect(hx + 4, cy + 5, 6, 14, C["led_on"], "none", rx=1))
            # Host name
            lines.append(text(hx + 16, cy + 16, host["name"], C["host_text"]))

            # VMs
            for i, vm in enumerate(host["vms"]):
                vy = cy + HOST_H + i * VM_H

                # Check if this VM is moving
                is_moving = vm in moving_vms
                if is_moving:
                    fill = C["vm_moving_bg"]
                    stroke = C["vm_moving_border"]
                    text_color = C["vm_moving_text"]
                else:
                    fill = C["vm_bg"]
                    stroke = C["vm_border"]
                    text_color = C["vm_text"]

                lines.append(
                    rect(
                        hx + VM_INDENT,
                        vy,
                        hw - VM_INDENT - 2,
                        VM_H - 2,
                        fill,
                        stroke,
                    )
                )
                lines.append(
                    text(hx + VM_INDENT + 5, vy + 11, f"▸ {vm}", text_color, size=8)
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


# ── DRAW MOVEMENT ARROWS ──────────────────────────────────────────────────────
def draw_movement_arrows(movements, host_positions):
    """Draw arrows between hosts showing VM movement."""
    lines = []

    for movement in movements:
        from_host = movement["from_host"]
        to_host = movement["to_host"]
        vm_name = movement["vm"]
        from_idx = movement["from_idx"]
        to_idx = movement["to_idx"]

        # Get positions
        from_pos = host_positions.get_vm_center(from_host, from_idx)
        to_pos = host_positions.get_vm_center(to_host, to_idx)

        if from_pos and to_pos:
            x1, y1 = from_pos
            x2, y2 = to_pos

            # Draw curved path with dashed line
            mid_x = (x1 + x2) / 2
            mid_y = min(y1, y2) - 30  # Curve above

            # Simplified quadratic bezier using line segments
            curve_points = []
            for t in [i / 20.0 for i in range(21)]:
                # Quadratic bezier: B(t) = (1-t)²P0 + 2(1-t)tP1 + t²P2
                bx = (1 - t) ** 2 * x1 + 2 * (1 - t) * t * mid_x + t**2 * x2
                by = (1 - t) ** 2 * y1 + 2 * (1 - t) * t * mid_y + t**2 * y2
                curve_points.append((bx, by))

            # Draw curve as polyline
            for i in range(len(curve_points) - 1):
                x1c, y1c = curve_points[i]
                x2c, y2c = curve_points[i + 1]
                lines.append(
                    line(x1c, y1c, x2c, y2c, C["arrow"], sw=2, dash=C["arrow_dash"])
                )

            # Draw arrow head at destination
            # Calculate angle to destination
            import math

            angle = math.degrees(
                math.atan2(y2 - curve_points[-2][1], x2 - curve_points[-2][0])
            )
            lines.append(arrow_head(x2, y2, angle))

            # Label on the curve (middle point)
            mid_label_idx = len(curve_points) // 2
            label_x, label_y = curve_points[mid_label_idx]
            lines.append(
                text(
                    label_x - 15,
                    label_y - 8,
                    vm_name,
                    C["arrow"],
                    size=7,
                    weight="bold",
                )
            )

    return "\n".join(lines)


# ── LEGEND ────────────────────────────────────────────────────────────────────
def draw_legend(total_w, legend_y):
    items = [
        (C["host_bg"], C["host_border"], "1", "host (online)"),
        (C["host_off_bg"], C["host_off_bdr"], "1", "host (offline)"),
        (C["vm_bg"], C["vm_border"], "1", "virtual machine"),
        (C["vm_moving_bg"], C["vm_moving_border"], "1", "VM moving"),
    ]
    lines = []
    lx = MARGIN
    for fill, stroke, sw, label in items:
        lines.append(rect(lx, legend_y, 14, 10, fill, stroke, sw=sw))
        lines.append(text(lx + 18, legend_y + 9, label, C["legend_text"], size=9))
        lx += 140
    return "\n".join(lines)


# ── BUILD SVG ─────────────────────────────────────────────────────────────────
def build_svg():
    max_rack_h = max(rack_total_h(r) for r in RACKS)
    total_w = MARGIN * 2 + len(RACKS) * RACK_W + (len(RACKS) - 1) * RACK_PADDING
    legend_y = RACK_TOP + max_rack_h + 20
    total_h = legend_y + 30

    # Track which VMs are moving
    moving_vms = {m["vm"] for m in MOVEMENTS}

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total_w} {total_h}" '
        f'width="{total_w}" height="{total_h}" font-family="monospace">',
        rect(0, 0, total_w, total_h, C["bg"], "none", rx=12),
        text(total_w / 2, 38, TITLE, C["rack_border"], size=12, anchor="middle"),
    ]

    # Track host positions for arrows
    host_positions = HostPositions()

    # Draw racks
    for i, rack in enumerate(RACKS):
        rx = MARGIN + i * (RACK_W + RACK_PADDING)
        parts.append(
            draw_rack(rack, rx, max_rack_h, host_positions, moving_vms=moving_vms)
        )

    # Draw movement arrows (on top layer)
    parts.append(draw_movement_arrows(MOVEMENTS, host_positions))

    parts.append(draw_legend(total_w, legend_y))
    parts.append("</svg>")
    return "\n".join(parts)


# ── MAIN ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    out = "vm_movement_out.svg"
    svg = build_svg()
    with open(out, "w") as f:
        f.write(svg)
    print(f"✓ Saved {out}")
