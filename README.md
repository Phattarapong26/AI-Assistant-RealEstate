## AI Property Consultant — LLM-powered Real Estate Assistant

โครงการระหว่างเทอม (Course Project) ในหัวข้อ LLM ที่ออกแบบให้ทุกคนเข้าถึงได้ง่าย โดยใช้กรณีใช้งานด้านอสังหาริมทรัพย์ เพื่อสาธิตการประยุกต์ใช้ LLM กับข้อมูลจริง และวางรากฐานต่อยอดสู่การทำ Machine Learning เพื่อคาดการณ์แนวโน้มราคาเพื่อการลงทุนแบบไม่ดอย

### Highlights
- **Conversational AI (TH)**: สนทนาภาษาไทยได้ลื่นไหล ปรับโทนการให้คำปรึกษาได้หลายแบบ (formal/casual/friendly/professional)
- **Context-aware**: อัปโหลดไฟล์ทรัพย์สิน (CSV/Excel) แล้วค้นหา/สรุปตัวเลือกที่เกี่ยวข้องจากคำถามผู้ใช้
- **Pluggable LLM Providers**: รองรับ OpenAI เป็นค่าเริ่มต้น และเตรียมจุดต่อขยายสำหรับ Google Gemini
- **Practical UX**: อินเทอร์เฟซแชทเรียบง่าย ใช้งานจริงได้ทันที เหมาะโชว์ผลงานในพอร์ต
- **Future-ready**: วางแผนต่อยอดด้วยโมเดล ML คาดการณ์ราคา และระบบจัดเก็บเวกเตอร์สำหรับการค้นหาที่แม่นยำขึ้น

---

### Screenshots

หน้าหลักและตัวอย่างแชท (ดูโฟลเดอร์ `src/image/` สำหรับไฟล์เต็ม):

![Homepage](src/image/homepage.png)

![Chat 1](src/image/chat1.png)

![Chat 2](src/image/chat2.png)

---

### Project Structure (สำคัญสำหรับ Reviewer)

```
src/
  backend/           # FastAPI + LLM integrations (demo-focused)
  components/        # UI components (shadcn/ui)
  context/           # React contexts (Auth, App settings)
  hooks/             # Custom hooks (chat/session management)
  pages/             # App pages (Index, Chat, Upload, Settings)
  frontend/api.ts    # Frontend API client
  image/             # Screenshots used in README/portfolio
```

---

### Tech Stack
- **Frontend**: React (Vite, TypeScript), TailwindCSS, shadcn/ui
- **Backend**: FastAPI (Python), Pydantic, OpenAI SDK (พร้อม hook สำหรับ Gemini)
- **Others**: dotenv, pandas (รองรับ CSV/XLSX อัปโหลดข้อมูลทรัพย์สิน)

---

### Getting Started (Dev)

Prerequisites
- Node.js 18+
- Python 3.10+

1) Install Frontend
```bash
npm install
npm run dev
```

2) Setup Backend
```bash
cd src/backend
python -m venv venv
source venv/bin/activate  # Windows ใช้ venv\\Scripts\\activate
pip install -r requirements.txt
cp .env.example .env  # ถ้ามี; กรณีนี้ตั้งค่าเองตามด้านล่าง
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Environment Variables (ไฟล์ `src/backend/.env`)
```
PROVIDER=openai            # หรือ google
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4o-mini   # ค่าเริ่มต้นในโปรเจกต์นี้
# GOOGLE_API_KEY=...
# GOOGLE_MODEL=gemini-1.5-flash
```

---

### Data Upload Format (สำคัญ)
รองรับไฟล์ `CSV` หรือ `Excel` โดยคอลัมน์ที่คาดหวัง (ต้องมี) ได้แก่:

```
ประเภท, โครงการ, ราคา, รูปแบบ, รูป, ตำแหน่ง,
สถานศึกษา, สถานีรถไฟฟ้า, ห้างสรรพสินค้า, โรงพยาบาล, สนามบิน
```

ระบบจะเติมค่า "ไม่มี" ให้ฟิลด์ว่างโดยอัตโนมัติและใช้เพื่อกรอง/จัดรูปแบบคำตอบ

---

### API (สำหรับทดสอบ/รีวิว)

Base URL: `http://localhost:8000/api`

- POST `/chat`
  - Body (ตัวอย่าง)
  ```json
  {
    "query": "คอนโดใกล้ BTS ราคาไม่เกิน 3 ล้าน",
    "consultation_style": "formal",
    "session_id": "optional"
  }
  ```
  - Response (ย่อ)
  ```json
  {
    "response": "...ข้อความตอบกลับ...",
    "session_id": "session_...",
    "properties": [{"โครงการ": "...", "ราคา": "..."}]
  }
  ```

- POST `/upload`
  - Form-Data: `file` (csv/xlsx/xls), `consultation_style`
  - Response: `{ message, file_id, num_records }`

- GET `/styles`
  - Response: mapping ของ style ที่รองรับ (TH)

หมายเหตุ: เวอร์ชันนี้เป็นเดโมสำหรับงานเรียน จึงยังเก็บข้อมูลและ session ในหน่วยความจำเพื่อความง่ายในการรัน

---

### How It Works (สรุปสถาปัตยกรรมเดโม)
1. ผู้ใช้พิมพ์คำถาม → Frontend ส่งคำถามไปยัง `/api/chat`
2. Backend ตรวจจับ intent ทักทาย/ทั่วไป, ทำ vector search แบบง่าย (keyword-based ในเดโมนี้)
3. สร้าง prompt และเรียก LLM ตามผู้ให้บริการที่ตั้งค่าไว้ → ส่งคำตอบกลับพร้อมรายการทรัพย์สินที่เกี่ยวข้อง
4. UI แสดงผลลัพธ์ พร้อมแสดงรายการที่พบและคอนเท็กซ์ภาษาไทย

---

### Roadmap (ต่อยอดที่วางไว้)
- เปลี่ยน vector search เป็น Embedding จริง + Vector DB (เช่น FAISS/pgvector)
- เพิ่ม persistence สำหรับ chat history และข้อมูลไฟล์ (MongoDB/Postgres)
- เพิ่มชุดทดสอบ (unit/integration/e2e) และ API contract (OpenAPI/TS SDK)
- สร้างโมเดล ML ทำนายแนวโน้มราคา (feature engineering + time-series + evaluation)
- ปรับปรุง Observability (structured logging, tracing, error reporting)

---

### Limitations (ตามจริงแบบมืออาชีพ)
- เก็บข้อมูลในหน่วยความจำ (เดโม) — รีสตาร์ตแล้วข้อมูลหาย ไม่เหมาะโปรดักชัน
- API contract ฝั่งเดโมยังเรียบง่าย ควรกำหนดสคีมาร่วมและเพิ่ม validation
- ไม่มีระบบ Auth/Rate Limit ในเวอร์ชันเพื่อการสาธิต

---

### Why This Project Matters (สำหรับ CTO/HR)
- แสดงศักยภาพการเชื่อม LLM กับกรณีใช้งานที่ชัดเจน มี UX ใช้งานได้จริง
- โครงสร้างแยกหน้า/หลังบ้านชัดเจน พร้อมจุดต่อยอดไปโปรดักชัน
- สื่อสารข้อจำกัดและ Roadmap ตรงไปตรงมา เหมาะเป็นฐานต่อยอดงานจริง

---

### Author
Student Project — LLM for Real Estate. เปิดรับคำแนะนำ/รีวิวโค้ดเพื่อพัฒนาต่อ หากต้องการทดลอง/รีวิวร่วม โปรดเปิด Issue หรือ PR.

