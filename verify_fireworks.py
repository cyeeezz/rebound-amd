"""verify_fireworks.py — end-to-end check of the live Fireworks AI round-trip.

Run this from the Rebound folder to confirm whether analyze_document_with_fireworks()
actually reaches Fireworks (LIVE) or silently uses the local heuristic (FALLBACK).
It makes the SAME request the app makes, using the SAME key-resolution order, so a
green result here means the app's Setup tab will also run live.

    cd Rebound
    python -m pip install -r requirements.txt      # once
    python verify_fireworks.py                      # default: sample text + primary model
    python verify_fireworks.py --pdf sample-a-level-biology-notes.pdf
    python verify_fireworks.py --model accounts/fireworks/models/deepseek-v3

Exit code 0 = LIVE API round-trip succeeded. Exit code 1 = fell back / failed.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

# --- Mirror app.py's connection settings (kept in sync intentionally) --------
FIREWORKS_BASE_URL = "https://api.fireworks.ai/inference/v1"
PRIMARY_MODEL = "accounts/fireworks/models/deepseek-v4-pro"
_FIREWORKS_API_KEY_DEFAULT = ""
_FIREWORKS_MAX_CHARS = 12000

SAMPLE_TEXT = (
    "Cell Structure\n"
    "All living organisms are made of cells. Eukaryotic cells contain a nucleus "
    "which stores DNA. The mitochondria are the site of aerobic respiration.\n\n"
    "Respiration\n"
    "Respiration releases energy from glucose. Aerobic respiration occurs in the "
    "mitochondria and produces ATP, carbon dioxide and water.\n\n"
    "Photosynthesis\n"
    "Photosynthesis occurs in the chloroplasts of plant cells. Light energy is "
    "used to convert carbon dioxide and water into glucose and oxygen."
)


def _line(char: str = "-") -> None:
    print(char * 68)


def resolve_api_key() -> tuple[str, str]:
    """Resolve the key exactly like app.py: secrets.toml -> env var -> default.

    Returns (key, source_label). st.secrets isn't available outside Streamlit,
    so this reads .streamlit/secrets.toml directly for parity.
    """
    # 1) .streamlit/secrets.toml
    for path in (".streamlit/secrets.toml", os.path.expanduser("~/.streamlit/secrets.toml")):
        if os.path.exists(path):
            try:
                try:
                    import tomllib  # Python 3.11+
                    with open(path, "rb") as fh:
                        data = tomllib.load(fh)
                except ModuleNotFoundError:
                    import toml  # type: ignore
                    data = toml.load(path)
                if data.get("FIREWORKS_API_KEY"):
                    return str(data["FIREWORKS_API_KEY"]), f"secrets.toml ({path})"
            except Exception as exc:
                print(f"[warn] could not parse {path}: {exc}")

    # 2) environment variable
    env = os.getenv("FIREWORKS_API_KEY")
    if env:
        return env, "env var FIREWORKS_API_KEY"

    # 3) hardcoded default
    return _FIREWORKS_API_KEY_DEFAULT, "hardcoded default in app.py (INSECURE)"


def load_text(pdf_path: str | None) -> tuple[str, str]:
    """Return (text, source_desc). Uses a PDF if given, else the built-in sample."""
    if not pdf_path:
        return SAMPLE_TEXT, "built-in sample text"
    if not os.path.exists(pdf_path):
        print(f"[error] PDF not found: {pdf_path}")
        sys.exit(2)
    # Reuse the app's own extraction cascade so we test the real path.
    try:
        from app import extract_pdf_text  # noqa: WPS433

        class _F:  # minimal shim: extract_pdf_text expects .getvalue()
            def __init__(self, b: bytes) -> None:
                self._b = b

            def getvalue(self) -> bytes:
                return self._b

        with open(pdf_path, "rb") as fh:
            text = extract_pdf_text(_F(fh.read()))
        return text, f"{pdf_path} (via app.extract_pdf_text)"
    except Exception as exc:
        print(f"[warn] app.extract_pdf_text unavailable ({exc}); falling back to pdfplumber")
        import io

        import pdfplumber

        with open(pdf_path, "rb") as fh:
            with pdfplumber.open(io.BytesIO(fh.read())) as pdf:
                text = "\n".join((p.extract_text() or "") for p in pdf.pages).strip()
        return text, f"{pdf_path} (via pdfplumber)"


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the live Fireworks round-trip.")
    parser.add_argument("--model", default=PRIMARY_MODEL, help="Fireworks model id to test")
    parser.add_argument("--pdf", default=None, help="Path to a PDF to analyze (optional)")
    args = parser.parse_args()

    print()
    _line("=")
    print(" REBOUND — Fireworks AI live round-trip verifier")
    _line("=")

    # 1) SDK present?
    try:
        from openai import OpenAI
    except Exception as exc:  # noqa: BLE001
        print(f"\nRESULT: FALLBACK — openai SDK not importable ({exc}).")
        print("Fix: python -m pip install -r requirements.txt")
        return 1

    # 2) Key + inputs
    key, key_source = resolve_api_key()
    masked = f"{key[:6]}...{key[-4:]}" if len(key) > 12 else "(short/empty)"
    text, text_source = load_text(args.pdf)

    print(f"\nKey source   : {key_source}")
    print(f"Key (masked) : {masked}")
    print(f"Model        : {args.model}")
    print(f"Endpoint     : {FIREWORKS_BASE_URL}")
    print(f"Input text   : {text_source}  ({len(text)} chars)")
    if not text.strip():
        print("\nRESULT: cannot test — no text extracted from the PDF.")
        return 1

    # 3) Live call — identical shape to analyze_document_with_fireworks()
    system_prompt = (
        "You are an expert study assistant. Split the student's revision notes "
        "into coherent learning sections. Return ONLY a JSON object of the form "
        '{"sections": [{"title": "<concise topic title>", "body": "<the relevant '
        'text for that topic>"}]}. Preserve the document\'s wording in each body. '
        "Do not invent content."
    )
    _line()
    print("Calling Fireworks...")
    t0 = time.perf_counter()
    try:
        client = OpenAI(api_key=key, base_url=FIREWORKS_BASE_URL)
        response = client.chat.completions.create(
            model=args.model,
            response_format={"type": "json_object"},
            temperature=0.2,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text[:_FIREWORKS_MAX_CHARS]},
            ],
        )
    except Exception as exc:  # noqa: BLE001
        dt = time.perf_counter() - t0
        print(f"\nRESULT: FALLBACK — the API call raised after {dt:.2f}s.")
        print(f"Error type : {type(exc).__name__}")
        print(f"Error      : {exc}")
        _line()
        low = str(exc).lower()
        if "401" in low or "auth" in low or "api key" in low or "unauthorized" in low:
            print("Likely cause: bad/expired API key. Rotate it and set FIREWORKS_API_KEY.")
        elif "404" in low or "not found" in low or "model" in low:
            print("Likely cause: model id not available to this account. Try --model "
                  "accounts/fireworks/models/deepseek-v3")
        elif "connection" in low or "timeout" in low or "resolve" in low or "network" in low:
            print("Likely cause: no network egress to api.fireworks.ai (firewall/proxy/offline).")
        elif "429" in low or "rate" in low:
            print("Likely cause: rate limited. Wait and retry.")
        else:
            print("See the error above for the specific cause.")
        return 1

    dt = time.perf_counter() - t0

    # 4) Validate the payload the same way the app does
    try:
        raw = response.choices[0].message.content
        payload = json.loads(raw)
        sections = [
            s for s in payload.get("sections", [])
            if isinstance(s, dict) and str(s.get("title", "")).strip()
            and str(s.get("body", "")).strip()
        ]
    except Exception as exc:  # noqa: BLE001
        print(f"\nRESULT: FALLBACK — API responded but JSON was invalid ({exc}).")
        print(f"Raw content: {str(raw)[:400]}")
        return 1

    if not sections:
        print("\nRESULT: FALLBACK — API responded but contained no valid sections.")
        return 1

    returned_model = getattr(response, "model", None) or args.model
    _line("=")
    print(f" RESULT: LIVE  ✅  Fireworks returned {len(sections)} sections in {dt:.2f}s")
    _line("=")
    print(f"Model returned by API : {returned_model}")
    print("Section titles:")
    for i, s in enumerate(sections, 1):
        print(f"  {i}. {str(s['title'])[:70]}")
    print("\nThis matches the app's success log: "
          f"[Rebound] Fireworks AI returned {len(sections)} sections.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
