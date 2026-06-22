import numpy as np
import base64
import io
import pickle
import os
import sys
import contextlib
import logging
import tempfile
from PIL import Image
from typing import Optional, Tuple, List

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")

logger = logging.getLogger(__name__)

# ArcFace = industry standard. Stores 512 numbers from facial geometry
# (eyes, nose, mouth, jaw). Clothes/lighting/background do NOT matter.
MODEL_NAME = "ArcFace"
EMBEDDING_DIM = 512

DETECTORS = ["retinaface", "opencv", "ssd"]

# STRICT thresholds — prefer "not recognized" over wrong person.
# ArcFace cosine distance: lower = more similar. DeepFace default ~0.68.
FACE_MATCH_THRESHOLD = 0.55
MATCH_MARGIN = 0.10          # 2nd person must be at least this much farther
MIN_MATCH_CONFIDENCE = 55.0  # reject weak matches (%)


@contextlib.contextmanager
def _quiet():
    devnull = open(os.devnull, "w", encoding="utf-8")
    old_out, old_err = sys.stdout, sys.stderr
    try:
        sys.stdout = devnull
        sys.stderr = devnull
        yield
    finally:
        sys.stdout = old_out
        sys.stderr = old_err
        devnull.close()


def decode_base64_image(b64: str) -> np.ndarray:
    if "," in b64:
        b64 = b64.split(",")[1]
    return np.array(Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB"))


def _normalize(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v)
    return v / n if n > 0 else v


def _cosine_dist(a: np.ndarray, b: np.ndarray) -> float:
    return float(1.0 - np.dot(_normalize(a), _normalize(b)))


def _save_temp(img_array: np.ndarray) -> str:
    f = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    Image.fromarray(img_array).save(f.name, quality=92)
    f.close()
    return f.name


def _pick_largest_face(reps: list) -> dict:
    if len(reps) == 1:
        return reps[0]
    return max(reps, key=lambda r: (
        r.get("facial_area", {}).get("w", 0)
        * r.get("facial_area", {}).get("h", 0)
    ))


def _face_big_enough(area: dict, img_shape) -> bool:
    if not area:
        return True
    h, w = img_shape[:2]
    face_area = area.get("w", 0) * area.get("h", 0)
    return face_area >= (w * h * 0.04)  # face >= 4% of frame


def _represent(img_array: np.ndarray, strict_only: bool = False) -> Tuple[Optional[np.ndarray], Optional[dict]]:
    """Detect + align face, return 512-d ArcFace embedding."""
    from deepface import DeepFace

    temp_path = None
    try:
        temp_path = _save_temp(img_array)
        paths = [img_array, temp_path]
    except Exception:
        paths = [img_array]

    strict_modes = [True] if strict_only else [True, False]

    try:
        for backend in DETECTORS:
            for strict in strict_modes:
                for img in paths:
                    try:
                        with _quiet():
                            reps = DeepFace.represent(
                                img_path=img,
                                model_name=MODEL_NAME,
                                detector_backend=backend,
                                enforce_detection=strict,
                                align=True,
                            )
                        if not reps:
                            continue
                        best = _pick_largest_face(reps)
                        area = best.get("facial_area")
                        if strict and not _face_big_enough(area, img_array.shape):
                            continue
                        emb = np.array(best["embedding"], dtype=np.float64)
                        if emb.shape[0] != EMBEDDING_DIM:
                            continue
                        return emb, area
                    except Exception as e:
                        logger.debug("represent %s strict=%s: %s", backend, strict, e)
        return None, None
    finally:
        if temp_path:
            try:
                os.unlink(temp_path)
            except Exception:
                pass


def _pack_embeddings(embs: List[np.ndarray]) -> bytes:
    return pickle.dumps({
        "model": MODEL_NAME,
        "version": 2,
        "embeddings": [e.reshape(-1) for e in embs],
    })


def _unpack(enc_bytes) -> List[np.ndarray]:
    data = pickle.loads(enc_bytes)
    if isinstance(data, dict):
        if data.get("model") and data.get("model") != MODEL_NAME:
            return []
        return [
            np.asarray(e, dtype=np.float64).reshape(-1)
            for e in data.get("embeddings", [])
            if len(np.asarray(e).reshape(-1)) == EMBEDDING_DIM
        ]
    if isinstance(data, list):
        return [np.asarray(e, dtype=np.float64).reshape(-1) for e in data if len(np.asarray(e).reshape(-1)) == EMBEDDING_DIM]
    arr = np.asarray(data, dtype=np.float64).reshape(-1)
    return [arr] if len(arr) == EMBEDDING_DIM else []


def extract_embedding(base64_image: str) -> Tuple[Optional[np.ndarray], Optional[str]]:
    try:
        img = decode_base64_image(base64_image)
        if img.size == 0 or min(img.shape[:2]) < 80:
            return None, "Move closer to the camera."
        emb, _ = _represent(img, strict_only=False)
        if emb is None:
            return None, "No face detected. Look straight at the camera in good light."
        return emb, None
    except Exception as e:
        logger.exception("extract_embedding")
        return None, f"Face scan failed: {e}"


def serialize_embeddings(embeddings: List[np.ndarray]) -> bytes:
    return _pack_embeddings(embeddings)


def encode_face(base64_image: str) -> Tuple[Optional[bytes], Optional[str]]:
    emb, err = extract_embedding(base64_image)
    if emb is None:
        return None, err
    return _pack_embeddings([emb]), None


def _confidence(dist: float) -> float:
    return round(max(0.0, min(100.0, (1.0 - dist / FACE_MATCH_THRESHOLD) * 100)), 2)


def match_face(base64_image: str, stored_encodings: list) -> Tuple[Optional[int], float, Optional[str]]:
    try:
        img = decode_base64_image(base64_image)
        # Attendance: STRICT only — no sloppy fallback that causes wrong matches.
        probe, _ = _represent(img, strict_only=True)
        if probe is None:
            return None, 0.0, "no_face"

        scores, outdated = [], 0
        for emp_id, enc_bytes in stored_encodings:
            try:
                embs = _unpack(enc_bytes)
            except Exception:
                continue
            if not embs:
                outdated += 1
                continue
            dists = [_cosine_dist(probe, e) for e in embs]
            scores.append((emp_id, min(dists)))

        if not scores:
            return None, 0.0, "outdated_profile" if outdated else "no_match"

        scores.sort(key=lambda x: x[1])
        best_id, best_dist = scores[0]
        second_dist = scores[1][1] if len(scores) > 1 else 999.0

        if best_dist > FACE_MATCH_THRESHOLD:
            return None, 0.0, "no_match"

        conf = _confidence(best_dist)
        if conf < MIN_MATCH_CONFIDENCE:
            return None, 0.0, "no_match"

        if len(scores) > 1 and second_dist <= FACE_MATCH_THRESHOLD:
            if (second_dist - best_dist) < MATCH_MARGIN:
                logger.info("Rejected ambiguous: best=%.3f second=%.3f", best_dist, second_dist)
                return None, 0.0, "ambiguous"

        return best_id, conf, None
    except Exception:
        logger.exception("match_face")
        return None, 0.0, "error"


def warmup_model():
    try:
        from deepface import DeepFace
        with _quiet():
            DeepFace.build_model(MODEL_NAME)
        logger.info("ArcFace ready")
    except Exception as e:
        logger.warning("Warmup failed: %s", e)
