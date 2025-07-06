"""
translator.py

Azure Translator service integration for contract documents
"""

import json
import uuid
import requests
from pathlib import Path
from typing import List, Any, Optional

# Azure Translator configuration
AZ_KEY = "CXVyATCUo61ujegcOMlOHnCStrugfV8nhhlM6gRaO7YvFJJI4NU7JQQJ99BGACGhslBXJ3w3AAAbACOGzhei"
AZ_ENDPOINT = "https://api.cognitive.microsofttranslator.com"
AZ_REGION = "centralindia"

# Translation options
TO_LANG = "en"
INFILE = Path("contract_data.json")
OUTFILE = Path("contract_data_translated.json")

# ── Utility to flatten and track text values to translate ─────────────

def flatten_json(node: Any, parent=None, key=None, texts=None, ptrs=None):
    """Recursively flatten JSON to extract all text values for translation"""
    if texts is None:
        texts, ptrs = [], []
    
    if isinstance(node, str) and node.strip():  # Only translate non-empty strings
        texts.append(node)
        ptrs.append((parent, key))
    elif isinstance(node, list):
        for i, item in enumerate(node):
            flatten_json(item, node, i, texts, ptrs)
    elif isinstance(node, dict):
        for k, v in node.items():
            flatten_json(v, node, k, texts, ptrs)
    
    return texts, ptrs

# ── Translate a list of strings via Azure Translator ─────────────────

def translate_texts(texts: List[str], to_lang: str = TO_LANG) -> List[str]:
    """Translate list of texts using Azure Translator"""
    if not texts:
        return []
    
    url = f"{AZ_ENDPOINT}/translate?api-version=3.0&to={to_lang}"
    headers = {
        "Ocp-Apim-Subscription-Key": AZ_KEY,
        "Ocp-Apim-Subscription-Region": AZ_REGION,
        "Content-Type": "application/json",
        "X-ClientTraceId": str(uuid.uuid4())
    }
    
    result = []
    batch_size = 100  # Azure Translator batch limit
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        
        # Limit text length to avoid API limits
        body = [{"text": t[:5000]} for t in batch]
        
        try:
            resp = requests.post(url, headers=headers, json=body, timeout=30)
            resp.raise_for_status()
            
            batch_result = resp.json()
            result.extend([item["translations"][0]["text"] for item in batch_result])
            
        except requests.exceptions.RequestException as e:
            print(f"Translation error for batch {i//batch_size + 1}: {e}")
            # If translation fails, keep original text
            result.extend(batch)
    
    return result

# ── Main processing pipeline ────────────────────────────────────────

def process_translation(input_file: Path, output_file: Path):
    """Main translation processing function"""
    try:
        # Load the array of documents
        with open(input_file, 'r', encoding='utf-8') as f:
            docs = json.load(f)
        
        if not isinstance(docs, list):
            docs = [docs]  # Ensure it's a list
        
        for doc in docs:
            # Step 1: Translate values (title, paragraphs, fields, etc.)
            values, ptrs = flatten_json(doc)
            
            if values:  # Only translate if there are values to translate
                translated = translate_texts(values)
                
                # Update the document with translated values
                for (parent, key), val in zip(ptrs, translated):
                    parent[key] = val
            
            # Step 2: Translate section headings (keys of "Sections" dict)
            if "Sections" in doc and isinstance(doc["Sections"], dict):
                original_sections = doc["Sections"]
                original_keys = list(original_sections.keys())
                
                if original_keys:
                    translated_keys = translate_texts(original_keys)
                    
                    # Replace keys with translations
                    new_sections = {}
                    for orig, trans in zip(original_keys, translated_keys):
                        # Keep original in parentheses for reference
                        key_label = f"{trans} ({orig})" if orig != trans else trans
                        new_sections[key_label] = original_sections[orig]
                    
                    doc["Sections"] = new_sections
        
        # Write final translated file
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(docs, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Translation complete. Output saved to: {output_file}")
        return output_file
        
    except FileNotFoundError:
        print(f"❌ Error: Input file '{input_file}' not found")
        raise
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON in input file: {e}")
        raise
    except Exception as e:
        print(f"❌ Translation error: {e}")
        raise

def translate_file(in_json: str | Path, out_json: str | Path) -> Path:
    """
    Programmatic interface for translation.
    Re-uses main processing logic.
    """
    input_path = Path(in_json)
    output_path = Path(out_json)
    
    return process_translation(input_path, output_path)

# ── Main function ─────────────────────────────────────────────────────

def main():
    """Main function for CLI usage"""
    return process_translation(INFILE, OUTFILE)

# ── Run ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    main()