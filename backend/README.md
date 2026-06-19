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

## Environment variables (set these in the Space "Settings → Variables and secrets")

- `SECRET_KEY` — a long random string used to sign login tokens.
- `DATABASE_URL` — optional. Defaults to local SQLite. Set a PostgreSQL URL
  (e.g. from Neon/Supabase) if you want data to survive rebuilds.

## First-time admin setup

After the Space is running, create the first admin account by sending a POST
request to `/api/auth/setup` with JSON:

```json
{
  "username": "admin",
  "email": "admin@example.com",
  "password": "your-password",
  "setup_key": "SETUP_ATTENDANCE_2024"
}
```
