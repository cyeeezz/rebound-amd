"""Reusable, native-Streamlit presentation primitives for Rebound pages."""

from __future__ import annotations

import html
import re
from collections.abc import Callable, Sequence

import streamlit as st
from streamlit.delta_generator import DeltaGenerator

from .icons import icon as _icon
from .theme import PALETTE


PRIORITY_CHIP: dict[str, tuple[str, str]] = {
    "High": ("rgba(250,133,90,.16)", "#8a3b1e"),
    "Medium": ("rgba(255,222,150,.38)", "#7a5a17"),
    "Low": ("rgba(98,196,218,.18)", "#0d5c6e"),
}

STATUS_TEXT: dict[str, str] = {
    "pending": "Planned",
    "completed": "Completed",
    "skipped": "Skipped",
}

BADGE_TONES = frozenset({"neutral", "coral", "green", "blue", "amber", "purple", "danger"})
PANEL_TONES = frozenset({"neutral", "coral", "green", "blue", "amber", "purple", "danger"})


def _safe_text(value: object) -> str:
    """Return an HTML-safe string for non-interactive presentation markup."""
    return html.escape(str(value), quote=True)


def _safe_key(value: str) -> str:
    """Normalize a developer-provided component key for Streamlit CSS classes."""
    normalized = re.sub(r"[^A-Za-z0-9_-]+", "_", str(value)).strip("_")
    return normalized or "default"


def _tone(value: str, allowed: frozenset[str] = PANEL_TONES) -> str:
    """Return a supported visual tone, falling back to neutral."""
    return value if value in allowed else "neutral"


def page_shell(key: str = "default") -> DeltaGenerator:
    """Return a responsive native Streamlit container for a page's content."""
    return st.container(key=f"rb_page_{_safe_key(key)}")


def render_plain_page_header(
    title: str,
    subtitle: str | None = None,
    *,
    icon_name: str | None = None,
    right_content: Callable[[], None] | None = None,
) -> None:
    """Render production page-heading content with no badge or status path."""
    icon_html = (
        f"<span class='rb-plain-page-icon'>{_icon(icon_name, 23, PALETTE['coral'], 2)}</span>"
        if icon_name
        else ""
    )
    subtitle_html = (
        f"<div class='rb-plain-page-subtitle'>{_safe_text(subtitle)}</div>" if subtitle else ""
    )
    def _render_left() -> None:
        st.markdown(
            "<div class='rb-plain-page-header'>"
            f"{icon_html}<div class='rb-plain-page-heading'>"
            f"<div class='rb-plain-page-title'><h1>{_safe_text(title)}</h1></div>"
            f"{subtitle_html}</div></div>",
            unsafe_allow_html=True,
        )

    if right_content is None:
        _render_left()
        return

    left, right = st.columns([3.2, 2.2], gap="large", vertical_alignment="center")
    with left:
        _render_left()
    with right:
        right_content()


def section_header(
    title: str,
    subtitle: str = "",
    *,
    icon_name: str | None = None,
    trailing_text: str | None = None,
) -> None:
    """Render an escaped section heading with optional static trailing text."""
    icon_html = _icon(icon_name, 19, PALETTE["coral"], 2) if icon_name else ""
    subtitle_html = (
        f"<div class='rb-ui-section-subtitle'>{_safe_text(subtitle)}</div>" if subtitle else ""
    )
    trailing_html = (
        f"<div class='rb-ui-section-trailing'>{_safe_text(trailing_text)}</div>"
        if trailing_text
        else ""
    )
    st.markdown(
        "<div class='rb-ui-section-header'>"
        f"<div class='rb-ui-section-icon'>{icon_html}</div>"
        f"<div class='rb-ui-section-copy'><h2>{_safe_text(title)}</h2>{subtitle_html}</div>"
        f"{trailing_html}</div>",
        unsafe_allow_html=True,
    )


def page_title(title: str, icon: str | None = None) -> None:
    """Render the legacy Rebound page title with escaped text."""
    icon_html = (_icon(icon, 26, PALETTE["coral"], 2.2) + " ") if icon else ""
    st.markdown(
        f"<h1 style='display:flex;align-items:center;gap:10px'>{icon_html}{_safe_text(title)}</h1>",
        unsafe_allow_html=True,
    )


def section_title(title: str, icon: str | None = None) -> None:
    """Render the legacy Rebound section title with escaped text."""
    icon_html = (_icon(icon, 20, PALETTE["coral"], 2.2) + " ") if icon else ""
    st.markdown(
        f"<h3 style='display:flex;align-items:center;gap:8px'>{icon_html}{_safe_text(title)}</h3>",
        unsafe_allow_html=True,
    )


def primary_action_area(key: str) -> DeltaGenerator:
    """Return a native container for a page's primary action controls."""
    return st.container(key=f"rb_primary_actions_{_safe_key(key)}")


def secondary_action_area(key: str) -> DeltaGenerator:
    """Return a native container for secondary or supporting controls."""
    return st.container(key=f"rb_secondary_actions_{_safe_key(key)}")


def card(key: str, *, tone: str = "neutral") -> DeltaGenerator:
    """Return a styled native Streamlit card container."""
    return st.container(key=f"rb_card_{_tone(tone)}_{_safe_key(key)}")


def sidebar_insight_card(key: str, *, tone: str = "neutral") -> DeltaGenerator:
    """Return a compact native card intended for a page insight rail."""
    return st.container(key=f"rb_insight_{_tone(tone)}_{_safe_key(key)}")


def metric_card(
    label: str,
    value: str,
    *,
    key: str,
    caption: str = "",
    icon_name: str | None = None,
    tone: str = "neutral",
) -> None:
    """Render a static metric inside a native styled card container."""
    icon_html = _icon(icon_name, 18, "currentColor", 2) if icon_name else ""
    caption_html = (
        f"<div class='rb-ui-metric-caption'>{_safe_text(caption)}</div>" if caption else ""
    )
    with st.container(key=f"rb_metric_{_tone(tone)}_{_safe_key(key)}"):
        st.markdown(
            "<div class='rb-ui-metric-label'>"
            f"{icon_html}<span>{_safe_text(label)}</span></div>"
            f"<div class='rb-ui-metric-value'>{_safe_text(value)}</div>{caption_html}",
            unsafe_allow_html=True,
        )


def chip(text: object, bg: str, fg: str) -> str:
    """Return an escaped pill-shaped chip as non-interactive HTML."""
    return (
        f"<span class='rb-chip' style='background:{_safe_text(bg)};color:{_safe_text(fg)}'>"
        f"{_safe_text(text)}</span>"
    )


def badge(text: object, tone: str = "neutral") -> str:
    """Return an escaped semantic badge as non-interactive HTML."""
    safe_tone = _tone(tone, BADGE_TONES)
    return f"<span class='rb-ui-badge rb-ui-tone-{safe_tone}'>{_safe_text(text)}</span>"


def priority_badge(priority: str) -> str:
    """Return the priority badge used by study sessions and topic cards."""
    bg, fg = PRIORITY_CHIP.get(priority, ("rgba(98,196,218,.18)", "#0d5c6e"))
    return chip(f"{priority} priority", bg, fg)


def status_badge(state: str) -> str:
    """Return the presentation badge for a study-session state."""
    if state == "completed":
        return chip("Completed", "#F6FFEA", "#3f6b1f")
    if state == "skipped":
        return chip("Skipped", "rgba(120,120,120,.16)", "#5b5b5b")
    return chip("Planned", "rgba(98,196,218,.18)", "#0d5c6e")


def feedback_panel(
    title: str,
    message: str,
    *,
    key: str,
    tone: str = "blue",
    icon_name: str = "info",
) -> None:
    """Render escaped feedback content in a native pastel panel."""
    safe_tone = _tone(tone)
    with st.container(key=f"rb_feedback_{safe_tone}_{_safe_key(key)}"):
        st.markdown(
            "<div class='rb-ui-feedback-content'>"
            f"<span class='rb-ui-feedback-icon'>{_icon(icon_name, 18, 'currentColor', 2)}</span>"
            "<div>"
            f"<div class='rb-ui-feedback-title'>{_safe_text(title)}</div>"
            f"<div class='rb-ui-feedback-message'>{_safe_text(message)}</div>"
            "</div></div>",
            unsafe_allow_html=True,
        )


def empty_state(
    title: str,
    message: str,
    *,
    key: str,
    icon_name: str = "info",
) -> None:
    """Render an escaped, non-interactive empty state in a native container."""
    with st.container(key=f"rb_empty_{_safe_key(key)}"):
        st.markdown(
            "<div class='rb-ui-empty-icon'>"
            f"{_icon(icon_name, 24, PALETTE['sky'], 1.9)}</div>"
            f"<div class='rb-ui-empty-title'>{_safe_text(title)}</div>"
            f"<div class='rb-ui-empty-message'>{_safe_text(message)}</div>",
            unsafe_allow_html=True,
        )


def progress_display(
    value: float,
    *,
    key: str,
    label: str = "",
    caption: str = "",
) -> None:
    """Render a labelled native Streamlit progress bar with a clamped value."""
    progress = max(0.0, min(float(value), 1.0))
    with st.container(key=f"rb_progress_{_safe_key(key)}"):
        if label:
            st.markdown(
                f"<div class='rb-ui-progress-label'>{_safe_text(label)}"
                f"<span>{progress:.0%}</span></div>",
                unsafe_allow_html=True,
            )
        st.progress(progress)
        if caption:
            st.caption(caption)


def responsive_button_row(
    count: int,
    *,
    key: str,
    widths: Sequence[int | float] | None = None,
    gap: str = "small",
) -> list[DeltaGenerator]:
    """Return native Streamlit columns that stack at the shared mobile breakpoint."""
    if count < 1:
        raise ValueError("count must be at least 1")
    spec: Sequence[int | float] = widths if widths is not None else [1] * count
    if len(spec) != count:
        raise ValueError("widths must contain exactly count entries")
    with st.container(key=f"rb_button_row_{_safe_key(key)}"):
        columns = st.columns(list(spec), gap=gap)
    return columns
