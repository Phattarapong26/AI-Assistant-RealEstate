"""Property vector store backed by real Gemini embeddings.

Each uploaded row (CSV/Excel) becomes one document: a natural-language
description of the property. That description is embedded with Gemini and
stored together with the original row, so retrieval returns both a similarity
score and the exact source data used to answer the customer.

The index is persisted to disk so a server restart does not lose the data
that the sales team uploaded.
"""

import json
import logging
import threading
from typing import Any, Dict, List, Optional

import numpy as np

from config import (
    EMPTY_VALUES,
    KEYWORD_BOOST,
    MAX_RESULTS,
    SEARCHABLE_COLUMNS,
    VECTOR_INDEX_PATH,
    VECTOR_META_PATH,
    VECTOR_SIMILARITY_THRESHOLD,
)
from language_models import GeminiClient, gemini

logger = logging.getLogger(__name__)


def is_empty(value: Any) -> bool:
    return value is None or str(value).strip() in EMPTY_VALUES


def clean_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """Drop empty/placeholder fields so the model never sees noise."""
    return {k: v for k, v in record.items() if not is_empty(v) and not str(k).startswith("_")}


def build_document(record: Dict[str, Any]) -> str:
    """Turn one property row into a sentence-like document for embedding.

    Field names are kept in the text ("ราคา 3500000 บาท") because the embedding
    model uses them as semantic anchors - a bare list of values retrieves badly.
    """
    clean = clean_record(record)
    parts: List[str] = []

    prop_type = clean.get("ประเภท")
    project = clean.get("โครงการ")
    if prop_type or project:
        parts.append(f"{prop_type or 'อสังหาริมทรัพย์'} โครงการ {project or 'ไม่ระบุชื่อ'}")

    if "ราคา" in clean:
        parts.append(f"ราคา {clean['ราคา']} บาท")
    if "รูปแบบ" in clean:
        parts.append(f"รูปแบบ {clean['รูปแบบ']}")
    if "ตำแหน่ง" in clean:
        parts.append(f"ทำเล {clean['ตำแหน่ง']}")

    nearby_labels = {
        "สถานศึกษา": "ใกล้สถานศึกษา",
        "สถานีรถไฟฟ้า": "ใกล้สถานีรถไฟฟ้า",
        "ห้างสรรพสินค้า": "ใกล้ห้างสรรพสินค้า",
        "โรงพยาบาล": "ใกล้โรงพยาบาล",
        "สนามบิน": "ใกล้สนามบิน",
    }
    for column, label in nearby_labels.items():
        if column in clean:
            parts.append(f"{label} {clean[column]}")

    # Any extra column the customer added to their sheet still gets indexed.
    known = set(SEARCHABLE_COLUMNS) | {"ราคา", "รูป"}
    for key, value in clean.items():
        if key not in known:
            parts.append(f"{key} {value}")

    return " | ".join(parts)


class VectorStore:
    """Cosine-similarity search over Gemini embeddings, persisted to disk."""

    def __init__(self, client: Optional[GeminiClient] = None):
        self.client = client or gemini
        self._lock = threading.Lock()
        self.vectors: np.ndarray = np.zeros((0, 0), dtype=np.float32)
        self.records: List[Dict[str, Any]] = []
        self.documents: List[str] = []
        self.file_id: Optional[str] = None
        self.load()

    # --- Persistence --------------------------------------------------------
    def load(self) -> None:
        try:
            if VECTOR_INDEX_PATH.exists() and VECTOR_META_PATH.exists():
                self.vectors = np.load(VECTOR_INDEX_PATH)["vectors"].astype(np.float32)
                meta = json.loads(VECTOR_META_PATH.read_text(encoding="utf-8"))
                self.records = meta.get("records", [])
                self.documents = meta.get("documents", [])
                self.file_id = meta.get("file_id")
                logger.info("Loaded %d properties from the saved index", len(self.records))
        except Exception as exc:  # noqa: BLE001 - a broken index must not block startup
            logger.exception("Could not load the saved index, starting empty: %s", exc)
            self.clear(persist=False)

    def save(self) -> None:
        np.savez_compressed(VECTOR_INDEX_PATH, vectors=self.vectors)
        VECTOR_META_PATH.write_text(
            json.dumps(
                {
                    "file_id": self.file_id,
                    "records": self.records,
                    "documents": self.documents,
                    "embedding_model": self.client.embedding_model_name,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def clear(self, persist: bool = True) -> None:
        self.vectors = np.zeros((0, 0), dtype=np.float32)
        self.records = []
        self.documents = []
        self.file_id = None
        if persist:
            self.save()

    # --- Indexing -----------------------------------------------------------
    def replace_properties(self, records: List[Dict[str, Any]], file_id: str) -> int:
        """Embed and index a freshly uploaded file, replacing the old catalogue."""
        documents = [build_document(r) for r in records]
        keep = [i for i, doc in enumerate(documents) if doc.strip()]
        if not keep:
            raise ValueError("ไม่พบข้อมูลที่ใช้งานได้ในไฟล์ที่อัปโหลด")

        records = [records[i] for i in keep]
        documents = [documents[i] for i in keep]

        raw = self.client.embed_documents(documents)
        vectors = np.asarray(raw, dtype=np.float32)
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        vectors = vectors / norms  # pre-normalise: cosine becomes a dot product

        with self._lock:
            self.vectors = vectors
            self.records = records
            self.documents = documents
            self.file_id = file_id
            self.save()

        logger.info("Indexed %d properties (file_id=%s)", len(records), file_id)
        return len(records)

    # --- Retrieval ----------------------------------------------------------
    def search(
        self,
        query: str,
        top_k: int = MAX_RESULTS,
        threshold: float = VECTOR_SIMILARITY_THRESHOLD,
    ) -> List[Dict[str, Any]]:
        """Hybrid search: cosine similarity plus a small exact-keyword boost."""
        if not self.records or self.vectors.size == 0 or not query.strip():
            return []

        query_vector = np.asarray(self.client.embed_query(query), dtype=np.float32)
        norm = np.linalg.norm(query_vector) or 1.0
        query_vector = query_vector / norm

        scores = self.vectors @ query_vector

        # Exact term overlap is a strong signal for project names and districts,
        # which embeddings alone can blur together.
        terms = [t for t in query.lower().split() if len(t) > 1]
        if terms and KEYWORD_BOOST:
            boosts = np.zeros(len(self.documents), dtype=np.float32)
            for i, doc in enumerate(self.documents):
                lowered = doc.lower()
                boosts[i] = sum(1 for t in terms if t in lowered)
            scores = scores + KEYWORD_BOOST * boosts

        order = np.argsort(-scores)[: max(top_k, 1)]
        results: List[Dict[str, Any]] = []
        for idx in order:
            score = float(scores[idx])
            if score < threshold:
                continue
            record = clean_record(self.records[int(idx)])
            record["similarity_score"] = round(score, 4)
            results.append(record)
        return results

    # --- Introspection ------------------------------------------------------
    @property
    def size(self) -> int:
        return len(self.records)

    def catalogue_summary(self, max_projects: int = 8) -> str:
        """A short factual overview, used when nothing matches the query."""
        if not self.records:
            return "ยังไม่มีข้อมูลทรัพย์ในระบบ (ทีมงานยังไม่ได้อัปโหลดไฟล์)"

        types, projects, prices = [], [], []
        for record in self.records:
            clean = clean_record(record)
            if clean.get("ประเภท") and clean["ประเภท"] not in types:
                types.append(str(clean["ประเภท"]))
            if clean.get("โครงการ") and clean["โครงการ"] not in projects:
                projects.append(str(clean["โครงการ"]))
            try:
                prices.append(float(str(clean.get("ราคา", "")).replace(",", "")))
            except (TypeError, ValueError):
                pass

        lines = [f"- จำนวนทรัพย์ทั้งหมด {len(self.records)} รายการ"]
        if types:
            lines.append(f"- ประเภทที่มี: {', '.join(types[:10])}")
        if projects:
            shown = ", ".join(projects[:max_projects])
            more = f" และอีก {len(projects) - max_projects} โครงการ" if len(projects) > max_projects else ""
            lines.append(f"- ตัวอย่างโครงการ: {shown}{more}")
        if prices:
            lines.append(f"- ช่วงราคา: {min(prices):,.0f} - {max(prices):,.0f} บาท")
        return "\n".join(lines)


# Shared singleton used by the API layer.
vector_store = VectorStore()
