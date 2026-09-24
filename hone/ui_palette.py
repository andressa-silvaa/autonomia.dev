from __future__ import annotations

BRAND_CORAL = "#F0643C"
COOL_TEAL = "#2A9D8F"
MUTED_NEUTRAL = "#8C8279"
MUSTARD_WARNING = "#D9A21B"

RICH_STYLES = {
    "accent": f"bold {BRAND_CORAL}",
    "secondary": COOL_TEAL,
    "muted": MUTED_NEUTRAL,
    "warning": MUSTARD_WARNING,
    "title": f"bold {BRAND_CORAL}",
    "ok": f"bold {COOL_TEAL}",
    "challenge": f"bold {MUSTARD_WARNING}",
}

LIGHT_THEME = {
    "bg": "#F7F2EC",
    "surface": "#FFFCF8",
    "text": "#231E1A",
    "text-muted": "#6E645B",
    "border": "#E4D9CD",
    "accent": BRAND_CORAL,
    "accent-text": "#B8431F",
    "accent-soft": "#FCE3D9",
    "secondary": "#1F7A70",
    "secondary-soft": "#D7EFEB",
    "warning": "#9A6F06",
    "warning-soft": "#FBEFCB",
}

DARK_THEME = {
    "bg": "#181513",
    "surface": "#221E1B",
    "text": "#F2ECE5",
    "text-muted": "#A99D92",
    "border": "#38312B",
    "accent": "#FF7A52",
    "accent-text": "#FF8F6B",
    "accent-soft": "#3F2419",
    "secondary": "#4CC2B2",
    "secondary-soft": "#17332F",
    "warning": "#F0C24B",
    "warning-soft": "#3A2F12",
}

HEADING_FONT = "'Bricolage Grotesque', 'Segoe UI', system-ui, sans-serif"
BODY_FONT = "'Atkinson Hyperlegible', 'Segoe UI', system-ui, sans-serif"
MONO_FONT = "'JetBrains Mono', 'Cascadia Code', Consolas, monospace"
