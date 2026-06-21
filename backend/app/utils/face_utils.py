import numpy as np
import base64
import io
import pickle
import os
import sys
import contextlib
import logging
from PIL import Image
from typing import Optional, Tuple, List

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")

logger = logging.getLogger(__name__)

# ArcFace is a state-of-the-art face recognition model. It encodes a person's
# facial geometry into a 512-d vector that stays stable across lighting, pose,
# expression and clothing changes — exactly what an attendance system needs.
MODEL_NAME = "ArcFace"

# Detectors tried in order. RetinaFace is the most accurate (finds + aligns the
# face precisely); opencv is a fast, dependency-free fallback. We never embed
# the whole picture — only the detected, aligned face.
DETECTOR_BACKENDS = ["retinaface", "opencv"]

# Cosine-distance threshold for ArcFace. DeepFace's reference value is 0.68.
FACE_MATCH_THRESHOLD = 0.68

# The best candidate must beat the runner-up by this margin, otherwise the
# result is treated as ambiguous and rejected (prevents wrong person matches).
MATCH_MARGIN = 0.12


@contextlib.contextmanager
def _quiet_deepface():
    devnull = open(os.devnull, "w", encoding="utf-8")
    old_stdout, old_stderr = sys.stdout, sys.stderr
    try:
        sys.stdout = devnull
        sys.stderr = devnull
        yield
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        devnull.close()


def decode_base64_image(b64: str) -> np.ndarray:
    if "," in b64:
        b64 = b64.split(",")[1]
    img = Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")
    return np.array(img)


def _normalize(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v)
    return v / n if n > 0 else v


def _cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
    return float(1.0 - np.dot(_normalize(a), _normalize(b)))


def _represent(img_array: np.ndarray, require_face: bool) -> Optional[np.ndarray]:
    """Return a face embedding, or None if no real face could be detected."""
    from deepface import DeepFace

    for backend in DETECTOR_BACKENDS:
        try:
            with _quiet_deepface():
                reps = DeepFace.represent(
                    img_path=img_array,
                    model_name=MODEL_NAME,
                    detector_backend=backend,
                    enforce_detection=require_face,
                    align=True,
                )
            if not reps:
                continue

            # Keep the largest face if several are present.
            if len(reps) > 1:
                reps = sorted(
                    reps,
                    key=lambda r: r.get("facial_area", {}).get("w", 0)
                    * r.get("facial_area", {}).get("h", 0),
                    reverse=True,
                )
            return np.array(reps[0]["embedding"], dtype=np.float64)
        except Exception as e:
            logger.warning("DeepFace detector '%s' failed: %s", backend, e)
            continue

    return None


def extract_embedding(base64_image: str) -> Tuple[Optional[np.ndarray], Optional[str]]:
    """Detect a face and return its embedding vector (for registration)."""
    try:
        img_array = decode_base64_image(base64_image)
        if img_array.size == 0 or min(img_array.shape[:2]) < 80:
            return None, "The photo is too small. Please capture again."

        emb = _represent(img_array, require_face=True)
        if emb is None:
            return None, ("No face detected. Move closer, face the camera "
                          "directly, and make sure the lighting is good.")
        return emb, None
    except Exception as e:
        logger.exception("extract_embedding error")
        return None, f"Face processing error: {str(e)}"


def serialize_embeddings(embeddings: List[np.ndarray]) -> bytes:
    return pickle.dumps([np.asarray(e, dtype=np.float64).reshape(-1) for e in embeddings])


def _load_embeddings(enc_bytes) -> List[np.ndarray]:
    """Supports both the new list format and the old single-vector format."""
    data = pickle.loads(enc_bytes)
    if isinstance(data, list):
        return [np.asarray(d, dtype=np.float64).reshape(-1) for d in data]
    return [np.asarray(data, dtype=np.float64).reshape(-1)]


# Backwards-compatible single-sample registration helper.
def encode_face(base64_image: str) -> Tuple[Optional[bytes], Optional[str]]:
    emb, err = extract_embedding(base64_image)
    if emb is None:
        return None, err
    return serialize_embeddings([emb]), None


def match_face(base64_image: str, stored_encodings: list) -> Tuple[Optional[int], float]:
    """Identify the person at check-in/out. Returns (employee_id, confidence%)."""
    try:
        img_array = decode_base64_image(base64_image)
        probe = _represent(img_array, require_face=True)
        if probe is None:
            return None, 0.0

        # Best (smallest) cosine distance per employee across all their samples.
        per_emp = []
        for emp_id, enc_bytes in stored_encodings:
            try:
                embs = _load_embeddings(enc_bytes)
            except Exception:
                continue
            dists = [
                _cosine_distance(probe, e)
                for e in embs
                if e.shape == probe.shape
            ]
            if dists:
                per_emp.append((emp_id, min(dists)))

        if not per_emp:
            return None, 0.0

        per_emp.sort(key=lambda x: x[1])
        best_id, best_dist = per_emp[0]
        second_dist = per_emp[1][1] if len(per_emp) > 1 else float("inf")

        if best_dist > FACE_MATCH_THRESHOLD:
            return None, 0.0
        if (second_dist - best_dist) < MATCH_MARGIN and second_dist <= FACE_MATCH_THRESHOLD:
            logger.info("Ambiguous match (best=%.3f second=%.3f) — rejected",
                        best_dist, second_dist)
            return None, 0.0

        confidence = round(max(0.0, (FACE_MATCH_THRESHOLD - best_dist) / FACE_MATCH_THRESHOLD) * 100, 2)
        return best_id, confidence
    except Exception:
        logger.exception("match_face error")
        return None, 0.0


def warmup_model():
    """Preload the recognition model + detector weights at startup."""
    try:
        from deepface import DeepFace
        with _quiet_deepface():
            DeepFace.build_model(MODEL_NAME)
            # Trigger RetinaFace weight download/caching.
            dummy = (np.random.rand(160, 160, 3) * 255).astype("uint8")
            try:
                DeepFace.extract_faces(dummy, detector_backend="retinaface",
                                       enforce_detection=False, align=True)
            except Exception:
                pass
        logger.info("Face model (%s) warmed up", MODEL_NAME)
    except Exception as e:
        logger.warning("Model warmup failed: %s", e)
