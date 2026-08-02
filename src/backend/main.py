"""AI Property Consultant API.

Flow of a customer question:
    1. the message is stored in the session,
    2. Gemini classifies the intent (greeting / property / other),
    3. for property questions the message is rewritten into a self-contained
       search query using the conversation so far,
    4. the query is embedded and matched against the property vector index,
    5. the retrieved rows are handed to Gemini inside a strictly-scoped prompt,
    6. the grounded answer and the source rows are returned to the UI.
"""

import io
import logging
import os
import secrets
import traceback
from typing import Any, Dict, List, Optional

import pandas as pd
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

from config import (  # noqa: E402  (env must be loaded first)
    ALLOWED_ORIGINS,
    CONSULTATION_STYLES,
    MAX_CONTEXT_PROPERTIES,
    MAX_RESULTS,
    MAX_UPLOAD_SIZE,
    REQUIRED_COLUMNS,
)
from auth import AuthError, user_store, create_token, verify_token  # noqa: E402
from financial import build_financial_profile, rank_and_trim  # noqa: E402
from formatting import enforce_paragraph_style  # noqa: E402
from language_models import GeminiUnavailableError, gemini  # noqa: E402
from prompts import (  # noqa: E402
    GREETING_SYSTEM_PROMPT,
    INTENT_SYSTEM_PROMPT,
    QUERY_REWRITE_SYSTEM_PROMPT,
    consultant_system_prompt,
    consultant_user_prompt,
    no_result_prompt,
)
from session_manager import session_manager  # noqa: E402
from vector_store import vector_store  # noqa: E402

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Property Consultant API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

AI_ERROR_MESSAGE = (
    "ตอนนี้ระบบผู้ช่วยเชื่อมต่อกับ AI ไม่สำเร็จ กรุณาลองใหม่อีกครั้งในอีกสักครู่"
)


# --- Request / response models ----------------------------------------------
class PropertyQuery(BaseModel):
    query: str
    consultation_style: str = "formal"
    session_id: Optional[str] = None
    chat_room_id: Optional[str] = None
    get_history: bool = False
    save_message: bool = True
    language: Optional[str] = None
    timestamp: Optional[int] = None


class ChatResponse(BaseModel):
    response: str
    session_id: str
    chat_room_id: Optional[str] = None
    properties: Optional[List[Dict[str, Any]]] = None
    messages: Optional[List[Dict[str, Any]]] = None
    financial_insight: Optional[Dict[str, Any]] = None


class UploadResponse(BaseModel):
    message: str
    file_id: str
    num_records: int


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    token: str
    user: Dict[str, Any]


def current_user(authorization: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    """Resolve the signed session token sent by the web app."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="กรุณาเข้าสู่ระบบก่อนใช้งาน")
    try:
        user_id = verify_token(authorization.split(" ", 1)[1].strip())
    except AuthError as exc:
        raise HTTPException(status_code=401, detail="เซสชันหมดอายุ กรุณาเข้าสู่ระบบใหม่") from exc

    user = user_store.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="ไม่พบบัญชีผู้ใช้นี้")
    return user


# --- Pipeline steps -----------------------------------------------------------
def classify_intent(query: str, history: List[Dict[str, str]]) -> str:
    """Ask the model what the customer is doing, with a safe default."""
    try:
        label = gemini.generate(
            prompt=f'ข้อความล่าสุดของผู้ใช้:\n"""{query}"""\n\nประเภท:',
            system_instruction=INTENT_SYSTEM_PROMPT,
            history=history[-4:],
            temperature=0.0,
            max_output_tokens=8,
        ).strip().lower()
    except GeminiUnavailableError:
        return "property"

    for candidate in ("greeting", "property", "other"):
        if candidate in label:
            return candidate
    return "property"


def build_search_query(query: str, history: List[Dict[str, str]]) -> str:
    """Fold the conversation into one self-contained search query."""
    if not history:
        return query
    try:
        rewritten = gemini.generate(
            prompt=f'ข้อความล่าสุดของลูกค้า:\n"""{query}"""\n\nคำค้นที่สมบูรณ์ในตัวเอง:',
            system_instruction=QUERY_REWRITE_SYSTEM_PROMPT,
            history=history,
            temperature=0.1,
            max_output_tokens=96,
        ).strip()
    except GeminiUnavailableError:
        return query
    return rewritten or query


def answer_property_question(
    query: str,
    style: str,
    history: List[Dict[str, str]],
) -> tuple[str, List[Dict[str, Any]], Dict[str, Any]]:
    """Financial routing -> hybrid retrieval -> grounded, paragraph-only answer."""
    profile = build_financial_profile(query, history)
    logger.info("Financial router: mode=%s signals=%s ceiling=%s",
                profile.mode, profile.signals, profile.price_ceiling)

    search_query = build_search_query(query, history)
    candidates = vector_store.search(search_query, top_k=MAX_RESULTS)
    logger.info("Retrieved %d candidates for query: %s", len(candidates), search_query)

    # Hybrid RAG guard: the model never sees more than MAX_CONTEXT_PROPERTIES rows.
    properties = rank_and_trim(candidates, profile, limit=MAX_CONTEXT_PROPERTIES)
    logger.info("Trimmed candidates from %d to %d", len(candidates), len(properties))

    system_instruction = consultant_system_prompt(style, profile.mode)
    if properties:
        prompt = consultant_user_prompt(query, properties, profile.summary_th())
    else:
        prompt = no_result_prompt(query, vector_store.catalogue_summary())

    answer = gemini.generate(
        prompt=prompt,
        system_instruction=system_instruction,
        history=history,
    )
    return enforce_paragraph_style(answer), properties, profile.to_dict()


def answer_greeting(query: str, history: List[Dict[str, str]]) -> str:
    return enforce_paragraph_style(
        gemini.generate(
            prompt=query,
            system_instruction=GREETING_SYSTEM_PROMPT,
            history=history[-4:],
            temperature=0.8,
            max_output_tokens=160,
        ),
        max_paragraphs=2,
    )


# --- Endpoints ----------------------------------------------------------------
@app.get("/")
async def root():
    return {"message": "AI Property Consultant API is running"}


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "ai_provider": "google-gemini",
        "chat_model": gemini.chat_model_name,
        "embedding_model": gemini.embedding_model_name,
        "ai_configured": gemini.is_ready,
        "indexed_properties": vector_store.size,
        "catalogue_file_id": vector_store.file_id,
    }


@app.get("/api/styles")
async def get_consultation_styles():
    return CONSULTATION_STYLES


@app.post("/api/auth/register", response_model=AuthResponse)
async def register(payload: RegisterRequest):
    try:
        user = user_store.register(payload.name, payload.email, payload.password)
        return AuthResponse(token=create_token(user["id"]), user=user)
    except AuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/auth/login", response_model=AuthResponse)
async def login(payload: LoginRequest):
    try:
        user = user_store.login(payload.email, payload.password)
        return AuthResponse(token=create_token(user["id"]), user=user)
    except AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@app.get("/api/auth/me")
async def me(user: Dict[str, Any] = Depends(current_user)):
    return user


@app.post("/api/chat", response_model=ChatResponse)
async def chat(query: PropertyQuery):
    session_id = session_manager.ensure_session(query.session_id or query.chat_room_id)

    # The UI reuses this endpoint to reload a conversation.
    if query.get_history or not query.query.strip():
        messages = session_manager.get_messages(session_id)
        return ChatResponse(
            response="",
            session_id=session_id,
            chat_room_id=session_id,
            messages=messages,
        )

    history = session_manager.get_history(session_id)
    session_manager.add_message(session_id, "user", query.query)

    style = query.consultation_style if query.consultation_style in CONSULTATION_STYLES else "formal"

    try:
        intent = classify_intent(query.query, history)
        if intent == "greeting":
            answer, properties, insight = answer_greeting(query.query, history), [], None
        else:
            answer, properties, insight = answer_property_question(query.query, style, history)
    except GeminiUnavailableError as exc:
        logger.error("Gemini unavailable: %s", exc)
        raise HTTPException(status_code=503, detail=AI_ERROR_MESSAGE) from exc
    except Exception as exc:  # noqa: BLE001
        logger.error("Chat pipeline failed: %s\n%s", exc, traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal server error") from exc

    session_manager.add_message(session_id, "assistant", answer, properties or None)

    return ChatResponse(
        response=answer,
        session_id=session_id,
        chat_room_id=session_id,
        properties=properties or None,
        financial_insight=insight,
    )


@app.post("/api/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    consultation_style: str = "formal",
    user: Dict[str, Any] = Depends(current_user),
):
    filename = file.filename or ""
    file_ext = filename.split(".")[-1].lower()
    if file_ext not in ("csv", "xlsx", "xls"):
        raise HTTPException(status_code=400, detail="รองรับเฉพาะไฟล์ CSV หรือ Excel เท่านั้น")

    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"ไฟล์มีขนาดใหญ่เกิน {MAX_UPLOAD_SIZE // (1024 * 1024)} MB",
        )

    try:
        if file_ext == "csv":
            df = pd.read_csv(io.BytesIO(content))
        else:
            df = pd.read_excel(io.BytesIO(content))
    except Exception as exc:  # noqa: BLE001
        logger.exception("Could not parse the uploaded file: %s", exc)
        raise HTTPException(status_code=400, detail="ไม่สามารถอ่านไฟล์นี้ได้ กรุณาตรวจสอบรูปแบบไฟล์") from exc

    df.columns = [str(c).strip() for c in df.columns]
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"ไฟล์ขาดคอลัมน์ที่จำเป็น: {', '.join(missing)}",
        )

    df = df.dropna(how="all")
    if df.empty:
        raise HTTPException(status_code=400, detail="ไฟล์นี้ไม่มีข้อมูลทรัพย์")

    records = df.fillna("ไม่มี").astype(object).to_dict("records")
    records = [{k: (str(v).strip() if not isinstance(v, (int, float)) else v) for k, v in r.items()} for r in records]

    logger.info("Catalogue upload by %s (%s)", user["email"], filename)
    file_id = f"upload_{secrets.token_hex(8)}"
    try:
        num_records = vector_store.replace_properties(records, file_id)
    except GeminiUnavailableError as exc:
        logger.error("Embedding failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="เชื่อมต่อบริการสร้างเวกเตอร์ของ Gemini ไม่สำเร็จ กรุณาตรวจสอบ GOOGLE_API_KEY แล้วลองใหม่",
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.error("Indexing failed: %s\n%s", exc, traceback.format_exc())
        raise HTTPException(status_code=500, detail="ประมวลผลไฟล์ไม่สำเร็จ") from exc

    return UploadResponse(
        message=f"อัปโหลดและสร้างดัชนีค้นหาสำเร็จ {num_records} รายการ",
        file_id=file_id,
        num_records=num_records,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
