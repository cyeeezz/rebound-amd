"""Loader for artifacts produced by the AMD ROCm embedding notebook.

Rebound consumes precomputed semantic embeddings and topic relationships that
were generated on AMD Radeon GPU hardware (PyTorch ROCm + SentenceTransformers)
inside the `notebooks/rebound_amd_embeddings.ipynb` notebook. This module reads
those artifacts *defensively*: every loader degrades to an empty structure when
a file is missing, unreadable, or malformed, so the application can never crash
because of the AMD integration.

Artifacts (in ``amd_artifacts/``):
    * amd_run_manifest.json  — run provenance (GPU, ROCm/PyTorch versions, ...)
    * topic_metadata.json    — per-topic summaries + semantic relationships
    * embeddings.npy         — float32 topic embedding matrix

Security notes:
    * JSON is parsed with the stdlib ``json`` module (no code execution).
    * ``numpy.load(..., allow_pickle=False)`` is enforced so a crafted .npy
      file can never execute arbitrary Python during unpickling.
    * pickle, eval, and exec are never used.
"""

from __future__ import annotations

import json
import os

# ---------------------------------------------------------------------------
# Artifact locations — resolved relative to the repository root so the loader
# works regardless of the process's current working directory.
# ---------------------------------------------------------------------------
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_THIS_DIR)
AMD_ARTIFACT_DIR = os.path.join(_REPO_ROOT, "amd_artifacts")

_MANIFEST_FILE = "amd_run_manifest.json"
_METADATA_FILE = "topic_metadata.json"
_EMBEDDINGS_FILE = "embeddings.npy"


def _artifact_path(filename: str) -> str:
    """Absolute path to an artifact file inside ``amd_artifacts/``."""
    return os.path.join(AMD_ARTIFACT_DIR, filename)


def _safe_load_json(path: str) -> dict:
    """Load a JSON object from ``path``.

    Returns an empty dict when the file is missing, unreadable, malformed, or
    does not decode to a JSON object. Never raises.
    """
    if not path or not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError, UnicodeDecodeError):
        # Missing file, permission error, or invalid JSON — degrade quietly.
        return {}
    return data if isinstance(data, dict) else {}


def load_amd_manifest() -> dict:
    """Return the AMD run manifest as a dict (empty dict if unavailable)."""
    return _safe_load_json(_artifact_path(_MANIFEST_FILE))


def load_amd_metadata() -> dict:
    """Return the topic metadata as a dict (empty dict if unavailable)."""
    return _safe_load_json(_artifact_path(_METADATA_FILE))


def load_amd_embeddings():
    """Return the topic embedding matrix as a numpy array, or ``None``.

    Loading is hardened with ``allow_pickle=False`` so a malicious .npy file
    cannot execute arbitrary code. Returns ``None`` when numpy is unavailable,
    the file is missing, or the array cannot be read.
    """
    path = _artifact_path(_EMBEDDINGS_FILE)
    if not os.path.isfile(path):
        return None
    try:
        import numpy as np  # imported lazily; optional at runtime
    except ImportError:
        return None
    try:
        return np.load(path, allow_pickle=False)
    except (OSError, ValueError):
        return None


def get_semantic_relationships() -> list[dict]:
    """Return AMD semantic relationships, de-duplicated and ranked.

    Each item is ``{"source", "target", "similarity", "relationship_type"}``.
    Reverse edges (A->B and B->A) are collapsed to the single highest-similarity
    entry, and the list is sorted by similarity descending. Returns an empty
    list when metadata is unavailable. Callers apply any display cap (e.g. 10).
    """
    metadata = load_amd_metadata()
    topics = metadata.get("topics")
    if not isinstance(topics, list):
        return []

    best_by_pair: dict[frozenset, dict] = {}
    for topic in topics:
        if not isinstance(topic, dict):
            continue
        for rel in topic.get("semantic_relationships", []) or []:
            if not isinstance(rel, dict):
                continue
            source = str(rel.get("source", "")).strip()
            target = str(rel.get("target", "")).strip()
            if not source or not target or source == target:
                continue
            try:
                similarity = float(rel.get("similarity", 0.0))
            except (TypeError, ValueError):
                continue
            pair = frozenset((source, target))
            existing = best_by_pair.get(pair)
            if existing is None or similarity > existing["similarity"]:
                best_by_pair[pair] = {
                    "source": source,
                    "target": target,
                    "similarity": similarity,
                    "relationship_type": str(
                        rel.get("relationship_type", "semantic_similarity")
                    ),
                }

    return sorted(
        best_by_pair.values(), key=lambda r: r["similarity"], reverse=True
    )


def is_verified_amd_run() -> bool:
    """True only when the manifest proves a real, completed AMD GPU run.

    All of the following must hold:
        * execution_status == "completed"
        * gpu_available is true
        * rocm_hip_version is present (non-empty)
        * topic_count > 0
        * embedding_dimensions > 0
    Any missing/failed condition returns False.
    """
    manifest = load_amd_manifest()
    if not manifest:
        return False
    if manifest.get("execution_status") != "completed":
        return False
    if manifest.get("gpu_available") is not True:
        return False
    if not str(manifest.get("rocm_hip_version", "")).strip():
        return False
    try:
        if int(manifest.get("topic_count", 0)) <= 0:
            return False
        if int(manifest.get("embedding_dimensions", 0)) <= 0:
            return False
    except (TypeError, ValueError):
        return False
    return True
