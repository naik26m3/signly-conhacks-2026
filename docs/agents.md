# ASL Bridge — Agents & AI Models

This file documents the AI agents and models used in the ASL Bridge pipeline.

---

## Vision Agent — ASL Recognition

**Primary:** Gemini 2.0 Flash  
**Fallback:** GPT-4o mini  
**Task:** Receive a preprocessed base64 frame → return ASL gloss label  
**Approach:** Zero-shot with few-shot reference images in prompt  
**Owner:** Dave

---

## Translation Agent — Gloss ↔ English

**Model:** Llama 3.1 8B via Groq  
**Tasks:**
- Deaf → Hearing: ASL gloss → natural English sentence
- Hearing → Deaf: English sentence → ASL gloss

**Owner:** Dave

---

## Speech-to-Text Agent — STT

**Model:** Whisper large-v3 via Groq  
**Task:** Audio file → English transcript  
**Owner:** Dave

---

## Data Collection Agent (passive)

**File:** `services/collector.py`  
**Task:** Auto-log every inference (frame + label + timestamp) as JSONL to `data/raw/`  
**Purpose:** Build labeled dataset for post-hackathon Qwen3-VL fine-tune  
**Owner:** Dave

---

## Post-Hackathon — Fine-tuned Vision Agent

**Model:** Qwen3-VL 7B (LoRA fine-tune)  
**Training data:** Hackathon JSONL + How2Sign dataset (~80h video)  
**Infra:** Colab Pro or RunPod A100  
**Replaces:** Gemini zero-shot  
**Timeline:** Week 1-2 post-hackathon

---

## Notes

- All agents read `docs/PLAN.md` for full context on the system architecture, team ownership, and API endpoints.
- Vision agent prompt is engineered by Dave — see `services/inference.py` for few-shot reference image logic.
- Confidence threshold is applied after vision agent response: if confidence < threshold, display "signing..." instead of a label.
