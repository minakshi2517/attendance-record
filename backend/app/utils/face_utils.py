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

# ArcFace encodes facial geometry (512-d) — stable across lighting, pose, glasses, beard.
MODEL_NAME = "ArcFace"
DETECTOR_BACKENDS = ["retinaface", "opencv", "ssd"]

# Cosine distance: lower = more similar. DeepFace reference for ArcFace is ~0.68.
# We use 0.78 so daily variation (lighting, angle, expression) still matches.
FACE_MATCH_THRESHOLD = 0.78

# Only reject as "ambiguous" when two people score nearly identically.
MATCH_MARGIN = 0.04

MAX_STORED_SAMPLES = 6


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
            if len(reps) > 1:
                reps = sorted(
                    reps,
                    key=lambda r: r.get("facial_area", {}).get("w", 0)
                    * r.get("facial_area", {}).get("h", 0),
                    reverse=True,
                )
            return np.array(reps[0]["embedding"], dtype=np.float64)
        except Exception as e:
            logger.warning("Detector '%s' failed: %s", backend, e)
    return None


def extract_embedding(base64_image: str) -> Tuple[Optional[np.ndarray], Optional[str]]:
    try:
        img_array = decode_base64_image(base64_image)
        if img_array.size == 0 or min(img_array.shape[:2]) < 80:
            return None, "Photo too small. Move closer to the camera."

        emb = _represent(img_array, require_face=True)
        if emb is None:
            return None, "No face detected. Face the camera in good lighting."
        return emb, None
    except Exception as e:
        logger.exception("extract_embedding error")
        return None, f"Face processing error: {str(e)}"


def serialize_embeddings(embeddings: List[np.ndarray]) -> bytes:
    return pickle.dumps([np.asarray(e, dtype=np.float64).reshape(-1) for e in embeddings])


def _load_embeddings(enc_bytes) -> List[np.ndarray]:
    data = pickle.loads(enc_bytes)
    if isinstance(data, list):
        return [np.asarray(d, dtype=np.float64).reshape(-1) for d in data]
    return [np.asarray(data, dtype=np.float64).reshape(-1)]


def encode_face(base64_image: str) -> Tuple[Optional[bytes], Optional[str]]:
    emb, err = extract_embedding(base64_image)
    if emb is None:
        return None, err
    return serialize_embeddings([emb]), None


def _confidence_pct(dist: float) -> float:
    return round(max(0.0, min(100.0, (1.0 - dist / FACE_MATCH_THRESHOLD) * 100)), 2)


def match_face(base64_image: str, stored_encodings: list) -> Tuple[Optional[int], float, Optional[str]]:
    """Returns (employee_id, confidence%, error_reason)."""
    try:
        probe = _represent(decode_base64_image(base64_image), require_face=True)
        if probe is None:
            return None, 0.0, "no_face"

        per_emp = []
        skipped_old = 0
        for emp_id, enc_bytes in stored_encodings:
            try:
                embs = _load_embeddings(enc_bytes)
            except Exception:
                continue
            dists = [_cosine_distance(probe, e) for e in embs if e.shape == probe.shape]
            if not embs:
                skipped_old += 1
            elif not dists and embs:
                skipped_old += 1
            if dists:
                per_emp.append((emp_id, min(dists)))

        if not per_emp:
            if skipped_old:
                return None, 0.0, "outdated_profile"
            return None, 0.0, "no_match"

        per_emp.sort(key=lambda x: x[1])
        best_id, best_dist = per_emp[0]
        second_dist = per_emp[1][1] if len(per_emp) > 1 else float("inf")

        if best_dist > FACE_MATCH_THRESHOLD:
            return None, 0.0, "no_match"

        if len(per_emp) > 1 and second_dist <= FACE_MATCH_THRESHOLD:
            if (second_dist - best_dist) < MATCH_MARGIN:
                return None, 0.0, "ambiguous"

        return best_id, _confidence_pct(best_dist), None
    except Exception:
        logger.exception("match_face error")
        return None, 0.0, "error"


def augment_stored_encoding(enc_bytes: bytes, new_emb: np.ndarray, confidence: float) -> Optional[bytes]:
    """Add a successful check-in sample so the profile adapts over time."""
    if confidence < 70.0:
        return None
    try:
        embs = _load_embeddings(enc_bytes)
        if not embs or embs[0].shape != new_emb.shape:
            return None
        dists = [_cosine_distance(new_emb, e) for e in embs]
        if min(dists) < 0.15:
            return None  # too similar to an existing sample — skip
        embs.append(new_emb.reshape(-1))
        if len(embs) > MAX_STORED_SAMPLES:
            embs = embs[-MAX_STORED_SAMPLES:]
        return serialize_embeddings(embs)
    except Exception:
        return None


def warmup_model():
    try:
        from deepface import DeepFace
        with _quiet_deepface():
            DeepFace.build_model(MODEL_NAME)
        logger.info("Face model (%s) warmed up", MODEL_NAME)
    except Exception as e:
        logger.warning("Model warmup failed: %s", e)
