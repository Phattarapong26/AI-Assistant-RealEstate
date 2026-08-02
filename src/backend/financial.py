"""Context-Aware Financial Router.

Turns free-text financial signals ("จน", "งบน้อย", "เงินเดือน 20k", "งบ 3 ล้าน")
into a deterministic financial profile that the retrieval layer can filter on and
that the prompt layer can reason about. The LLM never guesses budgets by itself:
this module computes them, and the model only writes the narrative around them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# --- Signals ----------------------------------------------------------------
HARDSHIP_KEYWORDS = (
    "จน", "ไม่มีเงิน", "เงินไม่พอ", "งบน้อย", "งบจำกัด", "งบประหยัด",
    "ผ่อนไม่ไหว", "กู้ไม่ผ่าน", "ติดแบล็คลิสต์", "ติดแบล็กลิสต์", "เครดิตไม่ดี",
    "หนี้", "ถูกที่สุด", "ราคาถูก", "ราคาต่ำ", "รายได้น้อย", "เงินเดือนน้อย",
    "broke", "cheap", "tight budget", "low budget", "cannot afford",
)

READY_TO_BUY_KEYWORDS = (
    "พร้อมโอน", "จะซื้อ", "อยากซื้อเลย", "ตัดสินใจแล้ว", "เงินสด", "จองเลย",
    "นัดดู", "เข้าชมโครงการ", "ดูโครงการ", "มีเงินดาวน์", "พรีอนุมัติ",
    "pre-approved", "ready to buy", "cash buyer", "book now",
)

# Installment affordability band as a share of monthly income.
INSTALLMENT_MIN_RATIO = 0.35
INSTALLMENT_MAX_RATIO = 0.45
# Baht of monthly installment required per 1,000,000 THB borrowed (30y term).
INSTALLMENT_PER_MILLION_LOW = 6_000.0
INSTALLMENT_PER_MILLION_HIGH = 7_000.0
# Fallback ceiling when the customer only signals hardship without numbers.
HARDSHIP_PRICE_CEILING = 3_500_000.0
BUDGET_TOLERANCE = 1.10

MODE_CLOSING = "closing_specialist"
MODE_STRATEGIST = "financial_strategist"
MODE_ADVISOR = "discovery_advisor"


@dataclass
class FinancialProfile:
    """Everything the pipeline knows about the customer's money situation."""

    mode: str = MODE_ADVISOR
    hardship: bool = False
    ready_to_buy: bool = False
    monthly_income: Optional[float] = None
    stated_installment: Optional[float] = None
    stated_budget: Optional[float] = None
    installment_low: Optional[float] = None
    installment_high: Optional[float] = None
    loan_low: Optional[float] = None
    loan_high: Optional[float] = None
    price_ceiling: Optional[float] = None
    signals: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "hardship": self.hardship,
            "ready_to_buy": self.ready_to_buy,
            "monthly_income": self.monthly_income,
            "installment_low": self.installment_low,
            "installment_high": self.installment_high,
            "loan_low": self.loan_low,
            "loan_high": self.loan_high,
            "price_ceiling": self.price_ceiling,
            "signals": self.signals,
        }

    def summary_th(self) -> str:
        """A compact, factual briefing injected into the prompt."""
        parts: List[str] = []
        if self.monthly_income:
            parts.append(f"รายได้ต่อเดือนที่ลูกค้าบอก: {self.monthly_income:,.0f} บาท")
        if self.stated_installment:
            parts.append(f"ยอดผ่อนที่ลูกค้ารับไหว: {self.stated_installment:,.0f} บาทต่อเดือน")
        if self.installment_low and self.installment_high:
            parts.append(
                f"ยอดผ่อนที่เหมาะสมโดยประมาณ: {self.installment_low:,.0f}-{self.installment_high:,.0f} บาทต่อเดือน"
            )
        if self.loan_low and self.loan_high:
            parts.append(
                f"วงเงินกู้โดยประมาณ: {self.loan_low/1_000_000:.2f}-{self.loan_high/1_000_000:.2f} ล้านบาท "
                "(กู้ร่วมกับคู่สมรสหรือพ่อแม่จะเพิ่มวงเงินได้อีกราว 40-70%)"
            )
        if self.stated_budget:
            parts.append(f"งบที่ลูกค้าระบุ: {self.stated_budget:,.0f} บาท")
        if self.price_ceiling:
            parts.append(f"เพดานราคาทรัพย์ที่เสนอได้: ไม่เกิน {self.price_ceiling:,.0f} บาท")
        if self.hardship:
            parts.append("ลูกค้าส่งสัญญาณข้อจำกัดทางการเงิน ต้องเปิดด้วยความเข้าใจก่อนเสนอทรัพย์")
        if self.ready_to_buy:
            parts.append("ลูกค้าส่งสัญญาณพร้อมตัดสินใจ ให้เดินเรื่องนัดชมโครงการต่อ")
        if not parts:
            return "ยังไม่มีข้อมูลการเงินของลูกค้า ให้ถามอย่างนุ่มนวลในย่อหน้าสุดท้าย"
        return "\n".join(f"- {p}" for p in parts)


# --- Number parsing ----------------------------------------------------------
_NUM = r"(\d[\d,]*(?:\.\d+)?)"


def _to_float(raw: str) -> float:
    return float(raw.replace(",", ""))


def _scaled_amounts(text: str) -> List[float]:
    """Every money-looking amount in the text, normalised to baht."""
    amounts: List[float] = []
    for raw, unit in re.findall(rf"{_NUM}\s*(ล้าน|แสน|หมื่น|พัน|k|K|m|M|บาท)?", text):
        try:
            value = _to_float(raw)
        except ValueError:
            continue
        unit = unit or ""
        if unit == "ล้าน" or unit in ("m", "M"):
            value *= 1_000_000
        elif unit == "แสน":
            value *= 100_000
        elif unit == "หมื่น":
            value *= 10_000
        elif unit == "พัน" or unit in ("k", "K"):
            value *= 1_000
        amounts.append(value)
    return amounts


def _first_amount_after(text: str, keywords: tuple) -> Optional[float]:
    for keyword in keywords:
        match = re.search(rf"{keyword}[^\d]{{0,12}}{_NUM}\s*(ล้าน|แสน|หมื่น|พัน|k|K|m|M|บาท)?", text)
        if not match:
            continue
        found = _scaled_amounts(match.group(0)[len(keyword):])
        if found:
            return found[0]
    return None


def parse_price(value: Any) -> Optional[float]:
    """Best-effort conversion of a catalogue price cell into baht."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        return number * 1_000_000 if 0 < number < 1_000 else number
    text = str(value).strip()
    if not text:
        return None
    amounts = _scaled_amounts(text)
    if not amounts:
        return None
    price = amounts[0]
    # A bare "3.45" in a price column means 3.45 million baht.
    if price < 1_000:
        price *= 1_000_000
    return price


# --- Router ------------------------------------------------------------------
def build_financial_profile(query: str, history: List[Dict[str, str]]) -> FinancialProfile:
    """Read the conversation and produce a deterministic financial profile."""
    recent_user_text = " ".join(
        m.get("content", "") for m in history[-6:] if m.get("role") == "user"
    )
    text = f"{recent_user_text} {query}".lower()

    profile = FinancialProfile()
    profile.hardship = any(k in text for k in HARDSHIP_KEYWORDS)
    profile.ready_to_buy = any(k in text for k in READY_TO_BUY_KEYWORDS)
    if profile.hardship:
        profile.signals.append("hardship")
    if profile.ready_to_buy:
        profile.signals.append("ready_to_buy")

    income = _first_amount_after(text, ("เงินเดือน", "รายได้", "salary", "income"))
    if income and income < 1_000:  # "เงินเดือน 20" -> 20k
        income *= 1_000
    if income and 3_000 <= income <= 5_000_000:
        profile.monthly_income = income
        profile.signals.append("income")

    installment = _first_amount_after(text, ("ผ่อนเดือนละ", "ผ่อนไหว", "ผ่อน", "installment"))
    if installment and 1_000 <= installment <= 500_000:
        profile.stated_installment = installment
        profile.signals.append("installment")

    budget = _first_amount_after(text, ("งบประมาณ", "งบ", "ไม่เกิน", "budget", "ราคาไม่เกิน"))
    if budget and budget < 1_000:
        budget *= 1_000_000
    if budget and budget >= 100_000:
        profile.stated_budget = budget
        profile.signals.append("budget")

    if profile.monthly_income:
        profile.installment_low = round(profile.monthly_income * INSTALLMENT_MIN_RATIO, -2)
        profile.installment_high = round(profile.monthly_income * INSTALLMENT_MAX_RATIO, -2)
    if profile.stated_installment:
        profile.installment_low = profile.stated_installment * 0.9
        profile.installment_high = profile.stated_installment

    if profile.installment_low and profile.installment_high:
        profile.loan_low = profile.installment_low / INSTALLMENT_PER_MILLION_HIGH * 1_000_000
        profile.loan_high = profile.installment_high / INSTALLMENT_PER_MILLION_LOW * 1_000_000

    ceilings: List[float] = []
    if profile.stated_budget:
        ceilings.append(profile.stated_budget * BUDGET_TOLERANCE)
    if profile.loan_high:
        ceilings.append(profile.loan_high * 1.15)  # loan + typical down payment
    if profile.hardship and not ceilings:
        ceilings.append(HARDSHIP_PRICE_CEILING)
    if ceilings:
        profile.price_ceiling = min(ceilings)

    if profile.hardship or (profile.price_ceiling and profile.price_ceiling <= HARDSHIP_PRICE_CEILING):
        profile.mode = MODE_STRATEGIST
    elif profile.ready_to_buy or profile.stated_budget:
        profile.mode = MODE_CLOSING
    else:
        profile.mode = MODE_ADVISOR

    return profile


def rank_and_trim(
    properties: List[Dict[str, Any]],
    profile: FinancialProfile,
    limit: int = 3,
) -> List[Dict[str, Any]]:
    """Hybrid RAG guard: never hand the model more than `limit` candidates.

    Rows above the affordable ceiling are dropped; if that empties the list we
    fall back to the cheapest rows so the customer still gets a real answer.
    """
    if not properties:
        return []

    priced = [(p, parse_price(p.get("ราคา"))) for p in properties]

    if profile.price_ceiling:
        affordable = [p for p, price in priced if price is not None and price <= profile.price_ceiling]
        if affordable:
            return affordable[:limit]
        cheapest = sorted(
            (item for item in priced if item[1] is not None),
            key=lambda item: item[1],
        )
        if cheapest:
            return [p for p, _ in cheapest[:limit]]

    return properties[:limit]
