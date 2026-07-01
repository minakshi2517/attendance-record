---
title: Attendance API
emoji: 🧑‍💼
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# Face Attendance API

FastAPI backend for the face-recognition attendance system (DeepFace + TensorFlow).

## Local setup (secure)

```powershell
cd backend
python scripts/generate_env.py
python scripts/reset_admin.py
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Credentials are written to `ADMIN_CREDENTIALS.local.txt` (gitignored). **Do not commit `.env`.**

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | Yes | Random string (32+ chars) for JWT signing |
| `SETUP_KEY` | Yes | Secret for one-time `/api/auth/setup` |
| `DEFAULT_ADMIN_USER` | Yes | Bootstrap admin username (not `admin`) |
| `DEFAULT_ADMIN_PASSWORD` | Yes | Strong password (12+ chars, mixed case, digit, symbol) |
| `ALLOWED_ORIGINS` | Yes | Comma-separated frontend URLs for CORS |
| `DATABASE_URL` | No | Defaults to SQLite |

## First-time admin setup (production)

Option A — use `scripts/generate_env.py` + `scripts/reset_admin.py` (recommended).

Option B — POST `/api/auth/setup` only when **no admin exists**:

```json
{
  "username": "your_username",
  "email": "admin@example.com",
  "password": "YourStr0ng!Pass",
  "setup_key": "<SETUP_KEY from .env>"
}
```

## Change password after login

POST `/api/auth/change-credentials` with Bearer token:

```json
{
  "current_password": "old",
  "new_password": "NewStr0ng!Pass",
  "new_username": "optional_new_username"
}
```
