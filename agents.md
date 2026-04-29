# ASL Bridge — Agent Guide

Read this first. Then load only the skills relevant to what you are working on.

---

## Project Structure

```
signly-conhacks-2026/
├── frontend/          # Expo React Native app
├── backend/           # FastAPI server
├── models/            # ML models and inference scripts
├── docs/              # Architecture and team plans
├── skills/            # Skill repos (load based on your role)
└── agents.md          # This file
```

---

## Load skills based on your role

**Doing frontend work?**
Read `skills/expo-skills/` and `skills/callstack-skills/`

**Doing backend work?**
Read `skills/fastapi/`

**Doing ML / data science work?**
Read `skills/huggingface-skills/` and look at `models/` for existing model files and inference scripts.

**Need full system context?**
Read `docs/PLAN.md`

---

## Commit convention

- No `Co-Authored-By` lines in any commit messages.
- Commit each task separately after user verifies the change.
