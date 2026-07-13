# Rebound Hackathon Submission

Submission assets for the **LabLab AI × AMD Hackathon — Track 3 (Unicorn / Open
Innovation)**.

## Live Demo

https://rebound-amd.streamlit.app/

## Demo Video

[Watch the Rebound demo video on Google Drive](https://drive.google.com/file/d/1UxHnfuKIPjFnWJrQL6jqemeWfrPTTOxe/view)

> Judges may need the file's sharing setting to be **"Anyone with the link —
> Viewer"** to watch without requesting access.

## Slide Deck

[Download the Track 3 slide deck](Rebound_Track_3_Slide_Deck.pdf)

## Sample Test PDF

[Sample A-Level Biology notes](../sample-data/sample-a-level-biology-notes.pdf)

## GitHub Repository

https://github.com/cyeeezz/rebound-amd

## Quick Overview

Rebound is an AI-powered adaptive exam-recovery study planner. A student uploads
revision notes; Rebound extracts the topic structure, runs a diagnostic,
estimates mastery, and builds a day-by-day plan that re-plans itself when
sessions are missed.

The system uses a **two-runtime architecture**:

- **Fireworks AI** performs the language understanding — extracting topics and
  concepts from the uploaded notes and generating diagnostic exam questions.
- **AMD ROCm (PyTorch HIP)** generates the semantic topic embeddings on AMD
  Radeon GPU hardware using a SentenceTransformer model.
- **Semantic relationships are computed** from those embeddings (cosine
  similarity) and exported, alongside the embeddings and a run manifest, as
  committed artifacts.
- **Streamlit visualizes the results** — the diagnostic, adaptive plan,
  knowledge map, AMD semantic relationships, and a Verified AMD GPU Execution
  panel.

The two runtimes are independent and independently verifiable: Fireworks handles
language reasoning, while AMD-generated artifacts drive the semantic-intelligence
features the deployed app consumes on every run.
