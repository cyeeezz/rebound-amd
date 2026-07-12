# AMD GPU Evidence — Screenshots

Chronological screenshots proving each stage of AMD ROCm execution for Rebound,
from the final notebook run (7 topics, 384 dimensions, 21 relationships).

| # | File | Stage | Proves |
|---|------|-------|--------|
| 01 | `01-rocm-smi.jpeg` | AMD ROCm environment | `rocm-smi` shows AMD GPU (Device 0) + active ROCm stack |
| 02 | `02-pytorch-rocm.jpeg` | PyTorch HIP runtime | `cuda.is_available()=True`, count 1, PyTorch 2.9.1, HIP 7.2.53211 |
| 03 | `03-model-loading.jpeg` | SentenceTransformer | `all-MiniLM-L6-v2` loaded on the ROCm device |
| 04 | `04-embedding-generation.jpeg` | Embedding generation | Final embeddings `(7, 384)`, 384 dims, 7 topics |
| 05 | `05-semantic-relationships.jpeg` | Semantic relationships | Cosine similarity → 21 relationships |
| 06 | `06-artifact-generation.jpeg` | Artifact generation | `np.save(..., allow_pickle=False)` + JSON writes |
| 07 | `07-manifest-generation.jpeg` | Manifest | Manifest JSON (device, ROCm, model, time, counts) |
| 08 | `08-artifact-validation.jpeg` | Artifact validation | Files exist + sizes (10,880 / 10,781 / 931 B) |
| 09 | `09-sha256-validation.jpeg` | SHA-256 verification | `hashlib.sha256` integrity hashes |
| 10 | `10-verified-amd-ui.jpeg` | Production app | Streamlit "Verified AMD GPU Execution" panel |

Additional context screenshots (notebook browser/tabs/kernel, cosine-similarity
code, intermediate manifest cells, test-run embeddings) are retained in
[`supplementary/`](supplementary/).

> Documentation evidence only — no application code or notebook outputs are
> affected.
