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

MODEL_NAME = "ArcFace"
DETECTORS = ["opencv", "ssd", "retinaface"]
FACE_MATCH_THRESHOLD = 0.72
MATCH_MARGIN = 0.05
MAX_SAMPLES = 5


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


def _represent(img_array: np.ndarray) -> Tuple[Optional[np.ndarray], Optional[dict]]:
    from deepface import DeepFace

    temp_path = None
    try:
        temp_path = _save_temp(img_array)
        paths = [img_array, temp_path]
    except Exception:
        paths = [img_array]

    try:
        for backend in DETECTORS:
            for strict in (True, False):
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
                        best = reps[0]
                        if len(reps) > 1:
                            best = max(reps, key=lambda r: (
                                r.get("facial_area", {}).get("w", 0)
                                * r.get("facial_area", {}).get("h", 0)
                            ))
                        return (
                            np.array(best["embedding"], dtype=np.float64),
                            best.get("facial_area"),
                        )
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
        "embeddings": [e.reshape(-1) for e in embs],
    })


def _unpack(enc_bytes) -> List[np.ndarray]:
    data = pickle.loads(enc_bytes)
    if isinstance(data, dict):
        return [np.asarray(e, dtype=np.float64).reshape(-1) for e in data.get("embeddings", [])]
    if isinstance(data, list):
        return [np.asarray(e, dtype=np.float64).reshape(-1) for e in data]
    return [np.asarray(data, dtype=np.float64).reshape(-1)]


def extract_embedding(base64_image: str) -> Tuple[Optional[np.ndarray], Optional[str]]:
    try:
        img = decode_base64_image(base64_image)
        if img.size == 0 or min(img.shape[:2]) < 60:
            return None, "Photo too small. Move closer to the camera."
        emb, _ = _represent(img)
        if emb is None:
            return None, "Could not detect a face. Look straight at the camera in good light."
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
        probe, _ = _represent(decode_base64_image(base64_image))
        if probe is None:
            return None, 0.0, "no_face"

        scores, outdated = [], 0
        for emp_id, enc_bytes in stored_encodings:
            try:
                embs = _unpack(enc_bytes)
            except Exception:
                continue
            dists = [_cosine_dist(probe, e) for e in embs if e.shape == probe.shape]
            if embs and not dists:
                outdated += 1
            if dists:
                scores.append((emp_id, min(dists)))

        if not scores:
            return None, 0.0, "outdated_profile" if outdated else "no_match"

        scores.sort(key=lambda x: x[1])
        best_id, best = scores[0]
        second = scores[1][1] if len(scores) > 1 else 999.0

        if best > FACE_MATCH_THRESHOLD:
            return None, 0.0, "no_match"
        if len(scores) > 1 and second <= FACE_MATCH_THRESHOLD and (second - best) < MATCH_MARGIN:
            return None, 0.0, "ambiguous"

        return best_id, _confidence(best), None
    except Exception:
        logger.exception("match_face")
        return None, 0.0, "error"


def augment_stored_encoding(enc_bytes: bytes, new_emb: np.ndarray, confidence: float) -> Optional[bytes]:
    if confidence < 65.0:
        return None
    try:
        embs = _unpack(enc_bytes)
        if not embs or embs[0].shape != new_emb.shape:
            return None
        if min(_cosine_dist(new_emb, e) for e in embs) < 0.12:
            return None
        embs.append(new_emb.reshape(-1))
        if len(embs) > MAX_SAMPLES:
            embs = embs[-MAX_SAMPLES:]
        return _pack_embeddings(embs)
    except Exception:
        return None


def warmup_model():
    try:
        from deepface import DeepFace
        with _quiet():
            DeepFace.build_model(MODEL_NAME)
        logger.info("ArcFace model ready")
    except Exception as e:
        logger.warning("Warmup failed: %s", e)
