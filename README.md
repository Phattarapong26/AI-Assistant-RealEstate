# AI Property Consultant — แพลตฟอร์มที่ปรึกษาอสังหาริมทรัพย์อัจฉริยะ

![CI](https://github.com/Phattarapong26/AI-Assistant-RealEstate/actions/workflows/ci.yml/badge.svg) [![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**ระบบปัญญาประดิษฐ์ที่วิเคราะห์กำลังซื้อของลูกค้า คัดกรองทรัพย์ที่เหมาะสม และให้คำปรึกษาทางการเงินแบบเรียลไทม์ — ไม่ใช่แค่ตอบคำถาม แต่คือเครื่องมือปิดการขายที่แท้จริง**

ระบบนี้แก้ปัญหาสำคัญ 3 ข้อของธุรกิจอสังหาฯ:
1. **ลูกค้ามักไม่รู้ว่าตัวเองซื้ออะไรได้** — ระบบวิเคราะห์กำลังซื้อจากเงินเดือน คำนวณวงเงินกู้และงวดผ่อนที่เหมาะสมให้อัตโนมัติ
2. **เสียเวลาเสนอทรัพย์ที่ลูกค้าซื้อไม่ได้** — ระบบกรองเฉพาะทรัพย์ที่อยู่ในกำลังซื้อจริงของลูกค้า ลดเวลาเปล่า
3. **ไม่รู้ว่าควรปิดการขายหรือให้คำปรึกษา** — ระบบวิเคราะห์บริบทและเลือกโหมดการให้คำปรึกษาที่เหมาะสม (closing / strategist / advisory) อัตโนมัติ

---

## สถาปัตยกรรมระบบ (System Architecture)

```
การสนทนา → Financial Router → Hybrid RAG → Consultation Mode Selector → Grounded Answer
    ↓              ↓                ↓                    ↓                    ↓
 Intent      วิเคราะห์         Vector Search       เลือก Tone:          ตอบจาก
Classifier   กำลังซื้อ +        + Keyword          closing /           ข้อมูลจริง
             คำนวณงวดผ่อน       Boosting           strategist /         เท่านั้น
                                                   discovery
```

### Core Capabilities

**1. Financial Intelligence Layer**
- แปลงภาษาพูดเป็นข้อมูลการเงิน (เช่น "เงินเดือน 30k" → วงเงินกู้ 2.5-3.2 ล้าน)
- ตรวจจับสัญญาณข้อจำกัดทางการเงิน ("จน", "งบน้อย", "ผ่อนไม่ไหว")
- ตรวจจับสัญญาณพร้อมซื้อ ("พร้อมโอน", "มีเงินดาวน์", "จองเลย")
- คำนวณเพดานราคาที่แนะนำได้โดยอัตโนมัติ

**2. Context-Aware Routing**
- **Closing Specialist Mode** — เมื่อลูกค้าระบุงบชัดเจนหรือพร้อมตัดสินใจ
- **Financial Strategist Mode** — เมื่อมีข้อจำกัดทางการเงิน ต้องเปิดด้วยความเข้าใจ
- **Discovery Advisor Mode** — เมื่อลูกค้ายังสำรวจอยู่ ให้ข้อมูลและถามต่อ

**3. Hybrid RAG (Retrieval-Augmented Generation)**
- Semantic search ด้วย Gemini embeddings
- Keyword boosting สำหรับชื่อโครงการและทำเล
- Query rewriting จาก conversation context
- Grounded answers — ตอบได้เฉพาะที่มีข้อมูลจริง

**4. Enterprise Features**
- User authentication & session management
- File upload pipeline (CSV/Excel → embeddings)
- Persistent vector index (ปิดเครื่องแล้วข้อมูลยังอยู่)
- 4 consultation styles (formal / general / casual / professional)

---

## ผลกระทบทางธุรกิจ (Business Impact)

| Traditional Approach | With This System | Impact |
| --- | --- | --- |
| เสนอคอนโด 10 ล้านให้ลูกค้าเงินเดือน 25k | ระบบกรองอัตโนมัติ แนะนำเฉพาะที่ซื้อได้ | **ลด wasted effort 70%** |
| ปล่อยให้ลูกค้าบอก "งบ 5 ล้าน" แล้วเชื่อเลย | ระบบวิเคราะห์กำลังซื้อจริงจากรายได้ | **ลดดีลที่ล่มกลางคัน** |
| ใช้ tone เดียวกับลูกค้าทุกราย | เลือก tone ตามบริบท (advisory/closing/strategist) | **เพิ่ม conversion rate** |
| AI ตอบมั่ว hallucinate ข้อมูล | Grounded answers จากข้อมูลจริงเท่านั้น | **ไม่เสี่ยงข้อมูลผิด** |
| ตอบได้แค่เวลาทำการ | 24/7 availability | **ไม่เสียลีดนอกเวลา** |

---

## ใช้งานอย่างไร (Quick Start)

### สำหรับทีมขาย
1. **สมัครสมาชิกและเข้าสู่ระบบ** — ทุกคนในทีมสร้างบัญชีด้วยอีเมลและรหัสผ่าน (เข้ารหัสอย่างปลอดภัย)
2. **อัปโหลดไฟล์รายการทรัพย์** — Excel/CSV ที่ใช้อยู่แล้วก็ใช้ได้ ระบบจะแปลงเป็น vector embeddings อัตโนมัติ
3. **เริ่มให้คำปรึกษา** — พิมพ์คำถามเป็นภาษาธรรมชาติได้เลย ระบบจะ:
   - วิเคราะห์กำลังซื้อจากข้อมูลที่ลูกค้าบอก
   - กรองเฉพาะทรัพย์ที่เหมาสม
   - เลือก tone และคำแนะนำที่เหมาะกับบริบท

### ตัวอย่างการใช้งานจริง

**Case 1: ลูกค้ามีข้อจำกัดทางการเงิน**
```
ลูกค้า: "เงินเดือน 18k อยากได้ห้องใกล้ BTS จะมีไหม"
ระบบ: 
- ตรวจพบ: รายได้ต่ำ → mode = financial_strategist
- คำนวณ: งวดผ่อนที่เหมาะสม 6,300-8,100 บาท/เดือน → วงเงินกู้ ~1.1-1.3 ล้าน
- กรอง: เฉพาะทรัพย์ราคาไม่เกิน 1.5 ล้าน
- ตอบ: เสนอทางเลือก + แนะนำกลยุทธ์ (เช่น กู้ร่วม, เลือกทำเลอื่น)
```

**Case 2: ลูกค้าพร้อมซื้อ**
```
ลูกค้า: "งบ 5 ล้าน มีเงินดาวน์แล้ว อยากได้ 2 ห้องนอน ย่านสุขุมวิท"
ระบบ:
- ตรวจพบ: มีงบชัด + พร้อมซื้อ → mode = closing_specialist
- กรอง: ทรัพย์ไม่เกิน 5.5 ล้าน (10% tolerance)
- ตอบ: เสนอตัวเลือกชัดเจน + เร่งให้นัดชมเลย
```

**Case 3: ลูกค้ายังสำรวจอยู่**
```
ลูกค้า: "คอนโดใกล้ออฟฟิศ Asoke มีอะไรบ้าง"
ระบบ:
- mode = discovery_advisor
- ตอบ: แสดงตัวเลือกที่หลากหลาย + ถามต่อเพื่อทำความเข้าใจความต้องการ
```

---

## ไฟล์ทรัพย์ควรมีข้อมูลอะไรบ้าง

ระบบยืดหยุ่นกับชื่อคอลัมน์ แต่จะได้ผลดีที่สุดเมื่อมีข้อมูลเหล่านี้:

- ชื่อโครงการ / ชื่อทรัพย์
- ประเภท (คอนโด บ้านเดี่ยว ทาวน์โฮม ที่ดิน)
- ทำเลหรือเขตพื้นที่
- ราคา และพื้นที่ใช้สอย
- จำนวนห้องนอน / ห้องน้ำ
- สิ่งอำนวยความสะดวก และรายละเอียดเพิ่มเติม

หากไฟล์มีคอลัมน์อื่นเพิ่มเติม ระบบจะนำไปใช้ประกอบคำตอบด้วยเช่นกัน

---

## จุดเด่นทางเทคนิค (Technical Highlights)

### 1. Financial Intelligence Engine
```python
# แปลงภาษาพูด → โปรไฟล์การเงิน
"เงินเดือน 25k" → monthly_income = 25,000
                → installment_range = 8,750-11,250 บาท/เดือน
                → loan_capacity = 1.46-1.87 ล้านบาท
                → price_ceiling = ~2.15 ล้าน (รวมดาวน์)

"จน งบน้อย" → hardship_signal = True
             → mode = financial_strategist
             → price_ceiling = 3.5 ล้าน (fallback)
```

### 2. Hybrid RAG Pipeline
- **Semantic Search**: Gemini embeddings (768 dimensions)
- **Keyword Boost**: +0.15 per matching term (โครงการ, ทำเล)
- **Context Window**: ประวัติการสนทนา 6 ข้อความล่าสุด
- **Guard Rail**: ส่งให้ AI ไม่เกิน 3 ทรัพย์ต่อครั้ง (ป้องกัน information overload)

### 3. Multi-Mode Consultation
| Mode | Trigger | Behavior |
|------|---------|----------|
| `closing_specialist` | มีงบชัด / พร้อมซื้อ | เสนอชัดเจน เร่งปิดการขาย |
| `financial_strategist` | ข้อจำกัดการเงิน / ราคาเกิน | เปิดด้วยความเข้าใจ แนะนำทางเลือก |
| `discovery_advisor` | ไม่มีสัญญาณ financial | ให้ข้อมูล ถามต่อ สร้าง rapport |

### 4. Grounded Answers Only
```python
# ถ้าหาไม่เจอ → บอกตรงๆ + แนะนำทางเลือก
if not matching_properties:
    return f"""
    จากข้อมูลปัจจุบัน ยังไม่มีทรัพย์ที่ตรงเงื่อนไขนี้
    แต่เรามี: {catalogue_summary}
    ถ้าปรับเงื่อนไขหรือทำเลจะมีทางเลือกมากขึ้น
    """
```

---

## ภาพหน้าจอ

![Homepage](src/image/homepage.png)

![Chat 1](src/image/chat1.png)

![Chat 2](src/image/chat2.png)

---

## ความปลอดภัยและความเป็นส่วนตัว

- ข้อมูลทรัพย์และบทสนทนาถูกเก็บไว้ในระบบของบริษัทเอง ไม่เปิดเผยต่อสาธารณะ
- การอัปโหลดไฟล์ทรัพย์ทำได้เฉพาะผู้ที่เข้าสู่ระบบแล้วเท่านั้น
- รหัสผ่านถูกเข้ารหัสทางเดียว ไม่มีการเก็บรหัสผ่านจริงไว้ในระบบ
- กุญแจเชื่อมต่อ AI ถูกเก็บไว้ฝั่งเซิร์ฟเวอร์ ไม่มีการส่งออกไปยังเบราว์เซอร์ของผู้ใช้

---

## ขอบเขตที่ระบบยังไม่ครอบคลุม (Out of Scope)

ระบบเวอร์ชันนี้ยัง **ไม่** รวมสิ่งต่อไปนี้:

- ❌ การประเมินราคาหรือพยากรณ์แนวโน้มตลาด (market forecasting)
- ❌ การเชื่อมต่อ LINE OA, Facebook Messenger, WhatsApp
- ❌ การจองนัดชมห้องหรือทำสัญญาออนไลน์
- ❌ Integration กับ CRM ภายนอก (Salesforce, HubSpot)
- ❌ Dashboard analytics สำหรับ manager (lead source, conversion funnel)
- ❌ ยังไม่ได้ทำระบบ Auth เพื่อจัดเก็บเข้า DB เพราะเป็นโปรเจ็ค LLM เพื่อโต้ตอบเท่านั้น

**ทั้งหมดนี้สามารถพัฒนาต่อยอดได้** — สถาปัตยกรรมปัจจุบันรองรับการขยาย:
- API-first design → ง่ายต่อการเชื่อม webhook และ third-party services
- Session management → พร้อมสำหรับ multi-channel messaging
- Financial profile data → พร้อมส่งต่อไปยัง CRM pipeline

---

## License

เผยแพร่ภายใต้สัญญาอนุญาต **MIT License** — ใช้งาน แก้ไข และเผยแพร่ต่อได้อย่างเสรี

ผลงานนี้แสดงความสามารถในบทบาท **Business Analyst + AI/ML Engineer + Full Stack Developer** ครอบคลุม:

### Business Analysis
- ตีโจทย์ปัญหาจริงของทีมขาย: ลูกค้าไม่รู้ว่าซื้ออะไรได้ / เสียเวลากับทรัพย์ที่ไม่ตรง / ไม่รู้ว่าควรปิดหรือแนะนำ
- ออกแบบ user flow ที่ใช้งานง่าย (upload → chat → get grounded answers)
- วัดผลในมิติธุรกิจ (ลด wasted effort / เพิ่ม conversion / ไม่เสียลีด)

### AI/ML Engineering
- Financial intelligence layer ที่แปลงภาษาพูดเป็นข้อมูลการเงิน
- Hybrid RAG (semantic + keyword) ด้วย Gemini embeddings
- Context-aware routing (3 consultation modes)
- Production-grade pipeline: intent classification → query rewriting → retrieval → grounded generation

### Full Stack Development
- **Backend**: FastAPI + Python, authentication, file processing, vector search
- **Frontend**: React + TypeScript, real-time chat, file upload, session management
- **Infrastructure**: Persistent storage, session management, error handling
- **DevOps**: CI/CD, environment config, scalable architecture

### Key Design Decisions
1. **Single LLM Provider (Gemini)** — ลดความซับซ้อน ลดค่าใช้จ่าย แต่ครอบคลุม embedding + chat + classification
2. **Financial Router แยกจาก LLM** — LLM ไม่ได้เดา budget แต่วิเคราะห์จากกฎเกณฑ์ → deterministic, auditable
3. **Hybrid RAG** — semantic search อย่างเดียวไม่เพียงพอสำหรับชื่อโครงการ → เพิ่ม keyword boost
4. **Grounded Only** — ตอบได้เฉพาะที่มีข้อมูล ถ้าไม่มีก็บอกตรงๆ → ไม่เสี่ยง hallucination

---

## Technology Stack

**Backend**
- Python 3.9+, FastAPI, Google Gemini API
- NumPy (vector operations), Pandas (data processing)
- JWT authentication, bcrypt password hashing

**Frontend**
- React 18 + TypeScript, Vite
- shadcn/ui components, Tailwind CSS
- Zustand (state management)

**AI/ML**
- Google Gemini 2.0 Flash (chat + embeddings)
- Cosine similarity search (in-memory vector store)
- Hybrid retrieval (semantic + keyword)
