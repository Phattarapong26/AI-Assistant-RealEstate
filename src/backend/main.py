from fastapi import FastAPI, UploadFile, File, HTTPException, Header, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import pandas as pd
import io
import logging
import os
from datetime import datetime, timedelta
import time
import secrets
import traceback
import random
import json
from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path
import re

# Load environment variables explicitly from backend .env
BACKEND_ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=BACKEND_ENV_PATH)

# Provider configuration
PROVIDER = os.getenv("PROVIDER", "openai").lower()

# Setup OpenAI client
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    logging.getLogger(__name__).warning("OPENAI_API_KEY is not set. Check src/backend/.env")
client = OpenAI(api_key=OPENAI_API_KEY)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Model configuration
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Optional: Google Gemini configuration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_MODEL = os.getenv("GOOGLE_MODEL", "gemini-1.5-flash")
genai = None
if PROVIDER == "google":
    try:
        import google.generativeai as genai  # type: ignore
        if not GOOGLE_API_KEY:
            logging.getLogger(__name__).warning("GOOGLE_API_KEY is not set. Check src/backend/.env")
        else:
            genai.configure(api_key=GOOGLE_API_KEY)
    except Exception as _e:
        logging.getLogger(__name__).exception(f"Failed to initialize Google Generative AI client: {_e}")


# Initialize FastAPI app
app = FastAPI(title="AI Property Consultant API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins in development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create models for request/response
class PropertyQuery(BaseModel):
    query: str
    consultation_style: str = "formal"
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str
    properties: Optional[List[Dict[str, Any]]] = None

class UploadResponse(BaseModel):
    message: str
    file_id: str
    num_records: int

# Mock database for development
property_data = []
user_sessions = {}

# Consultation styles with Thai descriptions
CONSULTATION_STYLES = {
    "formal": "ทางการ", 
    "casual": "ทั่วไป", 
    "friendly": "เป็นกันเอง", 
    "professional": "มืออาชีพ"
}

# Simulated vector search function
def vector_search(query: str, top_k: int = 3):
    """
    Simulate vector search in the property database
    Returns relevant properties based on the query
    """
    if not property_data:
        return []
    
    # In a real implementation, this would use embedding similarity
    # For now, we'll just do a simple keyword match
    keywords = query.lower().split()
    scored_items = []
    
    for item in property_data:
        score = 0
        item_text = json.dumps(item, ensure_ascii=False).lower()
        
        for keyword in keywords:
            if keyword in item_text:
                score += 1
                
        if score > 0:
            scored_items.append((item, score))
    
    # Sort by score and take top_k
    scored_items.sort(key=lambda x: x[1], reverse=True)
    return [item[0] for item in scored_items[:top_k]]

# Format property response based on missing data
def format_property_response(properties):
    """
    Formats property data by removing fields with value 'ไม่มี'
    """
    formatted = []
    for prop in properties:
        formatted_prop = {}
        for key, value in prop.items():
            if value != "ไม่มี":
                formatted_prop[key] = value
        formatted.append(formatted_prop)
    return formatted

# Simple greeting intent detection
GREETING_PATTERNS = re.compile(r"\b(สวัสดี|หวัดดี|ฮัลโหล|ทักทาย|ไงบ้าง|ไง|เฮลโล่|hello|hi|hey)\b", re.IGNORECASE)

def is_greeting_intent(text: str) -> bool:
    if not text:
        return False
    return GREETING_PATTERNS.search(text) is not None

def generate_greeting_response(query: str, style: str, session_id: Optional[str] = None) -> str:
    try:
        # Keep tone friendly and short; avoid sales push
        system_instructions = (
            "คุณคือผู้ช่วยสนทนาภาษาไทยที่เป็นกันเองและสุภาพ ตอบรับคำทักทายอย่างเป็นธรรมชาติ "
            "ต่อบทสนทนาอย่างยืดหยุ่นและถามต่ออย่างเหมาะสม โดยไม่เร่งขายหรือโฆษณา. "
            "ห้ามใช้คำลงท้ายที่ระบุเพศ เช่น 'ค่ะ', 'ครับ', 'คะ'. "
            "ให้ใช้ภาษากลางที่เป็นกลางทางเพศ เช่น จบประโยคแบบเรียบง่ายหรือด้วยคำว่า 'นะ' ตามความเหมาะสม"
        )

        if PROVIDER == "google":
            if genai is None or not GOOGLE_API_KEY:
                raise RuntimeError("Google provider selected but GOOGLE_API_KEY or client is not initialized")
            model = genai.GenerativeModel(
                GOOGLE_MODEL,
                system_instruction=system_instructions,
            )
            contents = []
            if session_id and session_id in user_sessions:
                for item in user_sessions[session_id].get("queries", [])[-4:]:
                    prev_q = item.get("query")
                    if prev_q:
                        contents.append({"role": "user", "parts": [prev_q]})
            contents.append({"role": "user", "parts": [query]})
            gemini_resp = model.generate_content(
                contents=contents,
                generation_config={
                    "temperature": 0.9,
                    "max_output_tokens": 180,
                },
            )
            answer = getattr(gemini_resp, "text", None) or ""
            answer = answer.strip()
            if not answer:
                answer = "สวัสดี มีอะไรให้ช่วยไหม"
            return answer
        else:
            response = client.responses.create(
                model=OPENAI_MODEL,
                input=query,
                instructions=system_instructions,
                max_output_tokens=180,
                temperature=0.9,
                store=False,
            )
            answer = getattr(response, "output_text", None)
            if not answer:
                try:
                    parts = []
                    output = getattr(response, "output", None)
                    if isinstance(output, list):
                        for item in output:
                            if isinstance(item, dict) and item.get("type") == "output_text":
                                parts.append(item.get("text", ""))
                    answer = "".join(parts).strip()
                except Exception:
                    answer = ""
            if not answer:
                answer = "สวัสดี มีอะไรให้ช่วยไหม"
            return answer
    except Exception as e:
        logger.exception(f"Greeting path error: {e.__class__.__name__}: {str(e)}")
        return "สวัสดี มีอะไรให้ช่วยไหม"

# Generate AI response based on consultation style
def generate_ai_response(query: str, properties: List[Dict[str, Any]], style: str, session_id: Optional[str] = None):
    """
    Generate AI response using OpenAI ChatGPT API as a top real estate closer
    """
    try:
        # Compose prompt
        property_text = "\n".join([
            f"{i+1}. {json.dumps(prop, ensure_ascii=False)}" for i, prop in enumerate(properties)
        ])
        prompt = (
            f"คุณคือเซลล์อสังหาริมทรัพย์มืออาชีพที่ยอดเยี่ยมที่สุดในไทย "
            f"มีความสามารถในการโน้มน้าวและปิดการขายได้เก่งมาก "
            f"ตอบคำถามลูกค้าแบบกระตุ้นความสนใจและเน้นข้อดีของแต่ละอสังหาฯ "
            f"ใช้ภาษาที่มั่นใจ มีความเป็นมืออาชีพ และเน้นปิดการขายให้ได้มากที่สุด "
            f"User query: {query}\nProperties:\n{property_text}\nStyle: {style}\nกรุณาตอบเป็นภาษาไทยและเน้นปิดการขาย"
        )

        # Build system instructions
        system_instructions = (
            "คุณคือเซลล์อสังหาริมทรัพย์ยอดนักปิดการขายในไทย ตอบแบบมืออาชีพ "
            "โน้มน้าวและกระตุ้นให้ลูกค้าตัดสินใจซื้อ เน้นข้อดีและความคุ้มค่า "
            "ปิดการขายให้ได้มากที่สุด ตอบเป็นภาษาไทยและใช้ style: " + style + ". "
            "ห้ามใช้คำลงท้ายที่ระบุเพศ เช่น 'ค่ะ', 'ครับ', 'คะ'. ให้ใช้ภาษากลางเป็นกลางทางเพศ"
        )

        # Branch by provider
        if PROVIDER == "google":
            if genai is None or not GOOGLE_API_KEY:
                raise RuntimeError("Google provider selected but GOOGLE_API_KEY or client is not initialized")
            # Build Gemini model with system instruction and higher temperature
            model = genai.GenerativeModel(
                GOOGLE_MODEL,
                system_instruction=system_instructions,
            )

            # Build conversation contents from history (if available)
            contents = []
            if session_id and session_id in user_sessions:
                for item in user_sessions[session_id].get("queries", [])[-8:]:  # last 8 turns
                    prev_q = item.get("query")
                    if prev_q:
                        contents.append({"role": "user", "parts": [prev_q]})
            # Add current context and query
            contents.append({"role": "user", "parts": [
                "บริบทอสังหาฯ:\n" + property_text + "\n\nคำถามล่าสุด:\n" + query
            ]})

            gemini_resp = model.generate_content(
                contents=contents,
                generation_config={
                    "temperature": 0.95,
                    "max_output_tokens": 512,
                },
            )
            answer = getattr(gemini_resp, "text", None) or ""
            answer = answer.strip()
            if not answer:
                answer = "ขออภัย เกิดข้อผิดพลาดในการเชื่อมต่อ AI"
        else:
            # Default: OpenAI Responses API
            response = client.responses.create(
                model=OPENAI_MODEL,
                input=prompt,
                instructions=system_instructions,
                max_output_tokens=512,
                temperature=0.7,
                store=False,
            )

            # Extract text from Responses API result
            answer = getattr(response, "output_text", None)
            if not answer:
                # Fallback: try to concatenate textual outputs
                try:
                    parts = []
                    output = getattr(response, "output", None)
                    if isinstance(output, list):
                        for item in output:
                            if isinstance(item, dict) and item.get("type") == "output_text":
                                parts.append(item.get("text", ""))
                    answer = "".join(parts).strip()
                except Exception:
                    answer = ""
            if not answer:
                answer = "ขออภัย เกิดข้อผิดพลาดในการเชื่อมต่อ AI"
        return answer
    except Exception as e:
        logger.exception(f"OpenAI API error: {e.__class__.__name__}: {str(e)}")
        if os.getenv("DEBUG_AI") == "1":
            return f"AI error ({e.__class__.__name__}): {str(e)}"
        return "ขออภัย เกิดข้อผิดพลาดในการเชื่อมต่อ AI"

@app.get("/")
async def root():
    return {"message": "AI Property Consultant API is running"}

@app.post("/api/chat", response_model=ChatResponse)
async def chat(query: PropertyQuery):
    try:
        # Generate or retrieve session ID
        session_id = query.session_id
        if not session_id:
            session_id = f"session_{secrets.token_hex(8)}"
            user_sessions[session_id] = {
                "created_at": datetime.now(),
                "queries": []
            }
        elif session_id not in user_sessions:
            user_sessions[session_id] = {
                "created_at": datetime.now(),
                "queries": []
            }
        
        # Log the query
        user_sessions[session_id]["queries"].append({
            "query": query.query,
            "timestamp": datetime.now()
        })
        
        # Greeting fast-path (no sales push)
        if is_greeting_intent(query.query):
            response = generate_greeting_response(query.query, query.consultation_style, session_id)
            return ChatResponse(
                response=response,
                session_id=session_id,
                properties=None
            )

        # Search for relevant properties for non-greeting intents
        relevant_properties = vector_search(query.query)
        formatted_properties = format_property_response(relevant_properties)
        
        # Generate AI response
        response = generate_ai_response(
            query.query, 
            formatted_properties, 
            query.consultation_style,
            session_id,
        )
        logger.info("Chat response: %s", (response[:200] + '...') if isinstance(response, str) and len(response) > 200 else response)
        
        return ChatResponse(
            response=response,
            session_id=session_id,
            properties=formatted_properties if formatted_properties else None
        )
        
    except Exception as e:
        logger.error(f"Error processing chat request: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...), consultation_style: str = "formal"):
    try:
        global property_data
        
        # Validate file type
        file_ext = file.filename.split('.')[-1].lower()
        if file_ext not in ['csv', 'xlsx', 'xls']:
            raise HTTPException(status_code=400, detail="Only CSV or Excel files are accepted")
        
        # Read the file content
        content = await file.read()
        
        if file_ext == 'csv':
            df = pd.read_csv(io.BytesIO(content))
        else:  # Excel file
            df = pd.read_excel(io.BytesIO(content))
            
        # Validate expected columns
        expected_columns = [
            'ประเภท', 'โครงการ', 'ราคา', 'รูปแบบ', 'รูป', 'ตำแหน่ง', 
            'สถานศึกษา', 'สถานีรถไฟฟ้า', 'ห้างสรรพสินค้า', 'โรงพยาบาล', 'สนามบิน'
        ]
        
        for col in expected_columns:
            if col not in df.columns:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Missing required column: {col}"
                )
                
        # Convert DataFrame to list of dicts for our database
        property_data = df.fillna("ไม่มี").to_dict('records')
        
        # Generate a unique file ID
        file_id = f"upload_{secrets.token_hex(8)}"
        
        return UploadResponse(
            message="อัพโหลดข้อมูลอสังหาริมทรัพย์สำเร็จ",
            file_id=file_id,
            num_records=len(property_data)
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error processing file upload: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Error processing file: " + str(e))

@app.get("/api/styles")
async def get_consultation_styles():
    return CONSULTATION_STYLES

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
