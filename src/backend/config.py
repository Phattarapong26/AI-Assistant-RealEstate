"""Central configuration for the AI Property Consultant backend.

Everything is driven by environment variables (see .env.example) so the same
codebase runs unchanged in development and production.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

# --- Google Gemini (the only AI provider used by this system) ---------------
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GEMINI_CHAT_MODEL = os.getenv("GEMINI_CHAT_MODEL", "gemini-2.5-flash")
GEMINI_EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")
GEMINI_TEMPERATURE = float(os.getenv("GEMINI_TEMPERATURE", "0.6"))
GEMINI_MAX_OUTPUT_TOKENS = int(os.getenv("GEMINI_MAX_OUTPUT_TOKENS", "3072"))
EMBEDDING_BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", "64"))

# --- Storage ----------------------------------------------------------------
MONGODB_URL = os.getenv("MONGODB_URL", "")
MONGODB_DB = os.getenv("MONGODB_DB", "AI")
VECTOR_INDEX_PATH = DATA_DIR / "property_index.npz"
VECTOR_META_PATH = DATA_DIR / "property_index.json"

# --- Retrieval tuning -------------------------------------------------------
VECTOR_SIMILARITY_THRESHOLD = float(os.getenv("VECTOR_SIMILARITY_THRESHOLD", "0.45"))
MAX_RESULTS = int(os.getenv("MAX_RESULTS", "5"))
# Hard cap on rows handed to the LLM (Hybrid RAG anti data-dump guard).
MAX_CONTEXT_PROPERTIES = int(os.getenv("MAX_CONTEXT_PROPERTIES", "4"))
KEYWORD_BOOST = float(os.getenv("KEYWORD_BOOST", "0.06"))
MAX_HISTORY_TURNS = int(os.getenv("MAX_HISTORY_TURNS", "8"))

# --- Domain -----------------------------------------------------------------
LANGUAGE_OPTIONS = ["th", "en"]

CONSULTATION_STYLES = {
    "formal": "ทางการ",
    "casual": "ทั่วไป",
    "friendly": "เป็นกันเอง",
    "professional": "มืออาชีพ",
}

# Columns that must exist in an uploaded CSV/Excel file.
REQUIRED_COLUMNS = ["ประเภท", "โครงการ", "ราคา"]

# Columns that are used (when present) to build the searchable text of a row.
SEARCHABLE_COLUMNS = [
    "ประเภท", "โครงการ", "รูปแบบ", "ตำแหน่ง",
    "สถานศึกษา", "สถานีรถไฟฟ้า", "ห้างสรรพสินค้า", "โรงพยาบาล", "สนามบิน",
]

EMPTY_VALUES = {"ไม่มี", "-", "", "nan", "NaN", "None", "null"}

# --- API --------------------------------------------------------------------
API_KEY_NAME = "X-API-Key"
API_KEY = os.getenv("API_KEY", "")
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",") if o.strip()]
MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", str(20 * 1024 * 1024)))
