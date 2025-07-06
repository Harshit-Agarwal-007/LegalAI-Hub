"""
ocr_contract.py
-----------------------------------------------------------------
• CLI usage:
      python ocr_contract.py sample.pdf
      → Runs Azure Document Intelligence on the PDF and writes
        contract_data.json in the current folder.

• Library usage (FastAPI):
      from ocr_contract import ocr_bytes
      json_path = ocr_bytes(pdf_bytes, endpoint, key, "tmp/out.json")
"""

import io
import json
import sys
from collections import OrderedDict
from pathlib import Path
from typing import List, Dict

from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient


# ────────────────────────────────────────────────────────────────
# Internal helpers
# ────────────────────────────────────────────────────────────────

def _field_text(f):
    """Return a field's string value, if present."""
    if not f:
        return None
    return getattr(f, "value_string", None) or getattr(f, "content", None)


def _convert_results(contract_res, layout_res) -> List[Dict]:
    """
    Build a structured dictionary list from Azure results.
    """
    docs = []
    for doc in contract_res.documents:
        output = OrderedDict()

        # Basic fields
        output["Title"] = _field_text(doc.fields.get("Title"))
        output["EffectiveDate"] = str(
            getattr(doc.fields.get("EffectiveDate"), "value_date", "")
        )

        # Parties
        parties = doc.fields.get("Parties")
        output["Parties"] = [_field_text(p) for p in (parties.value_array if parties else [])]

        # Jurisdictions
        juris_list = []
        juris_field = doc.fields.get("Jurisdictions")
        if juris_field and hasattr(juris_field, "value_array"):
            for item in juris_field.value_array:
                if hasattr(item, "value_object"):
                    juris_list.append({
                        "Region": _field_text(item.value_object.get("Region")),
                        "Clause": _field_text(item.value_object.get("Clause")),
                    })
        output["Jurisdictions"] = juris_list

        # Sections (from layout)
        sections = OrderedDict()
        current = "Preamble"
        for p in layout_res.paragraphs:
            if (p.role or "").lower().find("heading") >= 0:
                current = p.content.strip()
                sections.setdefault(current, [])
            else:
                sections.setdefault(current, []).append(p.content.strip())
        output["Sections"] = sections

        docs.append(output)
    return docs


def _extract_from_bytes(pdf_bytes: bytes, client: DocumentIntelligenceClient):
    """
    Run both prebuilt models on in‑memory PDF bytes.

    Works with *any* SDK version:
      • Tries modern `document=` signature.
      • Falls back to legacy `body=` if TypeError raised.
    """
    try:
        # ----- preferred (SDK ≥ 1.0.0b1) -----
        poll_contract = client.begin_analyze_document(
            model_id="prebuilt-contract",
            document=pdf_bytes,
            content_type="application/pdf"
        )
        poll_layout = client.begin_analyze_document(
            model_id="prebuilt-layout",
            document=pdf_bytes,
            content_type="application/pdf"
        )
    except TypeError:
        # ----- fallback for older SDKs -----
        poll_contract = client.begin_analyze_document(
            "prebuilt-contract", body=io.BytesIO(pdf_bytes)
        )
        poll_layout = client.begin_analyze_document(
            "prebuilt-layout", body=io.BytesIO(pdf_bytes)
        )

    contract_res = poll_contract.result()
    layout_res   = poll_layout.result()
    return _convert_results(contract_res, layout_res)


# ────────────────────────────────────────────────────────────────
# Public API
# ────────────────────────────────────────────────────────────────

def extract_contract(pdf_path: str, endpoint: str, key: str):
    """
    Extract contract data from a PDF on disk.
    Returns a list[dict] (one item per doc).
    """
    client = DocumentIntelligenceClient(endpoint, AzureKeyCredential(key))
    with open(pdf_path, "rb") as fh:
        pdf_bytes = fh.read()
    return _extract_from_bytes(pdf_bytes, client)


def ocr_bytes(pdf_bytes: bytes, endpoint: str, key: str,
              out_json: str | Path) -> Path:
    """
    FastAPI helper:
        ocr_bytes(pdf_bytes, endpoint, key, "tmp/raw.json")
    Saves the structured JSON and returns its Path.
    """
    client = DocumentIntelligenceClient(endpoint, AzureKeyCredential(key))
    data = _extract_from_bytes(pdf_bytes, client)

    out_path = Path(out_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return out_path


# ────────────────────────────────────────────────────────────────
# CLI entry‑point
# ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Quick manual test
    endpoint = "https://<your-ocr-resource>.cognitiveservices.azure.com/"
    key = "<your-ocr-key>"

    if len(sys.argv) < 2:
        print("Usage: python ocr_contract.py <pdf_path>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    if not Path(pdf_path).exists():
        print(f"❌ PDF file not found: {pdf_path}")
        sys.exit(1)

    try:
        docs = extract_contract(pdf_path, endpoint, key)
        out_file = Path("contract_data.json")
        out_file.write_text(json.dumps(docs, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"✅ OCR completed → {out_file} ({len(docs)} document(s))")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
