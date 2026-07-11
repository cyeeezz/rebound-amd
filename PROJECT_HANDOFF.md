# Rebound — Project Handoff Summary

## 1. Project Overview
- **App:** *Rebound* — an adaptive exam-recovery planner. A student uploads revision notes (PDF); the app extracts topics, runs a diagnostic, builds an adaptive study plan, and can intelligently rebuild that plan when a study session is missed.
- **Core tech stack:**
  - **Python + Streamlit** (single-file UI, five tabs).
  - **PDF extraction:** `pdfplumber` (primary) → `PyMuPDF`/`fitz` (fallback) → `pypdf` (final fallback).
  - **AI:** **Fireworks AI** accessed through the **OpenAI Python SDK** (OpenAI-compatible endpoint).
  - No database, auth, calendar, notifications, or chatbot (explicitly out of scope).

## 2. Architecture & File Structure
- **Location:** `C:\Users\Admin\Documents\Trading Analyst\Rebound\`
- **Files:**
  - `app.py` — entire application (helpers + UI). ~1,100+ lines.
  - `requirements.txt` — `streamlit>=1.36`, `openai>=1.30`, `pdfplumber>=0.11`, `PyMuPDF>=1.24`, `pypdf>=4.0`.
  - `PROJECT_HANDOFF.md` — this summary.
- **Structure inside `app.py`:** a large block of **pure helper functions** (no Streamlit calls) at the top, followed by the **UI** organized into 5 `st.tabs`.
- **Run command:** `python -m pip install -r requirements.txt` then `python -m streamlit run app.py` (use `python -m` so the libs land in the same interpreter that runs Streamlit).

## 3. Tabs & Session State
- **Tabs:** `Setup`, `Knowledge Map`, `Diagnostic`, `Study Plan`, `Recovery & AMD Evidence`.
- **Session state keys:** `document_text`, `sections`, `topics`, `prerequisites`, `diagnostic_questions`, `diagnostic_results`, `mastery_scores`, `study_plan`, `recovered_plan`, `recovery_decisions`, `amd_runtime`, `doc_stats`, `fireworks_model`, `processing_summary`, `compute_status`, plus student inputs (`student_name`, `subject`, `exam_date`, `daily_study_time`, `file_name`).
- **Important:** `study_plan` (original) and `recovered_plan` are kept **separate** — recovery never overwrites the original.

## 4. Key Features & Code Logic

### Setup tab — Fireworks document pipeline
- Student form (name, subject, exam date, daily study hours) + PDF-only uploader + "Analyze Notes".
- Visible pipeline via `st.status`: read PDF → extract text → Fireworks analysis → detect sections → build prereq graph → knowledge map.
- **AI Activity Log** (green checkmarks), **Processing Summary** (file, pages, chars, sections, time, provider, model), **⚡ AI Compute Status** panel (stored under separate `compute_status` key; extendable for AMD ROCm/GPU fields), **explainability** expander, success banner.

### PDF extraction (`_read_pdf`)
- Reads bytes via `getvalue()` (avoids stream-consumption bug), then cascades pdfplumber → PyMuPDF → pypdf; advances if an engine yields < 20 chars. Only returns empty ("scanned") if **all** fail. Prints Pages/Characters/Words for debugging (`_report_extraction`).
- Public helpers: `extract_pdf_text()`, `count_pdf_pages()`.

### Fireworks analysis (`analyze_document_with_fireworks(text, model) -> dict`)
- **Live call** via `OpenAI(api_key=..., base_url="https://api.fireworks.ai/inference/v1")`.
- Model: `accounts/fireworks/models/llama-v3p1-70b-instruct` (alt: `deepseek-v3`).
- Key resolution order: `st.secrets["FIREWORKS_API_KEY"]` → `os.getenv("FIREWORKS_API_KEY")` → hardcoded default.
- `response_format={"type":"json_object"}` requesting `{"sections":[{"title","body"}]}`; text capped at 12,000 chars.
- **Fallback:** on missing SDK / API error / invalid JSON / empty sections → `_fallback_response()` uses local `_segment_sections()`. Same `{model, sections:[{title,body,lines}]}` shape either way; `source` field flags which path ran. `OpenAI` import is guarded so a missing package can't crash the app.
- Supporting helpers: `_normalize_api_sections`, `_segment_sections`, `_is_heading`, `_clean_title`, `build_sections`, `parse_fireworks_response`, `build_topic_graph`, `calculate_document_statistics`, `_key_concepts`, `_learning_objectives`, `_quick_check`, `_estimate_difficulty`, `_estimate_study_time`.

### Knowledge Map tab
- AI Analysis Dashboard (metrics incl. heuristic **Document Complexity** from avg sentence length, vocab diversity, concept density), one expandable card per section (summary, objectives, key concepts, quick check, difficulty, study time, prerequisites), **Fireworks AI Insights** (hardest/foundation topics, strongest dependencies, exam focus), Document Statistics.

### Diagnostic tab
- `generate_questions()` → one 5-mark question per topic in expanders with answer textareas.
- `evaluate_answer()` = **word-count heuristic**: 0→0/5, 1–15→2/5, 16–40→3/5, 41–80→4/5, 80+→5/5, with fixed feedback strings. `mastery = score / marks` saved to `mastery_scores`.

### Study Plan tab
- `generate_study_plan()` — **priority_score = (1−mastery)*0.6 + prereq_weight*0.3 + exam_weight(0.8)*0.1**; labels: ≥0.75 🔴High, 0.50–0.74 🟠Medium, <0.50 🟢Low.
- Adaptive durations by mastery: <0.4→90, 0.4–0.6→60, 0.6–0.8→45, >0.8→30 min.
- Topological prerequisite ordering (`_order_with_prerequisites`); packs sessions into ≤7 days respecting `daily_study_time`. Auto-detects a recovered plan and offers a toggle (Recovered vs Original).

### Recovery & AMD Evidence tab (Adaptive Recovery Engine)
- Helpers: `recover_plan`, `make_recovery_decision`, `calculate_recovery_priority`, `calculate_confidence`, `compress_session`, `move_session`, `drop_session`, `rebuild_schedule`.
- **priority = (1−mastery)*0.5 + dependency_weight*0.3 + remaining_days_weight(0.8)*0.2**.
- Decisions: **Protect / Compress / Move / Drop** (Drop only if mastery >0.8 AND no dependents). Compression 90→60→45→30→15. Rebuilds a genuinely new schedule (moved sessions deferred to later days).
- UI: side-by-side comparison with change badges (🔴 removed, 🟡 duration, 🔵 day, 🟢 unchanged), decision cards with "Why did the AI choose this?" explainability, summary metrics (Protected/Compressed/Moved/Removed/Time Saved/New Completion Time).

## 5. Prompting Style & Conventions
- **Concise, direct responses**; minimal fluff.
- **Strictly scoped edits:** each task modifies only the named tab(s); other tabs left untouched.
- **Modular helpers, no AI/business logic inside Streamlit UI** — UI orchestrates helpers only.
- **Single swap point** philosophy: swapping placeholder → real integration touches one function (e.g., `analyze_document_with_fireworks`).
- **Dynamic, never hardcoded:** section titles/objectives/concepts/prereqs derive from the actual document.
- **Graceful fallbacks** everywhere (PDF engines, API → local heuristic) so the app never crashes.
- **Verification:** logic unit-tested with standalone scripts before hand-off.

## 6. Current Status, Errors & Blockers
- ✅ Full 5-tab app implemented; extraction, diagnostic, study plan, and recovery engine all working and unit-tested.
- ✅ Fireworks live call wired with robust fallback; all five code paths tested with a mocked client.
- ⚠️ **Live Fireworks round-trip not yet verified over the network** — real key/model behavior will only surface when run locally. Watch terminal for `[Rebound] Fireworks AI returned N sections.` (success) vs `Fireworks API call failed (...)` (fallback).
- ⚠️ **Security:** the Fireworks API key is currently hardcoded as a default in `app.py`. Recommend rotating it and using an env var or `.streamlit/secrets.toml` (both already take priority over the default).
- ⚠️ **"Scanned images" bug (resolved as environment issue):** the sample PDF (`sample-a-level-biology-notes.pdf`) extracts fine — all 3 engines return 10 pages / ~18,400 chars / 2,800 words. The error occurs only when the PDF libs aren't installed in the interpreter running Streamlit → fix with `python -m pip install -r requirements.txt`.
- 🧹 Minor cleanup: `extract_topics()` is now dead code (Knowledge Map uses `sections` instead) — safe to delete.

## 7. Immediate Next Step
1. **Verify the live Fireworks call end-to-end:** run the app locally, upload `sample-a-level-biology-notes.pdf`, and confirm the terminal prints `Fireworks AI returned N sections` (not the fallback). Fix key/model if it falls back.
2. **Then:** surface the analysis `source` (live API vs. local fallback) as a small badge in the Setup UI so it's obvious during a demo which path ran.
3. Rotate the hardcoded API key and move it to `secrets.toml` / env var.
