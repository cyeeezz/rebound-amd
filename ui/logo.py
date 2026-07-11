"""Rebound brand lockup."""

from __future__ import annotations

import streamlit as st

from .theme import PALETTE


def render_rebound_logo(compact: bool = False) -> str:
    """Return the official Rebound lockup as clean inline SVG."""
    dark = st.session_state.get("theme") == "dark"
    word = "#F7F8FA" if dark else "#17233A"
    coral = PALETTE["coral"]
    symbol = (
        f"<svg width='30' height='30' viewBox='0 0 40 40' fill='none' role='img' "
        f"aria-label='Rebound logo'>"
        f"<path d='M32 20 a12 12 0 1 1 -4.6 -9.4' stroke='{coral}' stroke-width='4.2' "
        f"stroke-linecap='round' fill='none'/>"
        f"<path d='M25.5 8.4 l3.6 1.2 l-1.1 3.6 z' fill='{coral}'/>"
        f"<text x='20' y='26' text-anchor='middle' font-family='Inter,Arial,sans-serif' "
        f"font-weight='800' font-size='16' fill='{coral}'>R</text></svg>"
    )
    if compact:
        return f"<span style='display:inline-flex;align-items:center'>{symbol}</span>"
    return (
        f"<span style='display:inline-flex;align-items:center;gap:8px'>{symbol}"
        f"<span style='font-family:Inter,Arial,sans-serif;font-weight:800;"
        f"font-size:1.2rem;color:{word}'>Rebound</span></span>"
    )
