"""Small reusable presentation components for Rebound pages."""

import streamlit as st

from .icons import icon as _icon
from .theme import PALETTE


PRIORITY_CHIP = {
    "High": ("rgba(250,133,90,.16)", "#8a3b1e"),
    "Medium": ("rgba(255,222,150,.38)", "#7a5a17"),
    "Low": ("rgba(98,196,218,.18)", "#0d5c6e"),
}

STATUS_TEXT = {
    "pending": "Planned",
    "completed": "Completed",
    "skipped": "Skipped",
}


def page_title(title, icon=None):
    """Render a page title with an optional inline icon."""
    icon_html = (_icon(icon, 26, PALETTE["coral"], 2.2) + " ") if icon else ""
    st.markdown(
        f"<h1 style='display:flex;align-items:center;gap:10px'>{icon_html}{title}</h1>",
        unsafe_allow_html=True,
    )


def section_title(title, icon=None):
    """Render a section title with an optional inline icon."""
    icon_html = (_icon(icon, 20, PALETTE["coral"], 2.2) + " ") if icon else ""
    st.markdown(
        f"<h3 style='display:flex;align-items:center;gap:8px'>{icon_html}{title}</h3>",
        unsafe_allow_html=True,
    )


def chip(text, bg, fg):
    """Return a reusable pill-shaped chip as HTML."""
    return f"<span class='rb-chip' style='background:{bg};color:{fg}'>{text}</span>"


def priority_badge(priority):
    """Return the priority badge used by study sessions and topic cards."""
    bg, fg = PRIORITY_CHIP.get(
        priority,
        ("rgba(98,196,218,.18)", "#0d5c6e"),
    )
    return chip(f"{priority} priority", bg, fg)


def status_badge(state):
    """Return the presentation badge for a study-session state."""
    if state == "completed":
        return chip("Completed", "#F6FFEA", "#3f6b1f")
    if state == "skipped":
        return chip("Skipped", "rgba(120,120,120,.16)", "#5b5b5b")
    return chip("Planned", "rgba(98,196,218,.18)", "#0d5c6e")
