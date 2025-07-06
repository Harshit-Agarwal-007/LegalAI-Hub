"""
main.py – FastAPI orchestrator

PDF → OCR (prebuilt-contract) → Translator → Phi-model analysis → chat

---------------------------------------------------------------------

• POST /api/process -> returns {id, analysis}
• POST /api/chat -> follows up with the same AI agent
• GET / -> serves static/index.html
"""

import uuid
import json
import os
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

from ocr_contract import ocr_bytes  # bytes → JSON (raw)
from translator import translate_file  # JSON → JSON (EN)
from aiagent import (  # JSON → risks + chat
    analyse_contract_text,
    chat_with_agent,
    json_to_contract_text,
)

from azure.ai.inference.models import SystemMessage, UserMessage

# ------------ Configuration -----------------

load_dotenv()

OCR_ENDPOINT = os.getenv("AZURE_DOC_ENDPOINT", "https://legaldocint-ocr.cognitiveservices.azure.com/")
OCR_KEY = os.getenv("AZURE_DOC_KEY", "CsEQkm6aYpH89LC1EGpQlle0LHJbcX7ySG8rmEPeZ3TMpOrnt7R4JQQJ99BGACGhslBXJ3w3AAALACOGvqgF")

TMP = Path("tmp")
TMP.mkdir(exist_ok=True)

# ------------ FastAPI Application ------------------

app = FastAPI(title="Legal-AI Hub")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)



# Session storage for chat history
SESSIONS: dict[str, list] = {}  # {uid: chat-history}

# ------------ Pydantic Models ------------------

class ChatReq(BaseModel):
    id: str
    message: str

# ------------ API Endpoints ------------------

# @app.get("/")
# async def root():
#     """Root endpoint"""
#     return {"message": "Legal-AI Hub API is running"}

@app.post("/api/process")
async def process(pdf: UploadFile = File(...)):
    """Process PDF: OCR → Translate → AI Analysis"""
    uid = uuid.uuid4().hex[:8]
    
    try:
        # 1. OCR → tmp/{uid}_raw.json
        ocr_json = TMP / f"{uid}_raw.json"
        pdf_bytes = await pdf.read()
        ocr_bytes(pdf_bytes, OCR_ENDPOINT, OCR_KEY, ocr_json)
        
        # 2. Translate → tmp/{uid}_en.json
        en_json = TMP / f"{uid}_en.json"
        translate_file(ocr_json, en_json)
        
        # 3. Flatten JSON → plain English text
        text = json_to_contract_text(str(en_json))
        
        # 4. LLM analysis (risks + improved draft)
        analysis_str = analyse_contract_text(text)
        
        try:
            analysis_obj = json.loads(analysis_str)
        except json.JSONDecodeError:
            # If JSON parsing fails, return raw response
            analysis_obj = {"raw_response": analysis_str}
        
        # 5. Save chat context
        SESSIONS[uid] = [
            SystemMessage(content="You are an Indian contract-law expert."),
            UserMessage(content=f"Contract text: {text}"),
            UserMessage(content=f"Analysis: {analysis_str}"),
        ]
        
        return {"id": uid, "analysis": analysis_obj}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
async def chat(req: ChatReq):
    """Chat with AI agent about the analyzed contract"""
    if req.id not in SESSIONS:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        hist = SESSIONS[req.id]
        hist.append(UserMessage(content=req.message))
        
        ai_msg = chat_with_agent(hist)
        hist.append(ai_msg)
        
        # Keep last 12 messages to avoid token limits
        SESSIONS[req.id] = hist[-12:]
        
        return {"answer": ai_msg.content}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": "2025-01-01T00:00:00Z"}


# Mount static files (if static directory exists)
app.mount("/", StaticFiles(directory="static", html=True), name="static")

# ------------ Run Application ------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)