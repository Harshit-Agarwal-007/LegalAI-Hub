"""
legal_risk_chatbot.py

-----------------------------------------------------------

1. One-shot analysis of a contract (English text already).
2. Returns JSON: {risks:[], improvedVersion:""}.
3. Enters a chat loop so the same model can answer questions.

-----------------------------------------------------------
"""

import os
import json
import re
from pathlib import Path
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential

# ---------- CONFIG (env → fallbacks) ----------------------------

ENDPOINT = os.getenv(
    "AZURE_INFERENCE_SDK_ENDPOINT",
    "https://legalai-hub-resource.services.ai.azure.com/models/"
)

MODEL_NAME = os.getenv("DEPLOYMENT_NAME", "Phi-4-mini-instruct")

API_KEY = os.getenv(
    "AZURE_INFERENCE_SDK_KEY", 
    "1PRZDEEBAiF3Lt77H8N7WbbugcQmq3j7WRIlyemjvL2GjyTKmndQJQQJ99BGAC77bzfXJ3w3AAAAACOGooar"
)

# ---------- PROMPTS ---------------------------------------------

SYSTEM_PROMPT_ANALYSE = (
    "You are a senior Indian contract-law expert. "
    "Your tasks:\n"
    "1. Identify all potentially risky, unfair or fraudulent clauses.\n"
    "2. Produce a safer, user-friendly rewrite of the entire contract.\n\n"
    "Return ONLY valid JSON with this schema:\n"
    "{\n"
    '  "risks": [\n'
    '    { "clause": "<clause_text>", "reason": "<explanation>" },\n'
    "    ...\n"
    "  ],\n"
    '  "improvedVersion": "<improved_contract_text>"\n'
    "}"
)

SYSTEM_PROMPT_CHAT = (
    "You are continuing as the same contract-law expert. "
    "Answer follow-up questions about the risks you found or the improved draft. "
    "If asked to revise text, output the revised text only."
)

# ---------- helpers for API -------------------------------------

def analyse_contract_text(text: str) -> str:
    """Return JSON string with risks + improvedVersion."""
    client = ChatCompletionsClient(ENDPOINT, AzureKeyCredential(API_KEY))
    
    resp = client.complete(
        model=MODEL_NAME,
        messages=[
            SystemMessage(content=SYSTEM_PROMPT_ANALYSE),
            UserMessage(content=f"Contract text follows:\n{text}")
        ],
        max_tokens=2048,
        temperature=0.2
    )
    
    return resp.choices[0].message.content.strip()

def chat_with_agent(history):
    """
    history = list[SystemMessage|UserMessage]
    returns ChatMessage (assistant)
    """
    client = ChatCompletionsClient(ENDPOINT, AzureKeyCredential(API_KEY))
    
    resp = client.complete(
        model=MODEL_NAME,
        messages=history,
        max_tokens=1024,
        temperature=0.3
    )
    
    return resp.choices[0].message

def json_to_contract_text(path: str) -> str:
    """Convert JSON contract data to plain text."""
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # If file starts with array, take first item
    node = data[0] if isinstance(data, list) else data
    
    parts = [node.get("Title", "")]
    
    # Sections is a dict {heading: [lines]}
    sections = node.get("Sections", {})
    
    for heading, lines in sections.items():
        if heading:
            parts.append(f"\n\n### {heading}\n")
        
        # lines may contain bilingual duplicates → keep the English half
        for line in lines:
            if not line:  # skip null / empty strings
                continue
            
            # crude filter: keep only latin chars + basic punctuation
            eng = re.sub(r"[^\x00-\x7F]+", " ", line)
            parts.append(eng.strip())
    
    # Join with newlines
    text = "\n".join(parts)
    
    # Collapse multiple spaces/newlines
    text = re.sub(r"\n{3,}", "\n\n", text)
    
    return text.strip()

# ---------- Main execution (if run directly) --------------------

if __name__ == "__main__":
    # Load contract text from JSON file
    try:
        contract_text = json_to_contract_text("contract_data_translated.json")
    except FileNotFoundError:
        print("Error: contract_data_translated.json not found")
        exit(1)
    
    # Create client
    client = ChatCompletionsClient(ENDPOINT, AzureKeyCredential(API_KEY))
    
    # One-shot analysis
    print("Analyzing contract...")
    
    analysis_response = client.complete(
        model=MODEL_NAME,
        max_tokens=2048,
        temperature=0.2,
        messages=[
            SystemMessage(content=SYSTEM_PROMPT_ANALYSE),
            UserMessage(content=f"Contract text follows:\n{contract_text}")
        ]
    )
    
    analysis_json = analysis_response.choices[0].message.content.strip()
    
    print("\n===== INITIAL ANALYSIS JSON =====")
    print(analysis_json)
    print("=================================\n")
    
    # Try to parse (optional, for validation)
    try:
        parsed = json.loads(analysis_json)
        print(f"🔹 Found {len(parsed['risks'])} risk items.\n")
    except Exception as e:
        print("⚠ Could not parse JSON – check model output.", e)
    
    # Interactive chatbot loop
    print("💬 Enter chat mode. Type 'exit' to quit.")
    
    chat_history = [
        SystemMessage(content=SYSTEM_PROMPT_CHAT),
        UserMessage(content="Here is the contract and analysis:\n" + analysis_json)
    ]
    
    while True:
        user_input = input("You: ")
        if user_input.lower() in {"exit", "quit"}:
            break
        
        chat_history.append(UserMessage(content=user_input))
        
        chat_resp = client.complete(
            model=MODEL_NAME,
            messages=chat_history,
            max_tokens=1024,
            temperature=0.3,
            top_p=0.9
        )
        
        assistant_msg = chat_resp.choices[0].message
        print(f"\nAI: {assistant_msg.content.strip()}\n")
        
        # Keep conversation context short (avoid token bloat)
        chat_history.append(assistant_msg)
        if len(chat_history) > 12:
            # Drop earliest user/assistant pair (keep system + recent 5 exchanges)
            chat_history = chat_history[:1] + chat_history[-10:]