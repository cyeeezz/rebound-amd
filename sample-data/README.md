# Rebound Sample Test File

This folder contains a demonstration **A-Level Biology notes** PDF
(`sample-a-level-biology-notes.pdf`) supplied so judges and reviewers can test
Rebound without needing to provide their own study material. It is
demonstration educational content, not a real student's notes.

The document covers seven topics:

- Cell Structure
- Cellular Respiration
- Energy Transfer in Cells
- DNA Structure
- Gene Expression
- Genetic Inheritance
- Historical Biology Experiments

## Testing instructions

### Local testing

1. Start the app:
   ```bash
   python -m streamlit run app.py
   ```
2. Open the upload page.
3. Select `sample-data/sample-a-level-biology-notes.pdf`.
4. Accept the Fireworks processing consent.
5. Run the analysis.
6. Review the diagnostic, adaptive plan, knowledge map, AMD semantic
   relationships, and the About page.

### Live-demo testing

1. Open https://rebound-amd.streamlit.app/
2. Download the sample PDF from the GitHub repository
   (`sample-data/sample-a-level-biology-notes.pdf`).
3. Upload it to Rebound.
4. Follow the same analysis flow as above.

## Notes

- The PDF is **sample educational material** and contains **no real student
  records** or personal data.
- It is included **only for demonstration and reproducibility**.
- **Live analysis requires a working Fireworks AI configuration** in the
  deployed application (a `FIREWORKS_API_KEY` set in the app's secrets).
- The AMD notebook artifacts in `amd_artifacts/` were generated from the
  corresponding **seven-topic development knowledge map** (`knowledge_map.json`).
  The deployed Streamlit server does **not** run live AMD GPU inference on each
  upload; it loads the pre-computed AMD artifacts.

## Licensing / distribution

This sample is supplied for **hackathon demonstration and testing** purposes. It
is demonstration educational content and is **not** covered by the repository's
MIT License (which applies to the software source code, not this document).

## Integrity

- **Size:** 73,090 bytes
- **Pages:** 10
- **SHA-256:** `8adf084fb7d29c4927452d5c1b81ca47dbf677c2ae9b28d725fe8190bf8fb18d`
