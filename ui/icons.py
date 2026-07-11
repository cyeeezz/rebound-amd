"""Inline SVG icon helpers for the Rebound interface."""


ICON_PATHS = {
    "home": "M3 10.5 12 3l9 7.5M5 9.5V21h14V9.5",
    "settings": "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6ZM19 12a7 7 0 0 0-.1-1l2-1.6-2-3.4-2.4 1a7 7 0 0 0-1.7-1L14.5 2h-5l-.3 3a7 7 0 0 0-1.7 1l-2.4-1-2 3.4L2.1 11a7 7 0 0 0 0 2l-2 1.6 2 3.4 2.4-1a7 7 0 0 0 1.7 1l.3 3h5l.3-3a7 7 0 0 0 1.7-1l2.4 1 2-3.4-2-1.6a7 7 0 0 0 .1-1Z",
    "book": "M4 4h9a3 3 0 0 1 3 3v13a3 3 0 0 0-3-3H4ZM20 4h-4a3 3 0 0 0-3 3v13a3 3 0 0 1 3-3h4Z",
    "clipboard": "M9 4h6a1 1 0 0 1 1 1v1H8V5a1 1 0 0 1 1-1ZM8 6H6a1 1 0 0 0-1 1v13a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V7a1 1 0 0 0-1-1h-2",
    "calendar": "M7 3v3M17 3v3M4 8h16M5 6h14a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1Z",
    "recovery": "M20 12a8 8 0 1 1-2.3-5.6M20 4v4h-4",
    "info": "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18ZM12 8h.01M11 12h1v5h1",
    "upload": "M12 15V4M8 8l4-4 4 4M4 17v2a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-2",
    "clock": "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18ZM12 7v5l3 2",
    "chart": "M4 20V10M10 20V4M16 20v-7M22 20H2",
    "compare": "M9 4 4 9l5 5M4 9h11M15 20l5-5-5-5M20 15H9",
    "zap": "M13 3 4 14h6l-1 7 9-11h-6z",
    "check": "M4 12l5 5L20 6",
    "x": "M6 6l12 12M18 6 6 18",
    "minus": "M5 12h14",
}


def icon(name, size=18, stroke="currentColor", sw=2):
    """Return a lucide-style inline SVG icon."""
    path = ICON_PATHS.get(name, "")
    return (
        f"<svg width='{size}' height='{size}' viewBox='0 0 24 24' fill='none' "
        f"stroke='{stroke}' stroke-width='{sw}' stroke-linecap='round' "
        f"stroke-linejoin='round' aria-hidden='true' style='vertical-align:-3px'>"
        f"<path d='{path}'/></svg>"
    )
