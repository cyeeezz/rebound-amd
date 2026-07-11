# Rebound

**AI-powered adaptive exam-recovery study planner** — turns revision notes into a
personalised, self-adjusting study plan, powered by Fireworks AI for language
understanding and **verified AMD Radeon GPU execution** (PyTorch ROCm) for
semantic topic embeddings.

> Built for the **AMD Developer Hackathon**.

## Overview

A student uploads revision notes (PDF); Rebound extracts the topic structure,
runs a diagnostic, estimates per-topic mastery, and generates a day-by-day study
plan that adapts when sessions are missed. Two independent runtimes power the app:

- **Fireworks AI** performs natural-language extraction and exam-question
  generation.
- An **AMD ROCm notebook** computes semantic topic embeddings and topic-to-topic
  relationships on AMD Radeon GPU hardware, exported as artifacts and loaded into
  the app at runtime.

## Features

- Adaptive planning that re-prioritises as mastery, time, and schedule change.
- Fireworks AI topic/concept extraction from uploaded notes.
- **Verified AMD GPU execution** — semantic embeddings/relationships computed on
  AMD Radeon hardware with PyTorch ROCm, surfaced in-app.
- Diagnostic assessment with keyword/semantic marking.
- Knowledge map with prerequisite graph **plus** AMD-computed semantic similarity.
- Recovery preview before applying missed-day changes.
- Privacy controls: explicit upload consent and one-click "Clear data".

## Architecture

```
User Upload
      |
      v
Fireworks AI Extraction
      |
      v
Knowledge Map  <----  AMD GPU Notebook
                            |
                      Sentence Transformer
                            |
                      Semantic Embeddings
                            |
                      Semantic Relationships
                            |
                    Knowledge Graph Enhancement
```

The uploaded document flows through Fireworks AI to produce the Knowledge Map.
Independently, the AMD GPU notebook runs a SentenceTransformer to produce semantic
embeddings and relationships that enhance the Knowledge Graph. The two runtimes
never share a process and are reported separately in the app.

### AMD GPU workflow

1. The notebook runs inside **AMD Radeon Developer Cloud** on ROCm-capable GPUs.
2. It loads `knowledge_map.json` (the app's extracted topics).
3. `sentence-transformers/all-MiniLM-L6-v2` runs under **PyTorch ROCm** to embed
   each topic into a 384-dimensional vector.
4. Cosine similarity yields semantic relationships above a threshold.
5. Embeddings, per-topic metadata, and a run manifest are exported to
   `amd_artifacts/`.
6. At runtime, `utils/amd_loader.py` loads the artifacts; the app renders the
   **Verified AMD GPU Execution** evidence and **AMD Semantic Relationships**.

### Fireworks workflow

Fireworks AI (via the OpenAI-compatible client) performs document analysis and
diagnostic exam-question generation only. It is a **separate runtime** and never
runs inside the AMD notebook. Local heuristics provide a labelled fallback.

### Notebook workflow

`notebooks/rebound_amd_embeddings.ipynb` is the reproducible source of the AMD
artifacts; running it regenerates `embeddings.npy`, `topic_metadata.json`, and
`amd_run_manifest.json`.

## Artifacts

| File | Description |
|------|-------------|
| `amd_artifacts/embeddings.npy` | Float32 topic embedding matrix (`topic_count x 384`). Loaded with `allow_pickle=False`. |
| `amd_artifacts/topic_metadata.json` | Per-topic titles, summaries, key concepts, semantic relationships. |
| `amd_artifacts/amd_run_manifest.json` | Run provenance: status, GPU availability, ROCm/HIP + PyTorch versions, model ID, counts, timestamp, duration. |

`utils/amd_loader.py` exposes `load_amd_manifest()`, `load_amd_metadata()`,
`load_amd_embeddings()`, `get_semantic_relationships()`, and
`is_verified_amd_run()`. Every loader degrades to an empty structure when an
artifact is missing or malformed; pickle/eval/exec are never used.

## Installation

```bash
git clone https://github.com/cyeeezz/rebound-amd.git
cd rebound-amd

python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate

pip install -r requirements.txt
```

`pdf2image` also requires the Poppler binary (`brew install poppler` /
`apt-get install poppler-utils` / Poppler for Windows).

## Running

```bash
streamlit run app.py
```

`.streamlit/config.toml` sets a 25 MB upload cap, enables XSRF protection, and
disables usage stats. The AMD notebook is run separately on ROCm hardware to
(re)generate artifacts.

## Environment variables

| Variable | Purpose |
|----------|---------|
| `FIREWORKS_API_KEY` | **Required.** Read from `.streamlit/secrets.toml` first, then the environment. Never hardcoded. |
| `DEBUG_OFFLINE` | Optional. Set to `1` to force local analysis/question generation offline. |

Store the key in `.streamlit/secrets.toml` (git-ignored):

```toml
FIREWORKS_API_KEY = "fw-..."
```

## Security

- No hardcoded secrets; `.streamlit/secrets.toml` is git-ignored.
- Safe deserialisation: stdlib JSON; numpy `allow_pickle=False`; no pickle/eval/exec.
- All dynamic values rendered via `unsafe_allow_html` pass through `html.escape`.
- Uploads bounded to 25 MB in both `app.py` and `config.toml`.
- Generic user-facing errors; internal exceptions logged server-side only.
- Explicit upload consent before analysis, and "Clear data" wipes session state.

## Hackathon evidence

- **Notebook:** `notebooks/rebound_amd_embeddings.ipynb` (AMD Radeon Developer
  Cloud, PyTorch ROCm).
- **Verified manifest:** `amd_artifacts/amd_run_manifest.json` —
  `execution_status: completed`, `gpu_available: true`, ROCm/HIP + PyTorch
  recorded, `topic_count: 7`, `embedding_dimensions: 384`,
  `relationship_count: 21`.
- **In-app verification:** the About page shows **Verified AMD GPU Execution**
  only when the manifest proves a real, completed GPU run.

## License

Released under the **MIT License** — see [`LICENSE`](LICENSE).
