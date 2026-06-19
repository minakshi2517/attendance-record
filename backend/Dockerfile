FROM python:3.10-slim

WORKDIR /app

# System libs required by OpenCV (used by DeepFace)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Pre-download the Facenet model weights into the image so the first
# request is not slow and does not depend on runtime network access.
RUN python -c "from app.utils.face_utils import warmup_model; warmup_model()" || true

# Hugging Face Spaces serves on 7860 by default; other hosts inject $PORT.
ENV PORT=7860
EXPOSE 7860

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-7860}"]
