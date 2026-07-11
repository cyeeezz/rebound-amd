"""Rebound — adaptive exam-recovery planner."""

import base64
import hashlib
import html
import io
import json
import os
import random
import re
import time
from collections import Counter
from datetime import date, timedelta

import streamlit as st

from ui.components import (
    PRIORITY_CHIP as _PRIORITY_CHIP,
    STATUS_TEXT as _STATUS_TEXT,
    chip as _chip,
    page_title as _page_title,
    priority_badge as _priority_chip,
    section_title as _section,
    status_badge as _status_chip,
)
from ui.icons import ICON_PATHS as _ICON_PATHS
from ui.icons import icon as _icon
from ui.logo import render_rebound_logo
from ui.theme import PALETTE as _PALETTE
from ui.theme import inject_css as _inject_css
from ui.theme import theme_css
from ui.theme import theme_vars as _theme_vars

# OpenAI SDK is used as the Fireworks-compatible client. Import is guarded so a
# missing package can never crash the app — analysis falls back to local logic.
try:
    from openai import OpenAI
except Exception:  # pragma: no cover - openai not installed
    OpenAI = None

st.set_page_config(page_title="Rebound", page_icon="📚", layout="wide")

# ---------------------------------------------------------------------------
# Session state initialization
# ---------------------------------------------------------------------------
DEFAULT_STATE = {
    "document_text": "",        # uploaded document text
    "topics": [],               # extracted topics
    "prerequisites": {},        # prerequisite relationships {topic: [prereqs]}
    "diagnostic_questions": [], # generated diagnostic questions
    "diagnostic_results": {},   # answers / correctness per question
    "mastery_scores": {},       # {topic: score 0..1}
    "study_plan": [],           # ordered study plan entries
    "recovery_decisions": [],   # adaptive recovery decisions log
    "amd_runtime": {},          # AMD runtime information
    "uploaded_pdf": None,
    "recovered_plan": None,     # recovered plan (kept for backward compat)
    "session_status": {},       # {topic: "completed"/"skipped"/"pending"}
    "recovery_preview": None,   # proposed recovered plan (before Apply)
    "recovery_changes": [],     # per-topic change classification for the preview
    "recovery_settings": {},    # last-used recovery settings
}

for key, default in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
# ===========================================================================
# Fireworks AI document-analysis pipeline
# ---------------------------------------------------------------------------
# The UI never calls Fireworks directly — it orchestrates these helpers.
# To go live, replace ONLY the body of analyze_document_with_fireworks() with
# a real Fireworks API call that returns the same {"model", "sections"} shape;
# every other function keeps working unchanged.
# ===========================================================================

# --- Fireworks AI configuration --------------------------------------------
# Primary chat / reasoning model for ALL language tasks: document analysis,
# knowledge extraction, summarisation, knowledge-map generation, diagnostic
# question generation, expected answers, marking, planner & recovery reasoning.
# Overridable via env so the id can change without touching code.
FIREWORKS_CHAT_MODEL = os.getenv(
    "FIREWORKS_CHAT_MODEL", "accounts/fireworks/models/deepseek-v4-pro"
)
# Single source of truth used across the UI + logging.
FIREWORKS_MODEL = {"id": FIREWORKS_CHAT_MODEL, "display": "DeepSeek V4 Pro"}

FIREWORKS_BASE_URL = "https://api.fireworks.ai/inference/v1"

# OCR is OFF by default — the revision notes are digital-text PDFs. A vision
# model is only used when it is explicitly configured (FIREWORKS_VISION_MODEL)
# and the extracted text is essentially empty. No deprecated model is hardcoded.
FIREWORKS_VISION_MODEL = os.getenv("FIREWORKS_VISION_MODEL", "")
OCR_ENABLED = os.getenv("REBOUND_OCR", "0").lower() not in ("0", "", "false", "no")
_OCR_TEXT_THRESHOLD = 50

# Fireworks errors fall back to local heuristics ONLY when DEBUG_OFFLINE is set;
# otherwise the real error is surfaced to the user (no hidden fallback).
DEBUG_OFFLINE = os.getenv("DEBUG_OFFLINE", "0").lower() not in ("0", "", "false", "no")

# API key is resolved only from st.secrets or the environment (never hardcoded).

# DeepSeek V4 Pro has a 1M-token context, so we DO NOT truncate at 12k: the
# whole document is sent. Very large documents are split into chunks that are
# analysed individually and merged (see analyze_document_with_fireworks).
_FIREWORKS_MAX_CHARS = 500_000
_FIREWORKS_CHUNK_CHARS = 40_000


def _get_fireworks_api_key() -> str:
    """Resolve the Fireworks API key from st.secrets or the environment only.

    Never returns a hardcoded key. Raises a clear configuration error if unset.
    """
    try:
        if "FIREWORKS_API_KEY" in st.secrets:
            key = st.secrets["FIREWORKS_API_KEY"]
            if key:
                return key
    except Exception:
        pass  # no secrets.toml configured
    key = os.getenv("FIREWORKS_API_KEY")
    if key:
        return key
    raise RuntimeError(
        "FIREWORKS_API_KEY is not configured. Add it to .streamlit/secrets.toml "
        "or set the FIREWORKS_API_KEY environment variable."
    )


_STOPWORDS = {
    "the", "and", "for", "are", "but", "not", "you", "all", "any", "can",
    "her", "was", "one", "our", "out", "his", "has", "had", "how", "its",
    "who", "get", "use", "this", "that", "with", "from", "they", "them",
    "then", "than", "into", "such", "some", "each", "will", "when", "where",
    "which", "these", "those", "there", "their", "have", "been", "also",
    "more", "most", "other", "about", "between", "because", "while", "role",
    "key", "ideas", "example", "context", "importance", "relationship",
}

# Shared difficulty / marking scales used by the diagnostic and planner.
DIFFICULTY_RANK = {"Easy": 1, "Medium": 2, "Hard": 3}
MARKS_BY_DIFFICULTY = {"Easy": [2, 3], "Medium": [3, 4], "Hard": [4, 5]}


def _read_pdf(uploaded_file) -> tuple[str, int]:
    """Read raw text and page count from an uploaded PDF.

    Extraction cascade — only declared "scanned" if ALL methods fail:
        1. pdfplumber  (primary)
        2. PyMuPDF / fitz  (fallback if pdfplumber yields very little text)
        3. pypdf  (final fallback)

    Returns (text, page_count) and prints extraction statistics for debugging.
    """
    file_bytes = uploaded_file.getvalue() if hasattr(uploaded_file, "getvalue") else uploaded_file.read()
    text, pages = "", 0

    # 1) pdfplumber -------------------------------------------------------
    try:
        import io

        import pdfplumber

        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            pages = len(pdf.pages)
            text = "\n".join((p.extract_text() or "") for p in pdf.pages).strip()
        if len(text) >= 20:
            return _report_extraction("pdfplumber", text, pages)
    except Exception as exc:
        print(f"[Rebound] pdfplumber failed: {exc}")

    # 2) PyMuPDF (fitz) ---------------------------------------------------
    try:
        import fitz  # PyMuPDF

        with fitz.open(stream=file_bytes, filetype="pdf") as doc:
            pages = doc.page_count
            text = "\n".join(page.get_text() for page in doc).strip()
        if len(text) >= 20:
            return _report_extraction("PyMuPDF", text, pages)
    except Exception as exc:
        print(f"[Rebound] PyMuPDF failed: {exc}")

    # 3) pypdf ------------------------------------------------------------
    try:
        import io

        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(file_bytes))
        pages = len(reader.pages)
        text = "\n".join((page.extract_text() or "") for page in reader.pages).strip()
        if len(text) >= 20:
            return _report_extraction("pypdf", text, pages)
    except Exception as exc:
        print(f"[Rebound] pypdf failed: {exc}")

    # All methods failed -> likely a scanned/image-only PDF
    print(
        f"[Rebound] Extraction failed on all methods. "
        f"Pages read: {pages} | Characters: {len(text)} | Words: {len(text.split())}"
    )
    return text, pages


def _report_extraction(method: str, text: str, pages: int) -> tuple[str, int]:
    """Print extraction statistics for debugging and return (text, pages)."""
    print(
        f"[Rebound] Extraction via {method} — "
        f"Pages read: {pages} | "
        f"Characters extracted: {len(text)} | "
        f"Words extracted: {len(text.split())}"
    )
    return text, pages


def _pdf_bytes(uploaded_file) -> bytes:
    """Return the raw bytes of an uploaded PDF without consuming its stream."""
    if hasattr(uploaded_file, "getvalue"):
        return uploaded_file.getvalue()
    uploaded_file.seek(0)
    return uploaded_file.read()


def _ocr_page_with_vision(client, png_bytes: bytes, page_num: int) -> str:
    """Run OCR on one page image via the Fireworks vision model."""
    b64 = base64.b64encode(png_bytes).decode("utf-8")
    prompt = (
        "You are an OCR engine. Transcribe ALL readable text from this page "
        "verbatim, preserving line breaks and reading order. Return only the "
        "extracted text with no commentary."
    )
    response = client.chat.completions.create(
        model=FIREWORKS_VISION_MODEL,
        temperature=0,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{b64}"},
                    },
                ],
            }
        ],
    )
    return (response.choices[0].message.content or "").strip()


def extract_pdf_text_with_ocr(uploaded_file, notify=None) -> str:
    """OCR a scanned/image PDF via a configured Fireworks vision model.

    Disabled by default: OCR only runs when a vision model is configured
    (FIREWORKS_VISION_MODEL) and OCR mode is enabled (REBOUND_OCR=1). Digital-
    text PDFs never reach this path. Returns "" if OCR is unavailable.
    """
    if not (OCR_ENABLED and FIREWORKS_VISION_MODEL):
        print("[Rebound] OCR disabled (digital-text PDFs; set REBOUND_OCR=1 "
              "and FIREWORKS_VISION_MODEL to enable).")
        return ""
    if OpenAI is None:
        print("[Rebound] OCR skipped — openai SDK not installed.")
        return ""
    try:
        from pdf2image import convert_from_bytes
    except Exception as exc:
        print(f"[Rebound] OCR skipped — pdf2image unavailable: {exc}")
        return ""
    try:
        images = convert_from_bytes(_pdf_bytes(uploaded_file), dpi=200)
    except Exception as exc:
        print(f"[Rebound] OCR failed to rasterize PDF (is poppler installed?): {exc}")
        return ""

    client = OpenAI(api_key=_get_fireworks_api_key(), base_url=FIREWORKS_BASE_URL)
    pages_text: list[str] = []
    for i, image in enumerate(images, start=1):
        if notify:
            notify(f"🔍 AI OCR — reading page {i} of {len(images)}...")
        try:
            buf = io.BytesIO()
            image.save(buf, format="PNG")
            page_text = _ocr_page_with_vision(client, buf.getvalue(), i)
            if page_text:
                pages_text.append(page_text)
        except Exception as exc:
            print(f"[Rebound] OCR failed on page {i}: {exc}")
            continue

    consolidated = "\n\n".join(pages_text).strip()
    print(f"[Rebound] Vision OCR — Pages: {len(images)} | Characters: {len(consolidated)}")
    return consolidated


def extract_pdf_text(uploaded_file, notify=None) -> str:
    """Extract text from an uploaded PDF (text-first; OCR only if configured).

    Digital-text PDFs are read with pdfplumber/PyMuPDF/pypdf. OCR is only
    attempted when the extracted text is under _OCR_TEXT_THRESHOLD characters
    AND OCR mode is explicitly enabled — normal notes skip OCR entirely.
    """
    text, _ = _read_pdf(uploaded_file)
    if len(text.strip()) >= _OCR_TEXT_THRESHOLD:
        return text
    if not (OCR_ENABLED and FIREWORKS_VISION_MODEL):
        return text  # nothing extractable and OCR disabled
    if notify:
        notify("📄 Scanned PDF detected. Running AI OCR...")
    ocr_text = extract_pdf_text_with_ocr(uploaded_file, notify=notify)
    return ocr_text if ocr_text else text


def count_pdf_pages(uploaded_file) -> int:
    """Return the number of pages in an uploaded PDF."""
    _, pages = _read_pdf(uploaded_file)
    return pages


# --- Text utilities --------------------------------------------------------
def _sentences(text: str) -> list[str]:
    """Split text into sentences."""
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) > 3]


def _is_heading(line: str) -> bool:
    """Heuristic: does this line look like a section heading?"""
    words = line.split()
    if not words or len(words) > 8 or len(line) > 60:
        return False
    if line.endswith((".", ",", ";", "!", "?")):
        return False
    if re.match(r"^(chapter|section|unit|topic|part)\b", line, re.I):
        return True
    if re.match(r"^\d+[.)]\s", line):
        return True
    if line.isupper() and len(line) > 3:
        return True
    caps = sum(1 for w in words if w[:1].isupper())
    return caps >= max(1, len(words) - 1)


def _clean_title(line: str) -> str:
    """Strip numbering / markers from a heading line."""
    line = re.sub(r"^(chapter|section|unit|topic|part)\s*\d*[:.\-]?\s*", "", line, flags=re.I)
    line = re.sub(r"^\d+[.)]\s*", "", line)
    return line.strip(" :-•*").strip()[:60] or "Untitled Section"


def _segment_sections(text: str) -> list[dict]:
    """Split document text into sections using heading detection.

    Purely text-driven: a different document yields different sections.
    """
    sections: list[dict] = []
    current: dict | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if _is_heading(line):
            if current:
                sections.append(current)
            current = {"title": _clean_title(line), "lines": []}
        else:
            if current is None:
                current = {"title": _clean_title(line[:50]), "lines": []}
            current["lines"].append(line)
    if current:
        sections.append(current)

    # Fallback: no usable headings -> split on blank-line blocks
    if len(sections) <= 1:
        blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
        sections = []
        for block in blocks:
            first = block.splitlines()[0].strip()
            sections.append(
                {"title": _clean_title(first[:50]), "lines": block.splitlines()}
            )

    for sec in sections:
        sec["body"] = " ".join(sec["lines"]).strip()
    return [s for s in sections if s["title"] and s["body"]]


def _key_concepts(lines: list[str], limit: int = 6) -> list[str]:
    """Extract candidate key concepts from a section's text."""
    body = " ".join(lines)
    tokens = re.findall(r"[A-Za-z][A-Za-z\-]{3,}", body)
    caps = [t for t in tokens if t[0].isupper() and t.lower() not in _STOPWORDS]
    concepts, seen = [], set()
    for term, _ in Counter(caps).most_common():
        if term.lower() not in seen:
            concepts.append(term)
            seen.add(term.lower())
        if len(concepts) >= limit:
            break
    if len(concepts) < limit:
        common = Counter(
            t.lower() for t in tokens if t.lower() not in _STOPWORDS
        ).most_common()
        for term, _ in common:
            if term not in seen:
                concepts.append(term)
                seen.add(term)
            if len(concepts) >= limit:
                break
    return concepts[:limit] or ["general principles"]


def _learning_objectives(lines: list[str], title: str) -> list[str]:
    """Derive learning objectives from bullet lines or leading sentences."""
    bullets = [
        re.sub(r"^[-•*]\s*", "", ln).strip()
        for ln in lines
        if re.match(r"^[-•*]\s+", ln)
    ]
    objs = [b for b in bullets if len(b) > 3]
    if objs:
        return objs[:5]
    sents = _sentences(" ".join(lines))
    if sents:
        return [f"Understand: {s[:90]}" for s in sents[:3]]
    return [f"Understand the key ideas of {title}"]


def _quick_check(title: str, concepts: list[str]) -> str:
    """Generate a quick-check question from the section's concepts."""
    if concepts and concepts[0] != "general principles":
        return f"Explain the role of {concepts[0]} in {title}."
    return f"Summarise the key ideas of {title}."


def _estimate_difficulty(body: str) -> str:
    """Estimate difficulty from length and vocabulary diversity."""
    words = body.split()
    wc = len(words)
    diversity = len({w.lower() for w in words}) / wc if wc else 0
    if wc < 45:
        return "Easy"
    if wc < 130 or diversity < 0.55:
        return "Medium"
    return "Hard"


def _estimate_study_time(body: str) -> str:
    """Estimate study time (minutes, rounded to 15) from length."""
    wc = len(body.split())
    minutes = 15 * max(1, min(6, round(wc / 50)))
    return f"{minutes} min"


def _fallback_response(text: str, model: dict, source: str) -> dict:
    """Build a response from local heuristic segmentation (never crashes)."""
    segments = _segment_sections(text)
    return {
        "model": model["id"],
        "model_display": model["display"],
        "created": time.time(),
        "source": source,
        "sections": [
            {"title": s["title"], "body": s["body"], "lines": s["lines"]}
            for s in segments
        ],
    }


def _normalize_api_sections(raw_sections: list) -> list[dict]:
    """Validate and normalize the model's section objects."""
    sections = []
    for item in raw_sections:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip()
        body = str(item.get("body", "")).strip()
        if not title or not body:
            continue
        sections.append({"title": title[:80], "body": body, "lines": body.splitlines()})
    return sections


_DOC_ANALYSIS_SYSTEM_PROMPT = (
    "You are an expert biology study assistant. Split the student's revision "
    "notes into coherent LEARNING TOPICS. Each topic must be a real biology "
    "topic, not a formatting heading. Treat 'Learning Objectives', 'Quick "
    "Check', 'Example', 'Why This Matters', 'Key Points', 'Summary' and "
    "'References' as metadata belonging to a topic — never as topics "
    "themselves. Return ONLY a JSON object of the form "
    '{"sections":[{"title":"<topic>","body":"<all notes text for that topic>"}]}. '
    "Preserve the document's wording in each body. Do not invent content."
)


def _chunk_text(text: str, size: int) -> list:
    """Split text into <= `size`-char chunks (never truncates content)."""
    return [text[i:i + size] for i in range(0, len(text), size)] or [""]


def analyze_document_with_fireworks(text: str, model: dict = FIREWORKS_MODEL) -> dict:
    """Analyze the whole document with Fireworks into topic sections.

    The full document is analysed (no 12k truncation): large documents are
    split into chunks, each analysed, and the resulting sections merged. The
    active model is printed on every call. On error the real exception is
    raised (surfaced to the user) unless DEBUG_OFFLINE is set, in which case it
    falls back to local heuristic segmentation for offline development.
    """
    active = FIREWORKS_CHAT_MODEL
    print(f"[Rebound] Fireworks Model: {active}")

    if OpenAI is None:
        if DEBUG_OFFLINE:
            print("[Rebound] DEBUG_OFFLINE: openai SDK missing — local segmentation.")
            return _fallback_response(text, model, source="fallback:no-sdk")
        raise RuntimeError("openai SDK not installed. Run: pip install -r requirements.txt")

    try:
        client = OpenAI(api_key=_get_fireworks_api_key(), base_url=FIREWORKS_BASE_URL)
        chunks = _chunk_text(text[:_FIREWORKS_MAX_CHARS], _FIREWORKS_CHUNK_CHARS)
        merged: dict[str, dict] = {}
        order: list[str] = []
        returned_model = active
        for ci, chunk in enumerate(chunks, 1):
            if len(chunks) > 1:
                print(f"[Rebound] Analysing chunk {ci}/{len(chunks)} ({len(chunk)} chars)...")
            response = client.chat.completions.create(
                model=active,
                response_format={"type": "json_object"},
                temperature=0.2,
                messages=[
                    {"role": "system", "content": _DOC_ANALYSIS_SYSTEM_PROMPT},
                    {"role": "user", "content": chunk},
                ],
            )
            returned_model = getattr(response, "model", None) or active
            payload = json.loads(response.choices[0].message.content)
            for sec in _normalize_api_sections(payload.get("sections", [])):
                key = sec["title"].lower()
                if key in merged:
                    merged[key]["body"] += "\n" + sec["body"]
                    merged[key]["lines"] += sec["lines"]
                else:
                    merged[key] = sec
                    order.append(key)

        sections = [merged[k] for k in order]
        if not sections:
            raise ValueError("Fireworks returned no valid sections.")
        print(f"[Rebound] Topics extracted: {len(sections)}")
        return {
            "model": returned_model,
            "model_display": model["display"],
            "created": time.time(),
            "source": "fireworks-api",
            "sections": sections,
        }
    except Exception as exc:
        print(f"[Rebound] Fireworks analysis error: {exc}")
        if DEBUG_OFFLINE:
            print("[Rebound] DEBUG_OFFLINE: using local segmentation.")
            return _fallback_response(text, model, source="fallback:api-error")
        raise


# --- Per-topic field extraction (metadata kept separate from concepts) -----
def _section_definitions(body: str, limit: int = 5) -> list:
    """Definition-style sentences ('X is/are/refers to ...') from the topic."""
    out = []
    for sent in _sentences(body):
        if re.search(r"\b(is|are|refers to|means|defined as|consists of)\b", sent.lower()):
            out.append(sent.strip())
        if len(out) >= limit:
            break
    return out


def _important_facts(body: str, limit: int = 4) -> list:
    """Key factual sentences — prefer those with figures/quantities."""
    sents = _sentences(body)
    facts = [s for s in sents if re.search(r"\d", s)]
    for s in sents:
        if len(facts) >= limit:
            break
        if s not in facts:
            facts.append(s)
    return facts[:limit]


def _section_processes(concepts: list, body: str, limit: int = 5) -> list:
    """Biological processes: process-like concepts + step/pathway sentences."""
    procs = [c for c in concepts if re.search(r"(sis|tion|lysis|olysis|cycle)$", c.lower())]
    for s in _sentences(body):
        if re.search(r"\b(process|pathway|cycle|stage|step|produces|converts|releases|synthesis)\b", s.lower()):
            procs.append(s.strip())
        if len(procs) >= limit * 2:
            break
    seen, out = set(), []
    for p in procs:
        if p.lower() not in seen:
            seen.add(p.lower())
            out.append(p)
    return out[:limit]


def _section_example(body: str) -> str:
    """An illustrative example sentence, if the notes contain one (metadata)."""
    for s in _sentences(body):
        if re.search(r"\b(for example|e\.g\.|such as|for instance)\b", s.lower()):
            return s.strip()
    return ""


def build_sections(raw_sections: list) -> list:
    """Turn raw analyzed sections into fully structured topic objects.

    Concepts/definitions/facts/processes are real biology content; learning
    objectives, example and quick-check are kept as metadata (never concepts).
    """
    sections = []
    for raw in raw_sections:
        title = raw["title"]
        lines = raw.get("lines", raw.get("body", "").splitlines())
        body = raw.get("body", " ".join(lines))
        concepts = _key_concepts(lines)
        sections.append({
            "title": title,
            "summary": (_sentences(body)[:2] and " ".join(_sentences(body)[:2])) or body[:180],
            "key_concepts": concepts,
            "definitions": _section_definitions(body),
            "important_facts": _important_facts(body),
            "processes": _section_processes(concepts, body),
            "relationships": [],   # filled by build_topic_graph
            "learning_objectives": _learning_objectives(lines, title),  # metadata
            "example": _section_example(body),                          # metadata
            "quick_check": _quick_check(title, concepts),               # metadata
            "prerequisites": [],   # filled by build_topic_graph
            "estimated_difficulty": _estimate_difficulty(body),
            "estimated_study_time": _estimate_study_time(body),
            "_body": body,
        })
    return sections


def parse_fireworks_response(raw: dict) -> list:
    """Parse a Fireworks-style response into structured section objects."""
    return build_sections(raw.get("sections", []))


def build_topic_graph(sections: list) -> dict:
    """Infer prerequisite / relationship edges between topics from content."""
    graph = {s["title"]: [] for s in sections}
    for i, sec in enumerate(sections):
        body_lower = sec.get("_body", "").lower()
        concepts = {c.lower() for c in sec["key_concepts"]}
        for earlier in sections[:i]:
            title = earlier["title"]
            shared = concepts & {c.lower() for c in earlier["key_concepts"]}
            if title.lower() in body_lower or len(shared) >= 2:
                if title not in graph[sec["title"]]:
                    graph[sec["title"]].append(title)
    for sec in sections:
        sec["prerequisites"] = graph[sec["title"]]
        sec["relationships"] = graph[sec["title"]]
    return graph


def calculate_document_statistics(text: str, pages: int, sections: list) -> dict:
    """Compute document statistics and a heuristic complexity rating."""
    words = re.findall(r"[A-Za-z']+", text)
    wc = len(words) or 1
    sentences = _sentences(text)
    paragraphs = [p for p in re.split(r"\n\s*\n", text) if p.strip()]

    avg_sentence_len = wc / (len(sentences) or 1)
    vocab_diversity = len({w.lower() for w in words}) / wc
    concept_total = sum(len(s["key_concepts"]) for s in sections)
    concept_density = concept_total / wc * 100

    complexity_score = min(
        1.0,
        (avg_sentence_len / 25) * 0.4
        + vocab_diversity * 0.3
        + min(1.0, concept_density / 5) * 0.3,
    )
    complexity = (
        "High" if complexity_score >= 0.66
        else "Medium" if complexity_score >= 0.4
        else "Low"
    )

    return {
        "pages": pages,
        "paragraphs": len(paragraphs),
        "words": len(words),
        "characters": len(text),
        "headings": len(sections),
        "reading_minutes": max(1, round(len(words) / 200)),
        "exam_topics": len(sections),
        "concepts": concept_total,
        "definitions": sum(len(s.get("definitions", [])) for s in sections),
        "relationships": sum(len(s.get("prerequisites", [])) for s in sections),
        "avg_sentence_length": round(avg_sentence_len, 1),
        "vocab_diversity": round(vocab_diversity, 2),
        "concept_density": round(concept_density, 2),
        "complexity_score": round(complexity_score, 2),
        "complexity": complexity,
    }


def split_paragraphs(document_text: str) -> list[str]:
    """Split document text into non-empty paragraphs."""
    return [p.strip() for p in document_text.split("\n\n") if p.strip()]


# ===========================================================================
# Diagnostic — question generation (derived from the extracted Knowledge Map)
# ---------------------------------------------------------------------------
# All question/answer intelligence lives in these helpers so it can later be
# swapped for a Fireworks call without touching the UI.
# ===========================================================================
def _kw(terms, limit: int = 5) -> list:
    """Flatten terms into up to `limit` deduped, meaningful lowercase keywords."""
    out, seen = [], set()
    for t in terms:
        for w in re.findall(r"[A-Za-z][A-Za-z\-]{2,}", str(t)):
            wl = w.lower()
            if wl in _STOPWORDS or wl in seen:
                continue
            seen.add(wl)
            out.append(wl)
            if len(out) >= limit:
                return out
    return out


def _plan_seed(sections) -> int:
    """Deterministic seed from section titles so results are stable per document."""
    return abs(hash("|".join(s.get("title", "") for s in sections))) % (2**32)


def _question_bank_for_section(section) -> list:
    """Build candidate questions (no marks yet) for one section.

    Covers definitions, key concepts, scenario/application, relationships,
    cause-and-effect, process description and exam-style synthesis. No
    formatting words are used, so nothing is rejected by the quality filter.
    """
    topic = section.get("title", "Topic")
    concepts = [c for c in section.get("key_concepts", []) if c and c != "general principles"]
    prereqs = section.get("prerequisites", [])
    out = []
    if concepts:
        out.append({
            "topic": topic, "difficulty": "Easy", "kind": "definition",
            "question": f"Define '{concepts[0]}' and describe its role within {topic}.",
            "expected_keywords": _kw([concepts[0]] + concepts[1:3] + [topic]),
        })
    if len(concepts) >= 2:
        out.append({
            "topic": topic, "difficulty": "Medium", "kind": "concept",
            "question": f"Explain how {concepts[1]} contributes to {topic}.",
            "expected_keywords": _kw([concepts[1], concepts[0]] + concepts[2:3]),
        })
    if concepts:
        out.append({
            "topic": topic, "difficulty": "Medium", "kind": "process",
            "question": f"Describe the process involving {concepts[0]} within {topic}.",
            "expected_keywords": _kw([concepts[0], topic] + concepts[1:2]),
        })
    if concepts:
        out.append({
            "topic": topic, "difficulty": "Hard", "kind": "scenario",
            "question": (f"Apply your understanding of {concepts[0]} to a biological "
                         f"scenario involving {topic}."),
            "expected_keywords": _kw([concepts[0], topic] + concepts[1:2]),
        })
    if prereqs:
        out.append({
            "topic": topic, "difficulty": "Hard", "kind": "relationship",
            "question": f"Explain the relationship between {topic} and {prereqs[0]}.",
            "expected_keywords": _kw([prereqs[0], topic] + concepts[:2]),
        })
    if len(concepts) >= 2:
        out.append({
            "topic": topic, "difficulty": "Hard", "kind": "cause_effect",
            "question": f"Explain how a change in {concepts[0]} affects {topic}.",
            "expected_keywords": _kw([concepts[0], topic] + concepts[1:2]),
        })
    return out


def generate_questions(sections, min_q: int = 7, max_q: int = 15) -> list:
    """Generate 7-15 diagnostic questions, progressively harder, with marks.

    Each question: {id, topic, question, difficulty, marks, expected_keywords}.
    Deterministic per document (stable across reruns). Swap point for a
    Fireworks question-generation call later — same return shape.
    """
    if not sections:
        return []
    rng = random.Random(_plan_seed(sections))

    candidates = []
    for sec in sections:
        candidates.extend(_question_bank_for_section(sec))

    # de-duplicate by question text
    seen, uniq = set(), []
    for c in candidates:
        if c["question"] in seen:
            continue
        seen.add(c["question"])
        uniq.append(c)

    target = min(max_q, max(min_q, round(len(sections) * 1.8)))

    # bucket by difficulty, then spread topics within each bucket (round-robin)
    buckets = {"Easy": [], "Medium": [], "Hard": []}
    for c in uniq:
        buckets[c["difficulty"]].append(c)

    def _spread(lst):
        by_topic = {}
        for c in lst:
            by_topic.setdefault(c["topic"], []).append(c)
        topics = list(by_topic)
        rng.shuffle(topics)
        out, i = [], 0
        while any(by_topic.values()) and i < 10000:
            t = topics[i % len(topics)]
            if by_topic[t]:
                out.append(by_topic[t].pop(0))
            i += 1
        return out

    for k in buckets:
        buckets[k] = _spread(buckets[k])

    # target distribution ~ 20% Easy / 40% Medium / 40% Hard (progressive)
    n_easy = max(1, round(target * 0.2))
    n_hard = max(1, round(target * 0.4))
    n_med = max(1, target - n_easy - n_hard)
    want = {"Easy": n_easy, "Medium": n_med, "Hard": n_hard}

    selected = []
    for diff in ("Easy", "Medium", "Hard"):
        selected.extend(buckets[diff][:want[diff]])

    # backfill from leftovers (hardest first) if any bucket ran short
    leftovers = []
    for diff in ("Hard", "Medium", "Easy"):
        leftovers.extend(buckets[diff][want[diff]:])
    for c in leftovers:
        if len(selected) >= target:
            break
        selected.append(c)

    # pad with generic (unique) questions if still under the minimum
    idx = 0
    while len(selected) < min_q:
        sec = sections[idx % len(sections)]
        idx += 1
        selected.append({
            "topic": sec.get("title", "Topic"), "difficulty": "Medium",
            "kind": "summary",
            "question": f"Summarise the main ideas of {sec.get('title', 'Topic')} (part {idx}).",
            "expected_keywords": _kw(sec.get("key_concepts", [])[:3] + [sec.get("title", "")]),
        })

    selected = selected[:max_q]

    # progressive difficulty ordering (Easy -> Medium -> Hard)
    selected.sort(key=lambda c: DIFFICULTY_RANK.get(c["difficulty"], 2))

    out = []
    for i, c in enumerate(selected, 1):
        marks = rng.choice(MARKS_BY_DIFFICULTY.get(c["difficulty"], [3, 4]))
        out.append({
            "id": f"q{i}",
            "topic": c["topic"],
            "question": c["question"],
            "difficulty": c["difficulty"],
            "marks": marks,
            "expected_keywords": c["expected_keywords"] or _kw([c["topic"]]),
        })
    return out


# ===========================================================================
# Diagnostic — answer evaluation (keyword coverage, NOT answer length)
# ===========================================================================
def evaluate_answer(question, answer) -> dict:
    """Concept-based marking (never length-based).

    Scores via calculate_semantic_similarity() against the expected answer and
    keywords, then reports correct concepts, missing concepts, misconceptions
    and an improvement suggestion.
    """
    expected_kw = [k.lower() for k in question.get("expected_keywords", []) if k]
    expected_answer = question.get("expected_answer", "")
    marks = question.get("marks", 5)
    text = (answer or "").strip()

    if not text:
        return {
            "score": 0, "coverage": 0.0, "similarity": 0.0,
            "matched": [], "missing": expected_kw,
            "strengths": [], "weaknesses": expected_kw,
            "correct_concepts": [], "missing_concepts": expected_kw,
            "misconceptions": [],
            "improvement": "Attempt the question — start from the key definitions.",
            "feedback": "No answer submitted. Revise this topic from the fundamentals.",
        }

    sim = calculate_semantic_similarity(text, expected_answer, expected_kw)
    matched, missing = sim["matched"], sim["missing"]
    similarity = sim["similarity"]

    score = round(similarity * marks)
    if matched and score == 0:
        score = 1
    score = max(0, min(marks, score))

    misconceptions = _detect_misconceptions(text, question)
    improvement = _improvement_suggestion(missing, question)
    return {
        "score": score, "coverage": round(sim["coverage"], 2),
        "similarity": round(similarity, 2),
        "matched": matched, "missing": missing,
        "strengths": matched, "weaknesses": missing,
        "correct_concepts": matched, "missing_concepts": missing,
        "misconceptions": misconceptions, "improvement": improvement,
        "feedback": generate_feedback(score, marks, matched, missing,
                                      misconceptions, improvement),
    }


def evaluate_diagnostic(questions, answers) -> tuple:
    """Evaluate every answer and compute per-topic mastery. Pure orchestration."""
    results = {}
    for q in questions:
        results[q["id"]] = evaluate_answer(q, answers.get(q["id"], ""))
    mastery = calculate_mastery(questions, results)
    return results, mastery


def calculate_mastery(questions, results) -> dict:
    """Per-topic mastery = sum(earned marks) / sum(available marks)."""
    earned, total = {}, {}
    for q in questions:
        t = q["topic"]
        earned[t] = earned.get(t, 0) + results.get(q["id"], {}).get("score", 0)
        total[t] = total.get(t, 0) + q["marks"]
    return {t: (earned[t] / total[t] if total[t] else 0.0) for t in total}


# ===========================================================================
# AI / COMPUTE LAYER  (kept out of the Streamlit pages)
# ---------------------------------------------------------------------------
# Two-layer design so compute can later move to local AMD ROCm hardware:
#   Layer 1 (local / AMD): PDF parsing, chunking, embeddings, knowledge map,
#            dependency graph, semantic-similarity scoring.
#   Layer 2 (Fireworks AI): exam-question generation, expected answers,
#            feedback, study recommendations.
# Every Fireworks call lives in a dedicated helper so the UI never changes if
# the provider (or the local model) is swapped later.
# ===========================================================================

# Multi-word heading phrases that must never appear anywhere in a question.
_HARD_FORMATTING = {
    "learning objectives", "learning objective", "quick check", "key points",
    "key point", "why this matters", "table of contents", "references",
    "recap", "checklist", "heading", "section", "topic", "summary",
}
# Single words that are only invalid when they are the SUBJECT of the question
# (e.g. "Define Example."), not when used naturally ("give a worked example").
_SOFT_FORMATTING = {
    "example", "examples", "summary", "overview", "introduction", "notes",
    "note", "objectives", "objective", "contents", "reference", "knowing",
    "aims",
}
FORMATTING_STOPWORDS = _HARD_FORMATTING | _SOFT_FORMATTING


# --- Layer 1: local / AMD-ready compute -----------------------------------
def chunk_document(text, chunk_size: int = 800, overlap: int = 100) -> list:
    """Layer-1 (local/AMD): split raw text into overlapping chunks for embedding.

    Pure and UI-independent. A ROCm embedding job can consume these chunks.
    """
    text = text or ""
    chunks, i = [], 0
    step = max(1, chunk_size - overlap)
    while i < len(text):
        piece = text[i:i + chunk_size]
        if piece.strip():
            chunks.append(piece)
        i += step
    return chunks


def generate_embeddings(chunks, dim: int = 64, model=None) -> list:
    """Layer-1 (local/AMD ROCm) embedding interface — dependency-free placeholder.

    Returns one deterministic bag-of-words vector per chunk so downstream code
    has a stable interface. Swap this body for a local ROCm embedding model, or
    load a precomputed embeddings.npy, without changing any caller.
    """
    vectors = []
    for ch in chunks:
        vec = [0.0] * dim
        for w in re.findall(r"[a-z][a-z\-]{2,}", (ch or "").lower()):
            if w in _STOPWORDS:
                continue
            vec[hash(w) % dim] += 1.0
        norm = sum(x * x for x in vec) ** 0.5 or 1.0
        vectors.append([x / norm for x in vec])
    return vectors


def build_knowledge_graph(sections) -> dict:
    """Layer-1: topic dependency graph (title -> [prerequisite titles]).

    Reads the already-extracted prerequisites; kept separate from the
    heavier build_topic_graph() so the AMD layer can regenerate it later.
    """
    return {s.get("title", ""): list(s.get("prerequisites", [])) for s in sections}


def _lexical_overlap(a: str, b: str) -> float:
    """Recall of the expected answer's content words present in the student text."""
    aw = {w for w in re.findall(r"[a-z][a-z\-]{2,}", (a or "").lower()) if w not in _STOPWORDS}
    bw = {w for w in re.findall(r"[a-z][a-z\-]{2,}", (b or "").lower()) if w not in _STOPWORDS}
    if not bw:
        return 0.0
    return len(aw & bw) / len(bw)


def calculate_semantic_similarity(student_answer, expected_answer, expected_keywords=None) -> dict:
    """Layer-1 (local/AMD) semantic-marking interface.

    Modular swap point: later this will embed both answers with a local ROCm
    model and return cosine similarity. For now it blends keyword coverage with
    lexical overlap against the expected answer. Never uses answer length.
    Returns {similarity, coverage, matched, missing, overlap}.
    """
    text = (student_answer or "").lower()
    expected_keywords = [k.lower() for k in (expected_keywords or []) if k]

    if expected_keywords:
        matched = [k for k in expected_keywords if k in text]
        missing = [k for k in expected_keywords if k not in text]
        coverage = len(matched) / len(expected_keywords)
    else:
        matched, missing, coverage = [], [], 0.0

    overlap = _lexical_overlap(text, expected_answer or "")
    similarity = (0.75 * coverage + 0.25 * overlap) if expected_keywords else overlap
    return {"similarity": similarity, "coverage": coverage,
            "matched": matched, "missing": missing, "overlap": round(overlap, 2)}


# --- Layer 1: knowledge map extraction + export ---------------------------
def _definitions_from_section(section) -> list:
    """Pull likely definition sentences ('X is/are/refers to ...') from a section."""
    body = section.get("_body") or " ".join(section.get("learning_objectives", [])) or section.get("summary", "")
    defs = []
    for s in _sentences(body):
        if re.search(r"\b(is|are|refers to|means|defined as)\b", s.lower()):
            defs.append(s.strip())
        if len(defs) >= 4:
            break
    return defs


def extract_knowledge_map(sections) -> dict:
    """Layer-1: structured, serialisable knowledge map built from the notes.

    This is the same shape an AMD ROCm notebook will later emit as
    knowledge_map.json, so the UI can consume either source unchanged.
    """
    topics = []
    for s in sections:
        topics.append({
            "title": s.get("title", ""),
            "summary": s.get("summary", ""),
            "key_concepts": s.get("key_concepts", []),
            "definitions": _definitions_from_section(s),
            "learning_objectives": s.get("learning_objectives", []),
            "biological_processes": [c for c in s.get("key_concepts", [])
                                     if re.search(r"(sis|tion|lysis|olysis)$", c.lower())],
            "relationships": s.get("prerequisites", []),
            "prerequisites": s.get("prerequisites", []),
            "example_applications": [o for o in s.get("learning_objectives", [])
                                     if "example" in o.lower()],
            "estimated_study_time": s.get("estimated_study_time", ""),
        })
    return {"topics": topics, "generated": time.time(), "source": "local"}


def export_knowledge_map(sections) -> str:
    """Serialise the knowledge map to a JSON string (for knowledge_map.json)."""
    return json.dumps(extract_knowledge_map(sections), indent=2, ensure_ascii=False)


def load_knowledge_map(path_or_json: str):
    """Load a knowledge map from a JSON file path or a JSON string.

    Lets a future AMD notebook's knowledge_map.json drop straight into the app.
    """
    try:
        if os.path.exists(path_or_json):
            with open(path_or_json, encoding="utf-8") as fh:
                return json.load(fh)
        return json.loads(path_or_json)
    except Exception as exc:
        print(f"[Rebound] load_knowledge_map failed: {exc}")
        return None


def load_precomputed_artifacts(folder: str = ".") -> dict:
    """Future AMD-notebook integration point.

    Loads knowledge_map.json / metadata.json / embeddings.npy from `folder`
    if present. Returns only what exists; the UI works with or without them.
    """
    out = {}
    km = os.path.join(folder, "knowledge_map.json")
    if os.path.exists(km):
        out["knowledge_map"] = load_knowledge_map(km)
    meta = os.path.join(folder, "metadata.json")
    if os.path.exists(meta):
        try:
            with open(meta, encoding="utf-8") as fh:
                out["metadata"] = json.load(fh)
        except Exception as exc:
            print(f"[Rebound] metadata.json load failed: {exc}")
    emb = os.path.join(folder, "embeddings.npy")
    if os.path.exists(emb):
        try:
            import numpy as _np  # optional dependency
            out["embeddings"] = _np.load(emb)
        except Exception as exc:
            print(f"[Rebound] embeddings.npy load failed: {exc}")
    return out


# --- Layer 2: Fireworks AI exam generation --------------------------------
def _exam_system_prompt() -> str:
    """System behaviour for the Fireworks Biology-examiner model."""
    return (
        "You are an experienced Cambridge IGCSE and A-Level Biology examiner. "
        "Your task is to generate a diagnostic assessment from the uploaded "
        "revision notes. The assessment is designed to identify weaknesses "
        "before generating an adaptive study plan. Generate between 7 and 15 "
        "written-response questions. Prioritize: core biological concepts, "
        "definitions, biological processes, relationships, cause and effect, "
        "comparisons, application, scenario-based, data-interpretation and process-description questions. Avoid questions based on "
        "document headings or formatting (never ask about 'Learning Objectives', "
        "'Example', 'Quick Check', 'Key Points', 'Summary', 'References'). "
        "Questions should resemble real Biology examination questions. "
        "Difficulty should gradually increase throughout the assessment. Assign "
        "marks by complexity: 2 = simple definition, 3 = short explanation, "
        "4 = comparison / process / cause-and-effect, 5 = application / reasoning. "
        "The expected_answer and keywords MUST come from the notes; do not invent "
        "content. Return ONLY valid JSON with this exact schema: "
        '{"questions":[{"topic":"","difficulty":"Easy|Medium|Hard","marks":0,'
        '"question":"","expected_answer":"","keywords":[],"rationale":""}]}'
    )


def _knowledge_map_payload(sections) -> list:
    """Compact knowledge map sent to Fireworks (never the raw PDF)."""
    payload = []
    for s in sections:
        payload.append({
            "topic": s.get("title", ""),
            "summary": s.get("summary", ""),
            "key_concepts": s.get("key_concepts", []),
            "learning_objectives": s.get("learning_objectives", []),
            "prerequisites": s.get("prerequisites", []),
        })
    return payload


def _norm_difficulty(value) -> str:
    v = str(value or "").strip().lower()
    if v.startswith("e"):
        return "Easy"
    if v.startswith("h"):
        return "Hard"
    return "Medium"


def _norm_marks(value, difficulty) -> int:
    try:
        m = int(round(float(value)))
    except Exception:
        m = 0
    if m in (2, 3, 4, 5):
        return m
    return {"Easy": 2, "Medium": 4, "Hard": 5}[_norm_difficulty(difficulty)]


def _mark_scheme(keywords: list, marks: int, expected_answer: str = "") -> list:
    """Build a simple points-based mark scheme from the expected keywords."""
    pts = [f"1 mark: correctly references '{k}'." for k in keywords[:marks]]
    if not pts and expected_answer:
        pts.append(f"{marks} marks: answer matches the expected response.")
    while len(pts) < min(marks, max(1, len(keywords) or 1)):
        pts.append("1 mark: relevant supporting detail / correct terminology.")
    return pts[:marks]


def is_valid_exam_question(q) -> bool:
    """Quality filter — reject formatting-derived or too-thin questions.

    Heading words are matched as whole words (so 'dissection' is not rejected
    for containing 'section'); single soft words are rejected only when they
    are the SUBJECT of the question.
    """
    if not isinstance(q, dict):
        return False
    question = str(q.get("question", "")).strip()
    if len(question) < 12:
        return False
    low = question.lower()
    topic = str(q.get("topic", "")).strip().lower()

    for bad in _HARD_FORMATTING:
        if re.search(rf"\b{re.escape(bad)}\b", low) or bad == topic:
            return False
    for bad in _SOFT_FORMATTING:
        if bad == topic:
            return False
        if re.search(rf"\b(define|explain|describe|state|outline|what\s+is|what\s+are)\b[\s'\"]+{re.escape(bad)}\b", low):
            return False

    kw = [str(k).strip().lower() for k in q.get("keywords", q.get("expected_keywords", []))
          if str(k).strip()]
    bio_kw = [k for k in kw if k not in FORMATTING_STOPWORDS]
    if len(bio_kw) >= 2:
        return True
    if len(bio_kw) == 1 and str(q.get("expected_answer", "")).strip():
        return True
    return False


def parse_fireworks_exam_response(payload, sections=None) -> list:
    """Validate + normalise Fireworks exam JSON into UI-ready questions.

    Adds ids, lowercase expected_keywords, a mark scheme, and semantic concepts.
    Orders questions progressively by difficulty.
    """
    raw = payload.get("questions", []) if isinstance(payload, dict) else []
    cleaned = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        q = {
            "topic": str(item.get("topic", "")).strip() or "General",
            "difficulty": _norm_difficulty(item.get("difficulty", "Medium")),
            "marks": _norm_marks(item.get("marks"), item.get("difficulty", "Medium")),
            "question": str(item.get("question", "")).strip(),
            "expected_answer": str(item.get("expected_answer", "")).strip(),
            "keywords": [str(k).strip() for k in item.get("keywords", []) if str(k).strip()],
            "mark_scheme": [str(m).strip() for m in item.get("mark_scheme", []) if str(m).strip()],
            "semantic_concepts": [str(c).strip() for c in item.get("semantic_concepts", []) if str(c).strip()],
            "rationale": str(item.get("rationale", "")).strip(),
        }
        if is_valid_exam_question(q):
            cleaned.append(q)

    cleaned.sort(key=lambda q: DIFFICULTY_RANK.get(q["difficulty"], 2))
    final = []
    for i, q in enumerate(cleaned, 1):
        q["id"] = f"q{i}"
        q["expected_keywords"] = [k.lower() for k in q["keywords"]] or _kw([q["topic"]])
        if not q["mark_scheme"]:
            q["mark_scheme"] = _mark_scheme(q["expected_keywords"], q["marks"], q["expected_answer"])
        if not q["semantic_concepts"]:
            q["semantic_concepts"] = q["expected_keywords"]
        if not q["rationale"]:
            q["rationale"] = (f"Assesses understanding of {q['topic']}, "
                              "a core concept and prerequisite for later topics.")
        q["_source"] = "fireworks-api"
        final.append(q)
    return final


def _expected_answer_from_notes(section, keywords) -> str:
    """Draw an expected answer straight from the notes (no hallucination)."""
    body = section.get("_body") or section.get("summary", "")
    kws = [k.lower() for k in keywords]
    picked = [s for s in _sentences(body) if any(k in s.lower() for k in kws)]
    ans = " ".join(picked[:2]) if picked else (section.get("summary", "") or body[:200])
    return ans.strip()[:400]


def _local_exam_fallback(sections, min_q: int = 7, max_q: int = 15) -> list:
    """Quality-filtered local generator used when DEBUG_OFFLINE is enabled.

    Grounds every question with an expected answer/keywords/mark-scheme from
    the notes, applies the quality filter, and tops up to `min_q`.
    """
    base = generate_questions(sections, min_q=max_q, max_q=max_q)
    by_title = {s.get("title", ""): s for s in sections}
    out, seen = [], set()
    for q in base:
        sec = by_title.get(q["topic"], {})
        kws = q["expected_keywords"]
        item = {
            "id": q["id"], "topic": q["topic"], "difficulty": q["difficulty"],
            "marks": q["marks"], "question": q["question"],
            "expected_answer": _expected_answer_from_notes(sec, kws),
            "keywords": kws, "expected_keywords": kws,
            "mark_scheme": _mark_scheme(kws, q["marks"], _expected_answer_from_notes(sec, kws)),
            "semantic_concepts": kws,
            "rationale": (f"Targets {', '.join(kws[:2]) or q['topic']} "
                          f"within {q['topic']} — a key idea drawn from your notes."),
            "_source": "local-fallback",
        }
        if is_valid_exam_question(item) and item["question"] not in seen:
            seen.add(item["question"])
            out.append(item)

    for sec in sections:
        if len(out) >= min_q:
            break
        concepts = [c for c in sec.get("key_concepts", []) if c and c != "general principles"]
        if not concepts:
            continue
        kws = [c.lower() for c in concepts[:3]]
        item = {
            "topic": sec.get("title", "Topic"), "difficulty": "Medium", "marks": 3,
            "question": (f"Outline the main biological ideas of {sec.get('title', 'this area')} "
                         f"and describe how {concepts[0]} functions."),
            "expected_answer": _expected_answer_from_notes(sec, kws),
            "keywords": kws, "expected_keywords": kws,
            "mark_scheme": _mark_scheme(kws, 3, _expected_answer_from_notes(sec, kws)),
            "semantic_concepts": kws,
            "rationale": f"Ensures coverage of {sec.get('title', '')} across the assessment.",
            "_source": "local-fallback",
        }
        if is_valid_exam_question(item) and item["question"] not in seen:
            seen.add(item["question"])
            out.append(item)

    out.sort(key=lambda q: DIFFICULTY_RANK.get(q["difficulty"], 2))
    for i, q in enumerate(out, 1):
        q["id"] = f"q{i}"
    return out[:max_q]


def generate_exam_questions(document_sections, min_q: int = 7, max_q: int = 15) -> list:
    """Layer-2 exam generation from the structured knowledge map (7-15 Qs).

    Sends the knowledge map (not the raw PDF) to the Fireworks Biology examiner
    model. Prints the active model. On error the real exception is raised
    (surfaced to the UI) unless DEBUG_OFFLINE is set, in which case a local
    quality-filtered paper is used.
    """
    sections = document_sections or []
    if not sections:
        return []
    print(f"[Rebound] Fireworks Model: {FIREWORKS_CHAT_MODEL}")

    if OpenAI is None:
        if DEBUG_OFFLINE:
            print("[Rebound] DEBUG_OFFLINE: local exam fallback.")
            return _local_exam_fallback(sections, min_q, max_q)
        raise RuntimeError("openai SDK not installed. Run: pip install -r requirements.txt")

    try:
        client = OpenAI(api_key=_get_fireworks_api_key(), base_url=FIREWORKS_BASE_URL)
        kmap = _knowledge_map_payload(sections)
        response = client.chat.completions.create(
            model=FIREWORKS_CHAT_MODEL,
            response_format={"type": "json_object"},
            temperature=0.4,
            messages=[
                {"role": "system", "content": _exam_system_prompt()},
                {"role": "user",
                 "content": "Knowledge map (JSON):\n" + json.dumps(kmap)[:_FIREWORKS_MAX_CHARS]},
            ],
        )
        payload = json.loads(response.choices[0].message.content)
        questions = parse_fireworks_exam_response(payload, sections)
        if len(questions) < min_q:
            raise ValueError(f"only {len(questions)} valid questions returned (need >= {min_q}).")
        print(f"[Rebound] Questions generated: {len(questions)}")
        return questions[:max_q]
    except Exception as exc:
        print(f"[Rebound] Exam generation error: {exc}")
        if DEBUG_OFFLINE:
            print("[Rebound] DEBUG_OFFLINE: local exam fallback.")
            return _local_exam_fallback(sections, min_q, max_q)
        raise


_CONFUSION_PAIRS = [
    ("mitosis", "meiosis"), ("aerobic", "anaerobic"), ("dna", "rna"),
    ("prokaryotic", "eukaryotic"), ("photosynthesis", "respiration"),
    ("artery", "vein"), ("diffusion", "osmosis"), ("mitochondria", "chloroplast"),
]


def _detect_misconceptions(text: str, question: dict) -> list:
    """Flag likely concept confusions (e.g. mitosis vs meiosis)."""
    t = (text or "").lower()
    exp = (str(question.get("expected_answer", "")) + " "
           + " ".join(question.get("expected_keywords", []))).lower()
    out = []
    for a, b in _CONFUSION_PAIRS:
        if re.search(rf"\b{a}\b", t) and a not in exp and b in exp:
            out.append(f"You mentioned '{a}', but this concerns '{b}'.")
        elif re.search(rf"\b{b}\b", t) and b not in exp and a in exp:
            out.append(f"You mentioned '{b}', but this concerns '{a}'.")
    return out[:2]


def _improvement_suggestion(missing: list, question: dict) -> str:
    """Actionable next step for the student."""
    if not missing:
        return "Strong answer — refine with precise terminology and an example."
    return (f"Revise {', '.join(missing[:3])} and link them explicitly to "
            f"{question.get('topic', 'the topic')}.")


def generate_feedback(score, marks, matched, missing, misconceptions=None, improvement="") -> str:
    """Feedback: score, correct concepts, missing concepts, misconceptions, improvement."""
    parts = [f"Score {score}/{marks}."]
    if matched:
        parts.append(f"Correct concepts: {', '.join(matched)}.")
    if missing:
        parts.append(f"Missing concepts: {', '.join(missing)}.")
    if misconceptions:
        parts.append("Misconceptions: " + " ".join(misconceptions))
    if improvement:
        parts.append(f"Improve: {improvement}")
    if not missing and matched and not misconceptions:
        parts.append("Excellent — all key concepts addressed.")
    return " ".join(parts)


def calculate_topic_mastery(questions, results) -> dict:
    """Per-topic mastery (spec alias of calculate_mastery)."""
    return calculate_mastery(questions, results)


# --- Adaptive study planner helpers ---------------------------------------
# All planner calculations live in these functions so the UI stays thin.
EXAM_WEIGHT_PLACEHOLDER = 0.8  # later this will come from AI


def _is_prerequisite(topic: str, prerequisites: dict) -> bool:
    """True if `topic` is a prerequisite for any other topic."""
    return any(topic in prereqs for prereqs in prerequisites.values())


def _dependents_of(topic: str, prerequisites: dict) -> list[str]:
    """Topics that depend on `topic`."""
    return [dep for dep, prereqs in prerequisites.items() if topic in prereqs]


def topic_difficulty_map(sections) -> dict:
    """Map each section title to its difficulty rank (1..3)."""
    return {s["title"]: DIFFICULTY_RANK.get(s.get("estimated_difficulty", "Medium"), 2)
            for s in sections}


def calculate_priority(topic, mastery, prerequisites, difficulty_rank=2,
                       exam_weight=EXAM_WEIGHT_PLACEHOLDER) -> float:
    """Priority from mastery, dependency, difficulty and exam importance.

    Poor mastery / high dependency / high difficulty -> higher priority.
    """
    prereq_w = 1.0 if _is_prerequisite(topic, prerequisites) else 0.5
    diff_w = difficulty_rank / 3.0
    return round(
        (1 - mastery) * 0.5 + prereq_w * 0.2 + diff_w * 0.2 + exam_weight * 0.1, 3
    )


def compute_priority_score(topic: str, mastery: float, prerequisites: dict) -> float:
    """Backward-compatible priority score (kept so older callers keep working)."""
    prerequisite_weight = 1.0 if _is_prerequisite(topic, prerequisites) else 0.5
    return (
        (1 - mastery) * 0.6
        + prerequisite_weight * 0.3
        + EXAM_WEIGHT_PLACEHOLDER * 0.1
    )


def priority_label(score: float) -> str:
    """Convert a priority score into a label."""
    if score >= 0.66:
        return "High"
    if score >= 0.45:
        return "Medium"
    return "Low"


def duration_for_mastery(mastery: float) -> int:
    """Adaptive session duration (minutes) based on mastery."""
    if mastery < 0.40:
        return 90
    if mastery <= 0.60:
        return 60
    if mastery <= 0.80:
        return 45
    return 30


def _reason(topic, mastery, prerequisites) -> str:
    """Human-readable explanation for scheduling this topic."""
    deps = _dependents_of(topic, prerequisites)
    if mastery < 0.40:
        base = f"Low mastery ({mastery:.0%}) — needs the most work"
    elif mastery <= 0.80:
        base = f"Medium mastery ({mastery:.0%})"
    else:
        base = f"High mastery ({mastery:.0%}) — light revision only"
    return f"{base} and prerequisite for {', '.join(deps)}." if deps else f"{base}."


def format_date(d) -> str:
    """Format a date as e.g. '17 Jul 2026'."""
    return d.strftime("%d %b %Y")


def _order_with_prerequisites(topics: list[str], prerequisites: dict) -> list[str]:
    """Topologically order topics so prerequisites come before dependents."""
    ordered: list[str] = []
    remaining = list(topics)
    while remaining:
        progressed = False
        for topic in list(remaining):
            prereqs = prerequisites.get(topic, [])
            if all(p in ordered or p not in remaining for p in prereqs):
                ordered.append(topic)
                remaining.remove(topic)
                progressed = True
        if not progressed:  # cycle — keep whatever order is left
            ordered.extend(remaining)
            break
    return ordered


def generate_study_plan(topics, mastery_scores, prerequisites, exam_date=None,
                        daily_study_time=2.0, topic_difficulty=None,
                        start_date=None) -> list:
    """Build an adaptive, calendar-dated study schedule (max 7 days).

    Poor mastery -> higher priority, longer duration, earlier day.
    High mastery -> shorter revision, later day.
    """
    topic_difficulty = topic_difficulty or {}
    start_date = start_date or date.today()
    daily_minutes = int(daily_study_time * 60)

    ordered = sorted(
        topics,
        key=lambda t: calculate_priority(
            t, mastery_scores.get(t, 0.0), prerequisites,
            topic_difficulty.get(t, 2)),
        reverse=True,
    )
    ordered = _order_with_prerequisites(ordered, prerequisites)

    sessions = []
    for topic in ordered:
        mastery = mastery_scores.get(topic, 0.0)
        score = calculate_priority(topic, mastery, prerequisites,
                                   topic_difficulty.get(topic, 2))
        sessions.append({
            "topic": topic,
            "duration": duration_for_mastery(mastery),
            "priority": priority_label(score),
            "priority_score": score,
            "mastery": mastery,
            "reason": _reason(topic, mastery, prerequisites),
        })

    plan, day, minutes_used = [], 1, 0
    for s in sessions:
        if minutes_used + s["duration"] > daily_minutes and minutes_used > 0:
            day += 1
            minutes_used = 0
        if day > 7:
            break
        d = start_date + timedelta(days=day - 1)
        plan.append({"day": day, "date": d.isoformat(),
                     "date_label": format_date(d), **s})
        minutes_used += s["duration"]
    return plan


def plan_progress(plan, session_status) -> dict:
    """Compute completion / remaining workload from per-session status."""
    total = len(plan)
    completed = sum(1 for s in plan if session_status.get(s["topic"]) == "completed")
    skipped = sum(1 for s in plan if session_status.get(s["topic"]) == "skipped")
    remaining_min = sum(s["duration"] for s in plan
                        if session_status.get(s["topic"]) not in ("completed", "skipped"))
    pct = completed / total if total else 0.0
    return {"total": total, "completed": completed, "skipped": skipped,
            "remaining_minutes": remaining_min, "pct": pct}


def reschedule_session(plan, topic, new_day, start_date) -> list:
    """Move one topic's session to new_day, recomputing its calendar date."""
    new_plan = []
    for s in plan:
        if s["topic"] == topic:
            d = start_date + timedelta(days=new_day - 1)
            s = {**s, "day": new_day, "date": d.isoformat(),
                 "date_label": format_date(d)}
        new_plan.append(s)
    return sorted(new_plan, key=lambda s: s["day"])


# --- Adaptive Recovery Engine ----------------------------------------------
# Pure functions, no Streamlit calls. These are the swap points for LLM
# reasoning or AMD embedding similarity later — the UI won't need to change.
REMAINING_DAYS_WEIGHT_PLACEHOLDER = 0.8

# Compression table: original duration -> compressed duration (minutes)
COMPRESSED_DURATION = {90: 60, 60: 45, 45: 30, 30: 15}

DECISION_BADGES = {
    "Protected": "🟢",
    "Compressed": "🟡",
    "Moved": "🔵",
    "Dropped": "🔴",
}


def calculate_recovery_priority(topic, mastery_scores, prerequisites) -> float:
    """Recovery priority in ~0..1. Placeholder heuristic."""
    mastery = mastery_scores.get(topic, 0.0)
    dependency_weight = 1.0 if _is_prerequisite(topic, prerequisites) else 0.5
    return (
        (1 - mastery) * 0.5
        + dependency_weight * 0.3
        + REMAINING_DAYS_WEIGHT_PLACEHOLDER * 0.2
    )


def calculate_confidence(priority, decision) -> int:
    """Confidence (%) for a decision. Placeholder heuristic."""
    base = {"Protected": 78, "Compressed": 74, "Moved": 70, "Dropped": 72}[decision]
    signal = priority if decision in ("Protected", "Moved") else 1 - priority
    return int(min(99, base + signal * 25))


def compress_session(session) -> dict:
    """Return a copy of the session with reduced duration (90→60→45→30→15)."""
    compressed = dict(session)
    compressed["duration"] = COMPRESSED_DURATION.get(
        session["duration"], max(15, session["duration"] // 2)
    )
    return compressed


def move_session(session) -> dict:
    """Return a copy of the session flagged to be scheduled later."""
    moved = dict(session)
    moved["deferred"] = True
    return moved


def drop_session(session) -> None:
    """Dropped sessions are removed from the schedule entirely."""
    return None


def make_recovery_decision(session, mastery_scores, prerequisites) -> dict:
    """Decide Protected / Compressed / Moved / Dropped for one topic."""
    topic = session["topic"]
    mastery = mastery_scores.get(topic, 0.0)
    dependents = _dependents_of(topic, prerequisites)
    dependency_weight = 1.0 if dependents else 0.5
    priority = calculate_recovery_priority(topic, mastery_scores, prerequisites)

    if mastery > 0.8 and not dependents:
        decision = "Dropped"
        reason = "High mastery and low dependency."
        rule = f"Dropped because mastery is high ({mastery:.0%}) and no topic depends on {topic}."
    elif dependents:
        decision = "Protected"
        reason = f"Prerequisite for {', '.join(dependents)}."
        rule = (
            f"Protected because {', '.join(dependents)} depend(s) on {topic}"
            + (f" and mastery is low ({mastery:.0%})." if mastery < 0.4 else ".")
        )
    elif mastery < 0.4:
        decision = "Protected"
        reason = "Very low mastery."
        rule = f"Protected because mastery is very low ({mastery:.0%})."
    elif mastery > 0.6:
        decision = "Compressed"
        reason = "Already mastered. Quick revision is sufficient."
        rule = f"Compressed because mastery is high ({mastery:.0%}); a shorter revision session suffices."
    else:
        decision = "Moved"
        reason = "Still important but can be delayed."
        rule = f"Moved because {topic} is important (mastery {mastery:.0%}) but not urgent."

    return {
        "topic": topic,
        "decision": decision,
        "reason": reason,
        "confidence": calculate_confidence(priority, decision),
        "priority": round(priority, 2),
        "details": {
            "mastery": mastery,
            "dependency_weight": dependency_weight,
            "priority_score": round(priority, 2),
            "remaining_days_weight": REMAINING_DAYS_WEIGHT_PLACEHOLDER,
            "rule": rule,
        },
    }


def rebuild_schedule(sessions, available_hours, start_day=1, prerequisites=None) -> list:
    """Pack sessions into days from start_day, respecting daily capacity."""
    daily_minutes = int(available_hours * 60)
    prerequisites = prerequisites or {}
    ranked = sorted(
        sessions,
        key=lambda s: (s.get("deferred", False), -s.get("recovery_priority", 0)),
    )
    ordered_topics = _order_with_prerequisites(
        [s["topic"] for s in ranked], prerequisites
    )
    by_topic = {s["topic"]: s for s in sessions}
    queue = [by_topic[t] for t in ordered_topics if t in by_topic]

    new_plan: list[dict] = []
    day, minutes_used = start_day, 0
    for session in queue:
        if minutes_used + session["duration"] > daily_minutes and minutes_used > 0:
            day += 1
            minutes_used = 0
        if day > 7:
            break
        entry = {k: v for k, v in session.items() if k != "deferred"}
        entry["day"] = day
        new_plan.append(entry)
        minutes_used += session["duration"]
    return new_plan


def recover_plan(study_plan, mastery_scores, prerequisites, missed_day,
                 available_hours) -> tuple:
    """Rebuild the schedule after a missed day (legacy engine, still available)."""
    kept = [s for s in study_plan if s["day"] < missed_day]
    remaining = [s for s in study_plan if s["day"] >= missed_day]

    ACTIONS = {
        "Protected": lambda s: dict(s),
        "Compressed": compress_session,
        "Moved": move_session,
        "Dropped": drop_session,
    }

    decisions, to_schedule, seen = [], [], set()
    for session in remaining:
        topic = session["topic"]
        if topic in seen:
            continue
        seen.add(topic)
        decision = make_recovery_decision(session, mastery_scores, prerequisites)
        decisions.append(decision)
        new_session = ACTIONS[decision["decision"]](session)
        if new_session is None:
            continue
        new_session["recovery_priority"] = decision["priority"]
        to_schedule.append(new_session)

    new_plan = kept + rebuild_schedule(
        to_schedule, available_hours, start_day=missed_day, prerequisites=prerequisites
    )
    return new_plan, decisions


# --- Recovery preview / redistribution (non-destructive) -------------------
# The new Recovery UX: mark unavailable days, preview a rebuilt plan, and only
# apply it on confirmation. Never mutates study_plan in place.
def _compress(duration) -> int:
    """Compress a single duration one step (90→60→45→30→15)."""
    return COMPRESSED_DURATION.get(duration, max(15, duration // 2))


def build_recovery_preview(plan, mastery_scores, prerequisites, unavailable_days,
                           available_hours, start_date, strategy="A") -> tuple:
    """Return (preview_plan, changes). Repacks sessions off unavailable days into
    the remaining days within capacity. Overflow strategy:
      A = rely on the (already increased) available_hours
      B = drop lowest-priority sessions
      C = compress high-mastery sessions
    Never mutates the input plan.
    """
    unavailable = set(unavailable_days)
    daily_minutes = int(available_hours * 60)

    work = []
    for s in plan:
        c = dict(s)
        c["recovery_priority"] = calculate_priority(
            c["topic"], mastery_scores.get(c["topic"], 0.0), prerequisites)
        work.append(c)

    available_days = [d for d in range(1, 8) if d not in unavailable]
    capacity = daily_minutes * len(available_days)

    # strategy C: compress high-mastery sessions up front
    if strategy == "C":
        for c in work:
            if mastery_scores.get(c["topic"], 0.0) > 0.6:
                c["duration"] = _compress(c["duration"])

    # order by priority (highest first), keep prerequisite order
    work.sort(key=lambda c: -c["recovery_priority"])
    ordered_topics = _order_with_prerequisites([c["topic"] for c in work], prerequisites)
    by_topic = {c["topic"]: c for c in work}
    queue = [by_topic[t] for t in ordered_topics]

    # strategy B: drop lowest-priority until it fits capacity
    dropped = []
    if strategy == "B":
        total = sum(c["duration"] for c in queue)
        low_first = sorted(queue, key=lambda c: c["recovery_priority"])
        while total > capacity and low_first:
            victim = low_first.pop(0)
            queue.remove(victim)
            dropped.append(victim["topic"])
            total -= victim["duration"]

    # pack into available days
    preview, changes = [], []
    di, minutes_used = 0, 0
    for c in queue:
        if di >= len(available_days):
            dropped.append(c["topic"])
            continue
        if minutes_used + c["duration"] > daily_minutes and minutes_used > 0:
            di += 1
            minutes_used = 0
            if di >= len(available_days):
                dropped.append(c["topic"])
                continue
        day = available_days[di]
        d = start_date + timedelta(days=day - 1)
        entry = {k: v for k, v in c.items() if k != "recovery_priority"}
        entry.update({"day": day, "date": d.isoformat(), "date_label": format_date(d)})
        preview.append(entry)
        minutes_used += c["duration"]

    # classify changes vs original
    orig_by_topic = {s["topic"]: s for s in plan}
    prev_by_topic = {s["topic"]: s for s in preview}
    for topic, o in orig_by_topic.items():
        r = prev_by_topic.get(topic)
        if r is None:
            changes.append({"topic": topic, "change": "removed"})
        elif r["duration"] != o["duration"]:
            changes.append({"topic": topic, "change": "compressed"})
        elif r["day"] != o["day"]:
            changes.append({"topic": topic, "change": "moved"})
        else:
            changes.append({"topic": topic, "change": "unchanged"})
    for topic in prev_by_topic:
        if topic not in orig_by_topic:
            changes.append({"topic": topic, "change": "added"})

    return sorted(preview, key=lambda s: s["day"]), changes


def estimate_impact(original, preview, changes) -> dict:
    """Summarise the preview's impact before it is applied."""
    counts = Counter(c["change"] for c in changes)
    orig_min = sum(s["duration"] for s in original)
    prev_min = sum(s["duration"] for s in preview)
    completion = max((s["day"] for s in preview), default=0)
    return {
        "moved": counts.get("moved", 0),
        "compressed": counts.get("compressed", 0),
        "removed": counts.get("removed", 0),
        "added": counts.get("added", 0),
        "unchanged": counts.get("unchanged", 0),
        "time_saved": max(0, orig_min - prev_min),
        "completion_day": completion,
        "fits": counts.get("removed", 0) == 0,
    }


def apply_recovery(preview) -> list:
    """Return the plan that should replace study_plan (UI assigns it)."""
    return [dict(s) for s in preview]


# ---------------------------------------------------------------------------
# Presentation layer — brand system, top navigation, page renderers
# ---------------------------------------------------------------------------
# Backend logic above is untouched. This layer renders + orchestrates it.

PAGES = ["Home", "Setup", "Knowledge Map", "Diagnostic", "Study Plan",
         "Recovery", "About Rebound"]   # Progress intentionally not in nav

_UI_DEFAULTS = {
    "nav_radio": "Home", "active_session": None, "diag_step": 0,
    "initial_mastery": None, "kmap_view": "Topic cards", "diag_answers": {},
    "diag_review_sel": 0, "kmap_sel_topic": None, "theme": "light",
    "week_offset": 0, "student_name": "",
}
for _k, _v in _UI_DEFAULTS.items():
    st.session_state.setdefault(_k, _v)

def _nav_to(page):
    st.session_state["_pending_nav"] = page
    st.rerun()


def _flags():
    ss = st.session_state
    return bool(ss.get("sections")), bool(ss.get("mastery_scores")), bool(ss.get("study_plan"))


def _lock_message(page):
    has_sec, has_mast, has_plan = _flags()
    if page in ("Knowledge Map", "Diagnostic") and not has_sec:
        return "Upload and analyse your notes in Setup to unlock this page."
    if page == "Study Plan" and not has_mast:
        return "Complete the diagnostic to unlock your study plan."
    if page == "Recovery" and not has_plan:
        return "Generate a study plan first to use Recovery."
    return None


_TINTS = [
    ("green", "rgba(232,247,222,.66)", "#31721f"),
    ("blue", "rgba(224,243,250,.72)", "#126f91"),
    ("amber", "rgba(255,241,211,.72)", "#9a5a08"),
    ("pink", "rgba(252,228,237,.72)", "#a52258"),
    ("purple", "rgba(237,231,251,.72)", "#5b3ca0"),
]


def _topic_tint(topic):
    stable_index = sum((index + 1) * ord(char) for index, char in enumerate(str(topic)))
    return _TINTS[stable_index % len(_TINTS)]


def _section_for(topic):
    for s in st.session_state.get("sections") or []:
        if s.get("title") == topic:
            return s
    return {}


def _key_points(topic, n=3):
    sec = _section_for(topic)
    pts = [c for c in sec.get("key_concepts", []) if c and c != "general principles"][:n]
    if not pts:
        pts = sec.get("learning_objectives", [])[:n]
    return pts


def _learning_goal(topic):
    objs = _section_for(topic).get("learning_objectives", [])
    return objs[0] if objs else f"Build a confident understanding of {topic}."


def _today_sessions(plan, status):
    today = date.today().isoformat()
    inc = [s for s in plan if status.get(s["topic"]) not in ("completed", "skipped")]
    todays = [s for s in inc if s.get("date") == today]
    if not todays and inc:
        d = min(s["day"] for s in inc)
        todays = [s for s in inc if s["day"] == d]
    return todays


def classify_topic_role(topic, graph):
    prereqs = graph.get(topic, [])
    deps = [t for t, ps in graph.items() if topic in ps]
    if not prereqs and deps:
        return "Foundation"
    if prereqs and deps:
        return "Intermediate"
    if prereqs and not deps:
        return "End"
    return "Independent"


def _mini_month_html(base, today, plan):
    import calendar
    sdays = {s["date"] for s in plan}
    cal = calendar.Calendar(firstweekday=6)
    rows = ["<table style='width:100%;border-collapse:collapse;font-size:.72rem'>",
            "<tr>" + "".join(f"<th class='rb-muted' style='font-weight:600'>{d}</th>"
                             for d in ["S", "M", "T", "W", "T", "F", "S"]) + "</tr>"]
    week = []
    for dt in cal.itermonthdates(base.year, base.month):
        instr = dt.month == base.month
        style = "padding:3px;text-align:center;border-radius:8px;"
        if dt == today:
            style += "background:var(--secondary);color:#08323c;font-weight:700;"
        elif instr and dt.isoformat() in sdays:
            style += "background:rgba(250,133,90,.18);"
        txt = str(dt.day) if instr else f"<span class='rb-muted'>{dt.day}</span>"
        week.append(f"<td style='{style}'>{txt}</td>")
        if len(week) == 7:
            rows.append("<tr>" + "".join(week) + "</tr>")
            week = []
    rows.append("</table>")
    return (f"<div class='rb-serif' style='font-size:1rem;margin-bottom:4px'>"
            f"{base.strftime('%B %Y')}</div>" + "".join(rows))


# --- distraction-free focus view -------------------------------------------
def render_focus_view():
    topic = st.session_state["active_session"]
    status = st.session_state.setdefault("session_status", {})
    _page_title("Focus session", "clock")
    with st.container(border=True):
        st.markdown(f"## {topic}")
        st.caption(f"Learning goal — {_learning_goal(topic)}")
        pts = _key_points(topic, 5)
        if pts:
            st.markdown("**Key study points**")
            for pt in pts:
                st.markdown(f"- {pt}")
        c1, c2 = st.columns([2, 3])
        if c1.button("Finish and mark complete", type="primary", key="focus_done"):
            status[topic] = "completed"
            st.session_state["session_status"] = status
            st.session_state["active_session"] = None
            st.rerun()
        if c2.button("Leave without completing", key="focus_leave"):
            st.session_state["active_session"] = None
            st.rerun()


# --- reusable session card (Home) ------------------------------------------
def render_today_session_card(session, status, all_days, expanded=False, keyprefix=""):
    topic = session["topic"]
    state = status.get(topic, "pending")
    start = date.today()
    tone, _, fg = _topic_tint(topic)
    topic_token = hashlib.sha1(str(topic).encode("utf-8")).hexdigest()[:10]
    topic_html = html.escape(str(topic))
    difficulty = _section_for(topic).get("estimated_difficulty", "")
    difficulty_html = html.escape(str(difficulty))
    with st.container(border=True, key=f"home_session_{tone}_{topic_token}"):
        st.markdown(
            "<div class='rb-home-session-top'>"
            f"<div class='rb-home-topic-icon' style='color:{fg}'>"
            f"{_icon('book', 21, fg, 1.9)}</div>"
            "<div class='rb-home-session-heading'>"
            f"<div class='rb-home-session-title' style='color:{fg}'>{topic_html}</div>"
            f"<div class='rb-home-session-meta'>{session['duration']} min"
            f"{' · ' + difficulty_html if difficulty_html else ''}</div></div>"
            "<div class='rb-home-session-badges'>"
            f"{_priority_chip(session.get('priority', 'Medium'))} {_status_chip(state)}"
            "</div></div>",
            unsafe_allow_html=True,
        )
        pts = _key_points(topic, 3 if expanded else 2)
        if pts:
            points_html = html.escape(", ".join(str(point) for point in pts))
            st.markdown(
                f"<div class='rb-home-session-points'>{points_html}</div>",
                unsafe_allow_html=True,
            )
        show = expanded or st.session_state.get(f"open_{keyprefix}{topic}", False)
        if not expanded:
            if st.button(
                "Open" if not show else "Close", key=f"tog_{keyprefix}{topic}",
                use_container_width=True,
            ):
                st.session_state[f"open_{keyprefix}{topic}"] = not show
                st.rerun()
        if show:
            if state == "pending":
                with st.container(key=f"home_actions_{topic_token}"):
                    c = st.columns(4)
                    if c[0].button(
                        "Start", type="primary", key=f"{keyprefix}start_{topic}",
                        use_container_width=True,
                    ):
                        st.session_state["active_session"] = topic
                        st.rerun()
                    if c[1].button(
                        "Complete", key=f"{keyprefix}done_{topic}", use_container_width=True
                    ):
                        status[topic] = "completed"
                        st.session_state["session_status"] = status
                        st.rerun()
                    with c[2].popover("Move"):
                        tgt = st.selectbox(
                            "Move to day", all_days,
                            format_func=lambda d: format_date(start + timedelta(days=d - 1)),
                            key=f"{keyprefix}mv_sel_{topic}",
                        )
                        if st.button(
                            "Confirm move", key=f"{keyprefix}mv_btn_{topic}",
                            use_container_width=True,
                        ):
                            st.session_state["study_plan"] = reschedule_session(
                                st.session_state["study_plan"], topic, tgt, start
                            )
                            st.rerun()
                    if c[3].button(
                        "Skip", key=f"{keyprefix}skip_{topic}", use_container_width=True
                    ):
                        status[topic] = "skipped"
                        st.session_state["session_status"] = status
                        st.rerun()
            else:
                if st.button(
                    "Reset to pending", key=f"{keyprefix}reset_{topic}",
                    use_container_width=True,
                ):
                    status.pop(topic, None)
                    st.session_state["session_status"] = status
                    st.rerun()
            with st.expander("View details"):
                st.write(f"Mastery: {session['mastery']:.0%} · Priority score: "
                         f"{session.get('priority_score', 0):.2f}")
                st.caption(session.get("reason", ""))


# ---------------------------------------------------------------------------
# Setup (split-screen)
# ---------------------------------------------------------------------------
def _run_analysis(pdf, subject, exam_date, daily):
    st.session_state["subject"] = subject
    st.session_state["exam_date"] = exam_date
    st.session_state["daily_study_time"] = daily
    st.session_state["file_name"] = pdf.name
    startt = time.perf_counter()
    with st.status("Analysing your notes...", expanded=True) as box:
        st.write("Reading PDF...")
        text = extract_pdf_text(pdf, notify=st.write)
        pages = count_pdf_pages(pdf)
        if not text.strip():
            box.update(label="No extractable text", state="error")
            st.error("Couldn't extract text (the PDF may be scanned images). Try a text-based PDF.")
            return
        st.write(f"Analysing with Fireworks ({FIREWORKS_CHAT_MODEL})...")
        try:
            raw = analyze_document_with_fireworks(text, FIREWORKS_MODEL)
        except Exception as exc:
            box.update(label="Fireworks analysis failed", state="error")
            st.error(f"Fireworks analysis failed: {exc}")
            st.info("Set DEBUG_OFFLINE=1 to use local analysis for offline development.")
            return
        sections = parse_fireworks_response(raw)
        graph = build_topic_graph(sections)
        stats = calculate_document_statistics(text, pages, sections)
        box.update(label="Analysis complete", state="complete")
    elapsed = round(time.perf_counter() - startt, 2)
    st.session_state["document_text"] = text
    st.session_state["sections"] = sections
    st.session_state["topics"] = [s["title"] for s in sections]
    st.session_state["prerequisites"] = graph
    st.session_state["doc_stats"] = stats
    st.session_state["fireworks_model"] = {"id": raw["model"], "display": raw["model_display"]}
    st.session_state["analysis_source"] = raw.get("source", "unknown")
    for k, v in {"diagnostic_questions": [], "diagnostic_results": {}, "mastery_scores": {},
                 "study_plan": [], "recovered_plan": None, "session_status": {},
                 "recovery_preview": None, "recovery_changes": [], "initial_mastery": None,
                 "diag_step": 0, "diag_answers": {}, "diag_review_sel": 0}.items():
        st.session_state[k] = v
    st.session_state["processing_summary"] = {
        "elapsed": elapsed,
        "objectives": sum(len(s["learning_objectives"]) for s in sections),
        "concepts": sum(len(s["key_concepts"]) for s in sections),
        "definitions": sum(len(s.get("definitions", [])) for s in sections),
        "relationships": sum(len(s.get("prerequisites", [])) for s in sections)}
    st.session_state["compute_status"] = {
        "provider": "Fireworks AI", "model": raw["model_display"],
        "inference_status": "Completed" if raw.get("source") == "fireworks-api" else "Local fallback",
        "analysis_time": f"{elapsed} s", "source": raw.get("source", "unknown")}
    try:
        with open("knowledge_map.json", "w", encoding="utf-8") as fh:
            fh.write(export_knowledge_map(sections))
        print("[Rebound] Knowledge map exported.")
    except Exception as exc:
        print(f"[Rebound] knowledge_map.json export failed: {exc}")
    print(f"[Rebound] Topics extracted: {len(sections)}")


def render_setup_split_layout():
    with st.container(key="setup_page"):
        left, right = st.columns([1.06, 1], gap="large", vertical_alignment="center")
        with left:
            with st.container(key="setup_intro"):
                st.markdown(
                    f"<div class='rb-setup-brand'>{render_rebound_logo()}</div>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"<div class='rb-setup-kicker'>{_icon('settings', 15, '#8a3b1e', 2.1)}"
                    "<span>Setup your exam</span></div>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    "<div class='rb-setup-hero'>Turn your notes into<br>a study plan that adapts.</div>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    "<div class='rb-setup-copy'>Upload your revision notes and we'll analyse them, "
                    "then build a personalised plan to help you recover and perform your best.</div>",
                    unsafe_allow_html=True,
                )
                features = st.columns(3, gap="medium")
                feature_content = [
                    ("upload", "mint", "#3f6b1f", "Upload notes", "Add your revision notes in PDF format."),
                    ("chart", "gold", "#8a6817", "We analyse", "Extract key topics and concepts."),
                    ("calendar", "blue", "#0d5c6e", "You rebound", "Get an adaptive plan that evolves with you."),
                ]
                for col, (icon_name, tone, colour, title, copy) in zip(features, feature_content):
                    col.markdown(
                        f"<div class='rb-setup-feature-icon {tone}'>"
                        f"{_icon(icon_name, 21, colour, 1.9)}</div>"
                        f"<div class='rb-setup-feature-title'>{title}</div>"
                        f"<div class='rb-setup-feature-copy'>{copy}</div>",
                        unsafe_allow_html=True,
                    )
        with right:
            with st.container(border=True, key="setup_form_card"):
                st.subheader("Let's set up your exam")
                st.caption("Tell us a bit about your exam and upload your notes to begin.")
                with st.form("setup_form"):
                    subject = st.selectbox("Subject", ["Biology", "Chemistry", "Physics", "Mathematics"])
                    exam_date = st.date_input("Exam date")
                    daily = st.number_input("Daily study time (hours)", 0.5, 12.0,
                                            float(st.session_state.get("daily_study_time", 2.0)), 0.5)
                    pdf = st.file_uploader("Upload notes (PDF)", type=["pdf"])
                    go = st.form_submit_button(
                        "Upload and analyse notes", type="primary", use_container_width=True
                    )
                if go:
                    if pdf is None:
                        st.warning("Please upload a PDF before analysing.")
                    else:
                        _run_analysis(pdf, subject, exam_date, daily)
                if st.session_state.get("sections"):
                    st.divider()
                    n = len(st.session_state["sections"])
                    with st.container(border=True, key="setup_success"):
                        st.markdown(
                            "<div class='rb-setup-success-row'>"
                            f"<div class='rb-setup-success-icon'>{_icon('check', 20, '#3f6b1f', 2.2)}</div>"
                            "<div class='rb-setup-success-copy'><strong>"
                            f"Analysed {n} topic{'s' if n != 1 else ''} from "
                            f"{st.session_state.get('file_name', 'your document')}.</strong></div></div>",
                            unsafe_allow_html=True,
                        )
                        st.caption("We've identified key concepts and are ready to build your plan.")
                        c1, c2 = st.columns(2)
                        if c1.button("View Knowledge Map", key="setup_kmap", use_container_width=True):
                            _nav_to("Knowledge Map")
                        if c2.button("Skip to Diagnostic", key="setup_diag", use_container_width=True):
                            _nav_to("Diagnostic")


def page_setup():
    render_setup_split_layout()


# ---------------------------------------------------------------------------
# Home
# ---------------------------------------------------------------------------
def page_home():
    _, _, has_plan = _flags()
    if not has_plan:
        with st.container(border=True, key="home_no_plan"):
            st.markdown(render_rebound_logo(), unsafe_allow_html=True)
            st.markdown("<div class='rb-hero' style='margin-top:10px'>Turn your notes into "
                        "a study plan that adapts.</div>", unsafe_allow_html=True)
            st.write("Upload your notes, complete a short diagnostic, and Rebound will build a "
                     "personalised plan around your available time.")
            if st.button("Set up my plan", type="primary", key="home_start"):
                _nav_to("Setup")
        return

    plan = st.session_state["study_plan"]
    status = st.session_state.setdefault("session_status", {})
    all_days = sorted({s["day"] for s in plan})
    todays = _today_sessions(plan, status)
    prog = plan_progress(plan, status)
    active = 1 if st.session_state.get("active_session") else 0
    planned = max(
        prog["total"] - prog["completed"] - prog.get("skipped", 0) - active,
        0,
    )
    tmin = sum(s["duration"] for s in todays)
    today_iso = date.today().isoformat()
    overdue = sum(
        1 for session in plan
        if session.get("date", today_iso) < today_iso
        and status.get(session["topic"]) not in ("completed", "skipped")
    )
    skipped = prog.get("skipped", 0)
    recovery_relevant = bool(skipped or overdue or st.session_state.get("recovery_preview"))

    with st.container(key="home_dashboard"):
        main, side = st.columns([2.6, 1], gap="large", vertical_alignment="top")
        with main:
            with st.container(key="home_main"):
                st.markdown(
                    "<div class='rb-home-study-header'>"
                    f"<div class='rb-home-heading-icon'>{_icon('calendar', 22, '#17233A', 1.9)}</div>"
                    "<div class='rb-home-heading-copy'>"
                    "<div class='rb-home-heading-row'>"
                    "<h2>Today's Study</h2>"
                    "</div>"
                    "<div class='rb-home-subtitle'>Your personalised plan for today.</div>"
                    "</div>"
                    f"<div class='rb-home-count'><strong>{len(todays)}</strong> "
                    f"session{'s' if len(todays) != 1 else ''} today</div></div>",
                    unsafe_allow_html=True,
                )
                if todays:
                    for index, session in enumerate(todays):
                        render_today_session_card(
                            session, status, all_days, expanded=(index == 0), keyprefix="home_"
                        )
                else:
                    with st.container(border=True, key="home_empty_state"):
                        st.markdown(
                            "<div class='rb-home-empty-icon'>"
                            f"{_icon('calendar', 25, '#0d5c6e', 1.8)}</div>"
                            "<div class='rb-home-empty-title'>Nothing scheduled for today</div>"
                            "<div class='rb-home-empty-copy'>Enjoy the breather, or look ahead "
                            "in Study Plan.</div>",
                            unsafe_allow_html=True,
                        )

        with side:
            with st.container(key="home_rail"):
                exam = st.session_state.get("exam_date")
                with st.container(border=True, key="home_rail_exam"):
                    st.markdown(
                        f"<div class='rb-home-rail-title'>{_icon('calendar', 17, '#17233A', 1.9)}"
                        "<span>Exam Countdown</span></div>",
                        unsafe_allow_html=True,
                    )
                    if exam:
                        try:
                            days = max((exam - date.today()).days, 0)
                            st.markdown(
                                f"<div class='rb-home-metric'>{days} days</div>",
                                unsafe_allow_html=True,
                            )
                            st.caption(f"until {st.session_state.get('subject', 'your exam')}")
                        except Exception:
                            st.caption("Set an exam date in Setup.")
                    else:
                        st.caption("Set an exam date in Setup.")

                with st.container(border=True, key="home_rail_time"):
                    st.markdown(
                        f"<div class='rb-home-rail-title accent-green'>{_icon('clock', 17, '#3f8f35', 1.9)}"
                        "<span>Today's Total Study Time</span></div>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f"<div class='rb-home-metric'>{tmin // 60}h {tmin % 60}m</div>",
                        unsafe_allow_html=True,
                    )
                    st.caption("of focused study")

                with st.container(border=True, key="home_rail_progress"):
                    st.markdown(
                        f"<div class='rb-home-rail-title'>{_icon('chart', 17, '#17233A', 1.9)}"
                        "<span>Progress Summary</span></div>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f"<div class='rb-home-metric'>{prog['pct']:.0%} complete</div>",
                        unsafe_allow_html=True,
                    )
                    st.progress(prog["pct"])
                    st.caption(
                        f"{prog['completed']} completed · {active} in progress · {planned} planned"
                    )

                if recovery_relevant:
                    with st.container(border=True, key="home_rail_recovery"):
                        st.markdown(
                            f"<div class='rb-home-rail-title accent-coral'>{_icon('recovery', 17, '#C93638', 1.9)}"
                            "<span>Recovery Alert</span></div>",
                            unsafe_allow_html=True,
                        )
                        recovery_notes = []
                        if skipped:
                            recovery_notes.append(
                                f"{skipped} skipped session{'s' if skipped != 1 else ''}"
                            )
                        if overdue:
                            recovery_notes.append(
                                f"{overdue} overdue session{'s' if overdue != 1 else ''}"
                            )
                        if st.session_state.get("recovery_preview"):
                            recovery_notes.append("Recovery preview ready")
                        st.caption(" · ".join(recovery_notes))

                with st.container(border=True, key="home_rail_quick"):
                    st.markdown(
                        f"<div class='rb-home-rail-title accent-blue'>{_icon('zap', 17, '#147DA1', 1.9)}"
                        "<span>Quick Actions</span></div>",
                        unsafe_allow_html=True,
                    )
                    if st.button(
                        "Upload another document", key="qa_upload", use_container_width=True
                    ):
                        _nav_to("Setup")
                    if st.button(
                        "Review availability", key="qa_recovery", use_container_width=True
                    ):
                        _nav_to("Recovery")


# ---------------------------------------------------------------------------
# Knowledge Map
# ---------------------------------------------------------------------------
def render_topic_inspector(sections, graph, sel):
    with st.container(border=True):
        _section("Topic Details", "info")
        if not sel:
            st.caption("Select a topic to inspect its details.")
            return
        sec = _section_for(sel)
        role = classify_topic_role(sel, graph)
        mastery = st.session_state.get("mastery_scores", {})
        tdiff = topic_difficulty_map(sections)
        pr = priority_label(calculate_priority(sel, mastery.get(sel, 0.0), graph, tdiff.get(sel, 2)))
        st.markdown(f"### {sel}")
        st.markdown(f"{_chip(role, 'rgba(98,196,218,.18)', '#0d5c6e')} {_priority_chip(pr)}",
                    unsafe_allow_html=True)
        if sec.get("summary"):
            st.write(sec["summary"])
        st.caption(f"Estimated study time: {sec.get('estimated_study_time', '—')} · "
                   f"Difficulty: {sec.get('estimated_difficulty', '—')}")
        pre = graph.get(sel, [])
        unlocked = [t for t in [x["title"] for x in sections] if sel in graph.get(t, [])]
        st.write("Prerequisites: " + (", ".join(pre) or "None"))
        st.write("Topics unlocked: " + (", ".join(unlocked) or "None"))
        kc = [c for c in sec.get("key_concepts", []) if c and c != "general principles"][:6]
        if kc:
            st.markdown("**Key assessable points**")
            st.write(", ".join(kc))
        if sel in mastery:
            st.caption(f"Mastery: {mastery[sel]:.0%}")


def render_relationship_canvas(sections, graph):
    titles = [s["title"] for s in sections]
    if not titles:
        st.info("No topics yet. Analyse your notes in Setup first.")
        return
    edges = [(pre, t) for t in titles for pre in graph.get(t, []) if pre in titles]
    roles = {"Foundation": "#62C4DA", "Intermediate": "#FA855A", "End": "#FFDE96", "Independent": "#A7AFBE"}
    st.markdown("**Legend** — " + " · ".join(
        f"<span class='rb-chip' style='background:{roles[r]};color:#0c1622'>{r}</span>"
        for r in roles) + " &nbsp; arrows point prerequisite &rarr; dependent.",
        unsafe_allow_html=True)

    graph_col, insp_col = st.columns([2.3, 1.2], gap="large")
    clicked = None
    with graph_col:
        rendered = False
        try:
            from streamlit_agraph import agraph, Node, Edge, Config
            nodes = [Node(id=t, label=t, size=18,
                          color=roles[classify_topic_role(t, graph)]) for t in titles]
            ag_edges = [Edge(source=a, target=b, color="#9AA6B2") for a, b in edges]
            cfg = Config(width="100%", height=470, directed=True, physics=True,
                         nodeHighlightBehavior=True, highlightColor="#FA855A", collapsible=False)
            clicked = agraph(nodes=nodes, edges=ag_edges, config=cfg)
            rendered = True
        except Exception as exc:
            print(f"[Rebound] streamlit-agraph unavailable ({exc}); graphviz fallback.")
        if not rendered:
            try:
                dot = ["digraph G {", 'rankdir=LR; bgcolor="transparent";',
                       'node [style=filled, fontname="Helvetica", fontcolor="#0c1622", '
                       'color="#9AA6B2", shape=box];']
                for t in titles:
                    dot.append(f'"{t}" [fillcolor="{roles[classify_topic_role(t, graph)]}"];')
                for a, b in edges:
                    dot.append(f'"{a}" -> "{b}" [color="#9AA6B2"];')
                dot.append("}")
                st.graphviz_chart("\n".join(dot), use_container_width=True)
                rendered = True
            except Exception as exc:
                print(f"[Rebound] graphviz fallback failed ({exc}).")
        if not rendered:
            st.info("Interactive graph unavailable — showing relationships as a list.")
            for a, b in edges:
                st.write(f"{a} -> {b}")
        # topic picker (also drives the inspector; works with every fallback)
        picked = st.selectbox("Inspect topic", titles,
                              index=titles.index(st.session_state["kmap_sel_topic"])
                              if st.session_state.get("kmap_sel_topic") in titles else 0,
                              key="kmap_pick")
        if clicked and clicked in titles:
            st.session_state["kmap_sel_topic"] = clicked
        else:
            st.session_state["kmap_sel_topic"] = picked
        if not edges:
            st.info("No prerequisite relationships were detected. "
                    "Each topic is currently treated as independent.")
    with insp_col:
        render_topic_inspector(sections, graph, st.session_state.get("kmap_sel_topic"))


def _rename_topic(old, new):
    ss = st.session_state
    for s in ss.get("sections", []):
        if s["title"] == old:
            s["title"] = new
        s["prerequisites"] = [new if p == old else p for p in s.get("prerequisites", [])]
        s["relationships"] = [new if p == old else p for p in s.get("relationships", [])]
    ss["topics"] = [new if t == old else t for t in ss.get("topics", [])]
    ss["prerequisites"] = {(new if k == old else k): [new if p == old else p for p in v]
                           for k, v in ss.get("prerequisites", {}).items()}
    m = ss.get("mastery_scores", {})
    if old in m:
        m[new] = m.pop(old)
    for sess in ss.get("study_plan") or []:
        if sess["topic"] == old:
            sess["topic"] = new


def _delete_topic(topic):
    ss = st.session_state
    ss["sections"] = [s for s in ss.get("sections", []) if s["title"] != topic]
    for s in ss["sections"]:
        s["prerequisites"] = [p for p in s.get("prerequisites", []) if p != topic]
        s["relationships"] = [p for p in s.get("relationships", []) if p != topic]
    ss["topics"] = [t for t in ss.get("topics", []) if t != topic]
    ss.get("prerequisites", {}).pop(topic, None)
    for k in ss.get("prerequisites", {}):
        ss["prerequisites"][k] = [p for p in ss["prerequisites"][k] if p != topic]
    ss.get("mastery_scores", {}).pop(topic, None)
    ss["study_plan"] = [s for s in ss.get("study_plan") or [] if s["topic"] != topic]


def _merge_topics(a, b):
    ss = st.session_state
    secs = ss.get("sections", [])
    sa = next((s for s in secs if s["title"] == a), None)
    sb = next((s for s in secs if s["title"] == b), None)
    if not sa or not sb:
        return
    sb["key_concepts"] = list(dict.fromkeys(sb.get("key_concepts", []) + sa.get("key_concepts", [])))
    sb["definitions"] = list(dict.fromkeys(sb.get("definitions", []) + sa.get("definitions", [])))
    _delete_topic(a)


def page_knowledge_map():
    _page_title("Knowledge Map", "book")
    st.caption("Explore how your topics connect and build on each other.")
    sections = st.session_state.get("sections") or []
    graph = st.session_state.get("prerequisites", {})
    mastery = st.session_state.get("mastery_scores", {})
    tdiff = topic_difficulty_map(sections)
    view = st.radio("View", ["Topic cards", "Relationship map"], horizontal=True, key="kmap_view")

    if view == "Topic cards":
        with st.expander("Manage topics (rename, delete, merge)"):
            titles = [s["title"] for s in sections]
            mc = st.columns(3)
            a = mc[0].selectbox("Merge this topic", ["—"] + titles, key="merge_a")
            b = mc[1].selectbox("into this topic", ["—"] + titles, key="merge_b")
            if mc[2].button("Merge", key="merge_btn") and a != "—" and b != "—" and a != b:
                _merge_topics(a, b)
                st.rerun()
        for idx, sec in enumerate(sections):
            topic = sec["title"]
            pr = priority_label(calculate_priority(topic, mastery.get(topic, 0.0), graph, tdiff.get(topic, 2)))
            with st.container(border=True):
                head = st.columns([4, 1])
                head[0].markdown(f"### {topic}")
                head[1].markdown(f"<div style='text-align:right'>{_priority_chip(pr)}</div>",
                                 unsafe_allow_html=True)
                if sec.get("tested"):
                    st.markdown(_chip("Definitely tested", "#F6FFEA", "#3f6b1f"), unsafe_allow_html=True)
                kc = [c for c in sec.get("key_concepts", []) if c and c != "general principles"][:4]
                if kc:
                    st.markdown("**Key assessable points**")
                    st.write(", ".join(kc))
                st.caption(f"Estimated study time: {sec.get('estimated_study_time', '—')} · "
                           f"Difficulty: {sec.get('estimated_difficulty', '—')}")
                st.write(sec.get("summary", ""))
                with st.expander("View details"):
                    if topic in mastery:
                        st.write(f"Mastery: {mastery[topic]:.0%}")
                    st.write("Prerequisites: " + (", ".join(sec.get("prerequisites", [])) or "None"))
                    if sec.get("definitions"):
                        st.markdown("**Definitions**")
                        for dd in sec["definitions"]:
                            st.markdown(f"- {dd}")
                    if sec.get("processes"):
                        st.markdown("**Processes**")
                        for pp in sec["processes"]:
                            st.markdown(f"- {pp}")
                    if sec.get("important_facts"):
                        st.markdown("**Important facts**")
                        for ff in sec["important_facts"]:
                            st.markdown(f"- {ff}")
                    if sec.get("learning_objectives"):
                        st.markdown("**Learning objectives**")
                        for oo in sec["learning_objectives"]:
                            st.markdown(f"- {oo}")
                    if sec.get("example"):
                        st.write("Example: " + sec["example"])
                    st.divider()
                    newname = st.text_input("Rename topic", value=topic, key=f"rn_{idx}")
                    ec = st.columns(3)
                    if ec[0].button("Save name", key=f"rnbtn_{idx}") and newname.strip() and newname.strip() != topic:
                        _rename_topic(topic, newname.strip())
                        st.rerun()
                    tested = ec[1].checkbox("Definitely tested", value=bool(sec.get("tested")), key=f"tst_{idx}")
                    if tested != bool(sec.get("tested")):
                        sec["tested"] = tested
                        st.rerun()
                    if ec[2].button("Delete topic", key=f"del_{idx}"):
                        _delete_topic(topic)
                        st.rerun()
    else:
        render_relationship_canvas(sections, graph)


# ---------------------------------------------------------------------------
# Diagnostic (question view + results view)
# ---------------------------------------------------------------------------
def render_diagnostic_question(questions):
    store = st.session_state.setdefault("diag_answers", {})
    n = len(questions)
    step = max(0, min(st.session_state.get("diag_step", 0), n - 1))
    q = questions[step]
    with st.container(border=True):
        h = st.columns([3, 2, 2])
        with h[0]:
            _section("Diagnostic Test", "clipboard")
            st.caption("Assess your current understanding")
        with h[1]:
            st.progress((step + 1) / n)
            st.caption(f"{(step + 1) / n:.0%} complete")
        with h[2]:
            st.caption(f"Question {step + 1} of {n}")
            st.markdown(_chip(q["topic"], "#F6FFEA", "#3f6b1f"), unsafe_allow_html=True)
    with st.container(border=True):
        top = st.columns([3, 1])
        top[0].markdown(f"<span style='color:var(--primary);font-weight:700;font-size:1.1rem'>"
                        f"Question {step + 1}</span>", unsafe_allow_html=True)
        top[1].markdown(f"<div style='text-align:right'>{_chip(str(q['marks']) + ' marks', 'rgba(250,133,90,.14)', '#8a3b1e')}</div>",
                        unsafe_allow_html=True)
        st.markdown(f"### {q['question']}")
        st.markdown(_chip("Biology", "#F6FFEA", "#3f6b1f"), unsafe_allow_html=True)
        key = f"diag_{q['id']}"
        if key not in st.session_state:
            st.session_state[key] = store.get(q["id"], "")
        st.text_area("Your answer", key=key, height=200, placeholder="Write your answer here...",
                     label_visibility="collapsed")
        st.caption("Use full sentences. You can reference key biological processes and examples.")

    def _harvest():
        store[q["id"]] = st.session_state.get(key, "")

    st.divider()
    b = st.columns([1, 1, 1, 3])
    if b[0].button("Previous", key="dq_prev", disabled=(step == 0)):
        _harvest()
        st.session_state["diag_step"] = step - 1
        st.rerun()
    if b[1].button("Next", key="dq_next", disabled=(step == n - 1)):
        _harvest()
        st.session_state["diag_step"] = step + 1
        st.rerun()
    if b[2].button("Finish", type="primary", key="dq_finish"):
        _harvest()
        res, mastery = evaluate_diagnostic(questions, store)
        st.session_state["diagnostic_results"] = res
        st.session_state["mastery_scores"] = mastery
        if st.session_state.get("initial_mastery") is None:
            st.session_state["initial_mastery"] = dict(mastery)
        for k, v in {"study_plan": [], "recovered_plan": None, "session_status": {},
                     "recovery_preview": None, "recovery_changes": [], "diag_review_sel": 0}.items():
            st.session_state[k] = v
        st.rerun()


def _q_status(score, marks):
    if marks and score >= marks:
        return ("Correct", "#3f6b1f", "rgba(231,241,168,.6)", "check")
    if score <= 0:
        return ("Incorrect", "#8a1f1f", "rgba(201,54,56,.14)", "x")
    return ("Partially correct", "#7a5a17", "rgba(255,222,150,.35)", "minus")


def render_diagnostic_results(questions, results):
    earned = sum(results.get(q["id"], {}).get("score", 0) for q in questions)
    avail = sum(q["marks"] for q in questions)
    pct = earned / avail if avail else 0.0
    sel = max(0, min(st.session_state.get("diag_review_sel", 0), len(questions) - 1))

    with st.container(border=True):
        h = st.columns([3, 4])
        with h[0]:
            _section("Diagnostic Results", "clipboard")
            st.caption("Review your performance and feedback")
        h[1].progress(1.0)

    main, side = st.columns([2, 1], gap="large")
    with side:
        with st.container(border=True):
            st.markdown(f"<div class='rb-serif' style='font-size:2.2rem;color:var(--primary)'>{pct:.0%}</div>",
                        unsafe_allow_html=True)
            st.caption(f"You got {earned} marks out of {avail}")
        with st.container(border=True):
            st.markdown("**Question overview**")
            st.markdown(
                _chip("Correct", "rgba(231,241,168,.6)", "#3f6b1f") + " " +
                _chip("Partially correct", "rgba(255,222,150,.35)", "#7a5a17") + " " +
                _chip("Incorrect", "rgba(201,54,56,.14)", "#8a1f1f"), unsafe_allow_html=True)
            for i, q in enumerate(questions):
                r = results.get(q["id"], {})
                label, fg, bg, ic = _q_status(r.get("score", 0), q["marks"])
                mark = "= " if i == sel else "  "
                if st.button(f"{mark}Question {i + 1} — {r.get('score', 0)}/{q['marks']} · {label}",
                             key=f"rev_{i}", use_container_width=True):
                    st.session_state["diag_review_sel"] = i
                    st.rerun()
    with main:
        q = questions[sel]
        r = results.get(q["id"], {})
        with st.container(border=True):
            top = st.columns([3, 1])
            top[0].markdown(f"<span style='color:var(--primary);font-weight:700'>Question {sel + 1}</span> · "
                            f"{q['topic']}", unsafe_allow_html=True)
            top[1].markdown(f"<div style='text-align:right'>{_chip(str(q['marks']) + ' marks', 'rgba(250,133,90,.14)', '#8a3b1e')}</div>",
                            unsafe_allow_html=True)
            st.markdown(f"### {q['question']}")
            st.markdown("**Your answer**")
            st.write(st.session_state.get("diag_answers", {}).get(q["id"], "") or "_No answer submitted._")
            cc, mm = st.columns(2)
            with cc:
                st.markdown(f"{_icon('check', 16, '#3f6b1f')} **What you got correct**", unsafe_allow_html=True)
                for c in (r.get("correct_concepts") or ["—"]):
                    st.markdown(f"- {c}")
            with mm:
                st.markdown(f"{_icon('x', 16, '#8a1f1f')} **What marks you missed**", unsafe_allow_html=True)
                for c in (r.get("missing_concepts") or ["—"]):
                    st.markdown(f"- {c}")
            if r.get("misconceptions"):
                st.markdown("**Misconceptions**")
                for mcn in r["misconceptions"]:
                    st.markdown(f"- {mcn}")
            st.markdown(f"**Score: {r.get('score', 0)} / {q['marks']}** — How to improve")
            st.write(r.get("improvement", "—"))
            with st.expander("Mark scheme & expected answer"):
                st.write("Expected answer: " + (q.get("expected_answer") or "—"))
                for pt in q.get("mark_scheme", []):
                    st.markdown(f"- {pt}")
                st.caption("Semantic concepts: " + (", ".join(q.get("semantic_concepts", [])) or "—"))

    st.divider()
    b = st.columns([1, 1, 3])
    if b[0].button("Retake diagnostic", key="res_retake"):
        st.session_state["diagnostic_results"] = {}
        st.session_state["diag_step"] = 0
        st.session_state["diag_answers"] = {}
        st.rerun()
    if b[1].button("View study plan", type="primary", key="res_plan"):
        _nav_to("Study Plan")


def page_diagnostic():
    sections = st.session_state.get("sections") or []
    if not st.session_state.get("diagnostic_questions"):
        try:
            st.session_state["diagnostic_questions"] = generate_exam_questions(sections)
        except Exception as exc:
            _page_title("Diagnostic", "clipboard")
            st.error(f"Fireworks question generation failed: {exc}")
            st.info("Set DEBUG_OFFLINE=1 to use the local generator for offline development.")
            return
    questions = st.session_state["diagnostic_questions"]
    if st.session_state.get("diagnostic_results"):
        render_diagnostic_results(questions, st.session_state["diagnostic_results"])
    else:
        render_diagnostic_question(questions)


# ---------------------------------------------------------------------------
# Study Plan (weekly calendar overview; no Today's Study here)
# ---------------------------------------------------------------------------
def _evt_tint(state, active):
    if active:
        return ("rgba(250,133,90,.16)", "#8a3b1e")
    if state == "completed":
        return ("#F6FFEA", "#3f6b1f")
    if state == "skipped":
        return ("rgba(120,120,120,.14)", "#5b5b5b")
    return ("rgba(98,196,218,.16)", "#0d5c6e")


def render_week_calendar(plan, status, all_days, base, today):
    nav = st.columns([1, 1, 1, 3])
    off = st.session_state.get("week_offset", 0)
    if nav[0].button("Prev", key="wk_prev"):
        st.session_state["week_offset"] = off - 1
        st.rerun()
    if nav[1].button("Today", key="wk_today"):
        st.session_state["week_offset"] = 0
        st.rerun()
    if nav[2].button("Next", key="wk_next"):
        st.session_state["week_offset"] = off + 1
        st.rerun()
    nav[3].markdown(f"<div class='rb-serif' style='font-size:1.2rem;text-align:right;margin-top:6px'>"
                    f"Week of {format_date(base)}</div>", unsafe_allow_html=True)
    days = [base + timedelta(days=i) for i in range(7)]
    by_date = {}
    for s in plan:
        by_date.setdefault(s["date"], []).append(s)
    cols = st.columns(7)
    for i, d in enumerate(days):
        with cols[i]:
            is_today = (d == today)
            cls = "rb-daycol rb-today" if is_today else "rb-daycol"
            bb = "var(--secondary)" if is_today else "transparent"
            bf = "#08323c" if is_today else "inherit"
            st.markdown(f"<div class='{cls}'><span class='rb-datebadge' style='background:{bb};color:{bf}'>"
                        f"{d.day}</span> <span class='rb-evt m'>{d.strftime('%a')}"
                        f"{' · Today' if is_today else ''}</span></div>", unsafe_allow_html=True)
            for s in by_date.get(d.isoformat(), []):
                state = status.get(s["topic"], "pending")
                active = st.session_state.get("active_session") == s["topic"]
                bg, fg = _evt_tint(state, active)
                st.markdown(f"<div class='rb-evt' style='background:{bg}'>"
                            f"<div class='t' style='color:{fg}'>{s['topic']}</div>"
                            f"<div class='m'>{s['duration']} min · {s.get('priority', '')} · "
                            f"{_STATUS_TEXT.get(state, 'Planned')}</div></div>", unsafe_allow_html=True)
                with st.expander("Open"):
                    st.write(f"Mastery: {s['mastery']:.0%} · Duration: {s['duration']} min")
                    st.caption(s.get("reason", ""))
                    for pt in _key_points(s["topic"], 3):
                        st.markdown(f"- {pt}")
                    if state == "pending":
                        a = st.columns(2)
                        if a[0].button("Start", type="primary", key=f"cal_start_{s['topic']}"):
                            st.session_state["active_session"] = s["topic"]
                            st.rerun()
                        if a[1].button("Complete", key=f"cal_done_{s['topic']}"):
                            status[s["topic"]] = "completed"
                            st.session_state["session_status"] = status
                            st.rerun()
                        tgt = st.selectbox("Move to day", all_days,
                                           format_func=lambda dd: format_date(today + timedelta(days=dd - 1)),
                                           key=f"cal_mv_sel_{s['topic']}")
                        a2 = st.columns(2)
                        if a2[0].button("Move", key=f"cal_mv_{s['topic']}"):
                            st.session_state["study_plan"] = reschedule_session(
                                st.session_state["study_plan"], s["topic"], tgt, today)
                            st.rerun()
                        if a2[1].button("Skip", key=f"cal_skip_{s['topic']}"):
                            status[s["topic"]] = "skipped"
                            st.session_state["session_status"] = status
                            st.rerun()
                    else:
                        if st.button("Reset", key=f"cal_reset_{s['topic']}"):
                            status.pop(s["topic"], None)
                            st.session_state["session_status"] = status
                            st.rerun()


def page_study_plan():
    _page_title("Study Plan", "calendar")
    mastery = st.session_state.get("mastery_scores") or {}
    sections = st.session_state.get("sections", [])
    tdiff = topic_difficulty_map(sections)
    today = date.today()
    if not st.session_state.get("study_plan"):
        st.session_state["study_plan"] = generate_study_plan(
            topics=list(mastery), mastery_scores=mastery,
            prerequisites=st.session_state.get("prerequisites", {}),
            exam_date=st.session_state.get("exam_date"),
            daily_study_time=st.session_state.get("daily_study_time", 2.0),
            topic_difficulty=tdiff, start_date=today)
    plan = st.session_state["study_plan"]
    status = st.session_state.setdefault("session_status", {})
    all_days = sorted({s["day"] for s in plan})
    prog = plan_progress(plan, status)
    off = st.session_state.get("week_offset", 0)
    base = today + timedelta(days=7 * off)

    left, mid, right = st.columns([1.1, 3, 1.3], gap="large")
    with left:
        with st.container(border=True):
            st.markdown(_mini_month_html(base, today, plan), unsafe_allow_html=True)
        with st.container(border=True):
            exam = st.session_state.get("exam_date")
            if exam:
                try:
                    st.markdown("**Exam countdown**")
                    st.markdown(f"<div class='rb-serif' style='font-size:1.5rem'>"
                                f"{max((exam - today).days, 0)} days</div>", unsafe_allow_html=True)
                except Exception:
                    pass
            st.markdown("**Weekly workload**")
            st.write(f"{sum(s['duration'] for s in plan)} min planned")
            st.progress(prog["pct"])
            st.caption("Adjust availability on the Recovery page.")
    with mid:
        render_week_calendar(plan, status, all_days, base, today)
    with right:
        with st.container(border=True):
            st.markdown("**Plan overview**")
            st.write(f"Total sessions: {prog['total']}")
            st.write(f"Completed: {prog['completed']}")
            st.write(f"Remaining: {prog['remaining_minutes']} min")
            st.progress(prog["pct"])
        with st.container(border=True):
            st.markdown("**Focus areas**")
            weak = sorted(mastery.items(), key=lambda x: x[1])[:3]
            for t, mv in weak:
                st.write(f"{t} — {mv:.0%}")
        with st.container(border=True):
            st.markdown("**Upcoming sessions**")
            inc = [s for s in plan if status.get(s["topic"]) not in ("completed", "skipped")][:4]
            for s in inc:
                st.caption(f"{s['date_label']} · {s['topic']}")


# ---------------------------------------------------------------------------
# Recovery (SaaS dashboard layout)
# ---------------------------------------------------------------------------
def render_recovery_dashboard():
    _page_title("Recovery", "recovery")
    st.write("Life happens. Mark the days you can't study and Rebound rebuilds a realistic plan — "
             "you preview it before anything changes.")
    plan = st.session_state.get("study_plan") or []
    if not plan:
        st.info("Generate a study plan first (Diagnostic -> Study Plan).")
        return
    mastery = st.session_state.get("mastery_scores", {})
    prereqs = st.session_state.get("prerequisites", {})
    start = date.today()
    preview = st.session_state.get("recovery_preview")
    changes = st.session_state.get("recovery_changes", [])

    # --- Estimated Impact (top, wide) ---
    with st.container(border=True):
        st.markdown("### Estimated Impact")
        if preview is None:
            st.caption("Generate a preview below to see how your plan would change. "
                       "Nothing changes until you apply.")
        else:
            impact = estimate_impact(plan, preview, changes)
            st.caption("Preview only — your study plan has NOT changed yet.")
            im = st.columns(5)
            for col, (lbl, val) in zip(im, [("Moved", impact["moved"]), ("Compressed", impact["compressed"]),
                                            ("Removed", impact["removed"]), ("Added", impact["added"]),
                                            ("Time Saved", f"{impact['time_saved']} min")]):
                col.metric(lbl, val)
            if impact["fits"]:
                st.success("All sessions fit within your available days.")
            else:
                st.warning("Some sessions couldn't be placed. Try strategy B or C, or add hours.")

    mainc, rightc = st.columns([2.4, 1], gap="large")
    with mainc:
        # --- Recovery Settings ---
        with st.container(border=True):
            settop = st.columns([3, 2])
            with settop[0]:
                _section("Recovery Settings", "settings")
            available_hours = st.number_input("Daily study hours", 0.5, 12.0,
                                              float(st.session_state.get("daily_study_time", 2.0)), 0.5,
                                              key="rec_hours")
            day_options = [(d, format_date(start + timedelta(days=d - 1))) for d in range(1, 8)]
            unavailable_labels = st.multiselect("Days you're unavailable (calendar)",
                                                [lbl for _, lbl in day_options], key="rec_unavail")
            unavailable_days = {d for d, lbl in day_options if lbl in unavailable_labels}
            strat = st.radio("If the plan no longer fits your available time, prefer to:",
                             ["A · Increase time", "B · Reduce sessions", "C · Compress topics"],
                             index=0, horizontal=True, key="rec_strategy")
            st.caption("A increases study time on remaining days · B reduces low-priority sessions · "
                       "C compresses high-mastery topics.")
            if settop[1].button("Generate Recovery Preview", type="primary", key="rec_gen"):
                pv, ch = build_recovery_preview(plan, mastery, prereqs, unavailable_days,
                                                available_hours, start, strategy=strat[0])
                st.session_state["recovery_preview"] = pv
                st.session_state["recovery_changes"] = ch
                st.session_state["recovery_settings"] = {"available_hours": available_hours,
                                                         "unavailable_days": sorted(unavailable_days),
                                                         "strategy": strat[0]}
                st.rerun()

        # --- Original vs Recovered ---
        if preview is not None:
            with st.container(border=True):
                _section("Original vs. Recovered", "compare")
                change_of = {c["topic"]: c["change"] for c in changes}
                CH = {"moved": ("Moved", "rgba(98,196,218,.18)", "#0d5c6e"),
                      "compressed": ("Compressed", "rgba(255,222,150,.35)", "#7a5a17"),
                      "removed": ("Removed", "rgba(201,54,56,.14)", "#8a1f1f"),
                      "added": ("Added", "#F6FFEA", "#3f6b1f"),
                      "unchanged": ("Unchanged", "rgba(120,120,120,.12)", "#5b5b5b")}
                cl, cr = st.columns(2)
                with cl:
                    st.markdown("**Original Plan**")
                    for s in plan:
                        st.caption(f"{s['date_label']} — {s['topic']} ({s['duration']} min)")
                with cr:
                    st.markdown("**Recovered Plan (preview)**")
                    for s in preview:
                        lbl, bg, fg = CH.get(change_of.get(s["topic"], "unchanged"))
                        st.markdown(f"<div class='rb-evt m'>{s['date_label']} — {s['topic']} "
                                    f"({s['duration']} min) {_chip(lbl, bg, fg)}</div>", unsafe_allow_html=True)
                    for c in changes:
                        if c["change"] == "removed":
                            lbl, bg, fg = CH["removed"]
                            st.markdown(f"<div class='rb-evt m'>{c['topic']} {_chip(lbl, bg, fg)}</div>",
                                        unsafe_allow_html=True)
                act = st.columns(2)
                if act[0].button("Apply Recovery Plan", type="primary", key="rec_apply"):
                    st.session_state["study_plan"] = apply_recovery(preview)
                    st.session_state["recovered_plan"] = st.session_state["study_plan"]
                    print("[Rebound] Recovery plan updated.")
                    live = {s["topic"] for s in preview}
                    st.session_state["session_status"] = {t: v for t, v in
                                                          st.session_state.get("session_status", {}).items()
                                                          if t in live}
                    st.session_state["recovery_preview"] = None
                    st.session_state["recovery_changes"] = []
                    st.success("Recovery applied. Your study plan is now updated.")
                    st.rerun()
                if act[1].button("Cancel", key="rec_cancel"):
                    st.session_state["recovery_preview"] = None
                    st.session_state["recovery_changes"] = []
                    st.rerun()

    with rightc:
        with st.container(border=True):
            st.markdown("**Recovery Summary**")
            st.write("Rebound will rebuild your plan around the days and strategy you choose. "
                     "Nothing changes until you apply.")
        with st.container(border=True):
            st.markdown("**Selected Constraints**")
            settings = st.session_state.get("recovery_settings", {})
            st.write(f"Daily study hours: {settings.get('available_hours', st.session_state.get('daily_study_time', 2.0))}")
            un = settings.get("unavailable_days", [])
            st.write(f"Unavailable days: {len(un)} selected" if un else "Unavailable days: none")
            st.write(f"Strategy: {settings.get('strategy', 'A')}")
        with st.container(border=True):
            st.markdown("**Tips**")
            st.write("Rebound prioritises low-mastery and prerequisite topics so your progress "
                     "stays on track.")


def page_recovery():
    render_recovery_dashboard()


# ---------------------------------------------------------------------------
# Progress (kept for backward compatibility; not in navigation)
# ---------------------------------------------------------------------------
def page_progress():
    _page_title("Progress", "chart")
    mastery = st.session_state.get("mastery_scores") or {}
    init = st.session_state.get("initial_mastery") or {}
    n = len(mastery)
    secure = sum(1 for v in mastery.values() if v >= 0.7)
    at_risk = [t for t, v in mastery.items() if v < 0.5]
    with st.container(border=True):
        st.markdown("### Exam readiness")
        st.write(f"Based on your current diagnostic and completed sessions, {secure} of {n} "
                 f"topic{'s' if n != 1 else ''} appear secure.")
        if at_risk:
            st.write(f"{len(at_risk)} topic(s) may need more attention before your exam.")
        st.caption("This is a guide from your responses so far, not a guarantee.")
    st.subheader("Mastery by topic")
    for topic, mv in sorted(mastery.items(), key=lambda x: x[1]):
        st.write(f"{topic} — {mv:.0%}")
        st.progress(mv)
        delta = mv - init.get(topic, mv)
        if abs(delta) >= 0.01:
            st.caption(f"Change since first diagnostic: {'+' if delta >= 0 else ''}{delta * 100:.0f} points")


# ---------------------------------------------------------------------------
# About Rebound (split-screen, mirrors Setup)
# ---------------------------------------------------------------------------
def render_about_split_layout():
    left, right = st.columns([1, 1], gap="large")
    with left:
        st.markdown(render_rebound_logo(), unsafe_allow_html=True)
        st.markdown(f"<div style='margin:14px 0'>{_chip('About Rebound', 'rgba(250,133,90,.14)', '#8a3b1e')}</div>",
                    unsafe_allow_html=True)
        st.markdown("<div class='rb-hero'>How Rebound helps<br>you recover and<br>perform your best.</div>",
                    unsafe_allow_html=True)
        st.write("Rebound turns your revision notes into a calm, adaptive study plan and helps you "
                 "recover when life gets in the way. Language tasks run on Fireworks AI; the "
                 "architecture is designed to move heavier compute to local AMD ROCm hardware.")
        f = st.columns(3)
        for col, (t, d) in zip(f, [
                ("Adaptive planning", "Plans adapt to your progress, schedule, and available time."),
                ("AI-powered analysis", "Rebound extracts key topics and concepts from your notes."),
                ("AMD-ready architecture", "Structured to support heavier local compute workflows.")]):
            col.markdown(f"<div class='rb-feat'>{t}</div>", unsafe_allow_html=True)
            col.caption(d)
    with right:
        with st.container(border=True):
            _page_title("About Rebound", "info")
            st.write("Rebound turns your revision notes into a calm, adaptive study plan and helps you "
                     "recover when life gets in the way.")
            with st.expander("AMD Compute Evidence", expanded=True):
                cs = st.session_state.get("compute_status", {})
                fm = st.session_state.get("fireworks_model", {})
                src = st.session_state.get("analysis_source", "")
                if not cs and not fm:
                    st.info("Run an analysis in Setup to populate runtime metadata.")
                else:
                    rows = [("Provider", cs.get("provider", "Fireworks AI")),
                            ("Returned model", fm.get("id") or fm.get("display") or "—"),
                            ("Operation", "document analysis / exam generation"),
                            ("Request ID", "Not captured by the client"),
                            ("Token usage", "Not captured by the client"),
                            ("Inference status", cs.get("inference_status", "—")),
                            ("Local fallback", "yes" if str(src).startswith("fallback") else "no")]
                    for label, value in rows:
                        c = st.columns([1, 2])
                        c[0].markdown(f"**{label}**")
                        c[1].write(value)
                st.caption("Only real runtime metadata is shown; nothing is hardcoded as successful.")


def page_about():
    render_about_split_layout()


# ---------------------------------------------------------------------------
# Top navigation + dispatch
# ---------------------------------------------------------------------------
def render_topbar():
    with st.container(border=True):
        left, mid, right = st.columns([2, 3, 2])
        with left:
            st.markdown(render_rebound_logo(), unsafe_allow_html=True)
        with mid:
            bits = []
            if st.session_state.get("subject"):
                bits.append(st.session_state["subject"])
            exam = st.session_state.get("exam_date")
            if exam:
                try:
                    days = (exam - date.today()).days
                    bits.append(f"Exam in {days} day{'s' if days != 1 else ''}" if days >= 0 else "Exam date passed")
                except Exception:
                    pass
            st.markdown(f"<div class='rb-muted' style='text-align:center;margin-top:8px'>{' · '.join(bits)}</div>",
                        unsafe_allow_html=True)
        with right:
            cur = st.session_state.get("theme", "light")
            if st.button("Dark mode" if cur == "light" else "Light mode", key="theme_toggle"):
                st.session_state["theme"] = "dark" if cur == "light" else "light"
                st.rerun()
        st.radio("Navigate", PAGES, key="nav_radio", horizontal=True,
                 format_func=lambda p: (p + " (locked)" if _lock_message(p) else p),
                 label_visibility="collapsed")


_PAGE_FUNCS = {"Home": page_home, "Setup": page_setup, "Knowledge Map": page_knowledge_map,
               "Diagnostic": page_diagnostic, "Study Plan": page_study_plan,
               "Recovery": page_recovery, "About Rebound": page_about}

if st.session_state.get("_pending_nav"):
    st.session_state["nav_radio"] = st.session_state.pop("_pending_nav")

_inject_css()
render_topbar()
_page = st.session_state["nav_radio"]

if st.session_state.get("active_session"):
    render_focus_view()
else:
    _msg = _lock_message(_page)
    if _msg:
        _page_title(_page)
        with st.container(border=True):
            st.info(_msg)
            _target = ("Setup" if _page in ("Knowledge Map", "Diagnostic")
                       else "Diagnostic" if _page == "Study Plan" else "Study Plan")
            if st.button(f"Go to {_target}", type="primary", key="lock_go"):
                _nav_to(_target)
    else:
        _PAGE_FUNCS[_page]()
