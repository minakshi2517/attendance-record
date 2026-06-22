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

# ArcFace stores 512-d vectors from facial geometry (eyes, nose, jaw).
# Like phone face unlock — clothes, background, and lighting should not matter.
MODEL_NAME = "ArcFace"
EMBEDDING_DIM = 512
PACK_VERSION = 3

DETECTORS = ["retinaface", "opencv", "ssd"]

# DeepFace ArcFace default verify threshold is ~0.68 (cosine distance).
FACE_MATCH_THRESHOLD = 0.65
DUPLICATE_THRESHOLD = 0.52
MATCH_MARGIN = 0.05
MIN_FACE_FRAME_RATIO = 0.03
MIN_BLUR_VARIANCE = 15.0
MIN_BLUR_VARIANCE_ATTENDANCE = 10.0


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


def image_bytes_to_base64(raw: bytes, content_type: str = "image/jpeg") -> str:
    return f"data:{content_type};base64,{base64.b64encode(raw).decode('ascii')}"


def extract_embedding_from_bytes(raw: bytes) -> Tuple[Optional[np.ndarray], Optional[str]]:
    return _probe_from_bytes(raw)


def build_profile_from_bytes(raw_images: List[bytes]) -> Tuple[Optional[bytes], Optional[str]]:
    """Same face pipeline as check-in — register and match stay consistent."""
    embeddings = []
    last_err = None
    for raw in raw_images:
        emb, reason = _probe_from_bytes(raw)
        if emb is not None:
            embeddings.append(emb)
        else:
            last_err = _reason_message(reason)
    if not embeddings:
        return None, last_err or "No valid face found. Please try again."
    return _pack_embeddings(embeddings), None


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


def _normalize_lighting(img_array: np.ndarray) -> np.ndarray:
    """Reduce lighting/shadow impact before embedding (phone-lock style)."""
    try:
        import cv2
        lab = cv2.cvtColor(img_array, cv2.COLOR_RGB2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        merged = cv2.merge((l, a, b))
        return cv2.cvtColor(merged, cv2.COLOR_LAB2RGB)
    except Exception:
        return img_array


def _face_crop(img_array: np.ndarray, area: dict, pad: float = 0.30) -> np.ndarray:
    if not area:
        return img_array
    h, w = img_array.shape[:2]
    x = int(area.get("x", 0))
    y = int(area.get("y", 0))
    fw = int(area.get("w", 0))
    fh = int(area.get("h", 0))
    if fw <= 0 or fh <= 0:
        return img_array
    px, py = int(fw * pad), int(fh * pad)
    x1, y1 = max(0, x - px), max(0, y - py)
    x2, y2 = min(w, x + fw + px), min(h, y + fh + py)
    if x2 <= x1 or y2 <= y1:
        return img_array
    return img_array[y1:y2, x1:x2].copy()


def _blend_embeddings(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return _normalize((_normalize(a) + _normalize(b)) * 0.5)


def _represent_crop_only(crop: np.ndarray) -> Optional[np.ndarray]:
    """Second pass on face crop only — ignores background, clothes, hair outside crop."""
    from deepface import DeepFace

    crop = _normalize_lighting(crop)
    if crop.size == 0 or min(crop.shape[:2]) < 48:
        return None
    for backend in ["opencv", "ssd", "retinaface"]:
        try:
            with _quiet():
                reps = DeepFace.represent(
                    img_path=crop,
                    model_name=MODEL_NAME,
                    detector_backend=backend,
                    enforce_detection=False,
                    align=True,
                )
            if not reps:
                continue
            emb = np.array(reps[0]["embedding"], dtype=np.float64)
            if emb.shape[0] == EMBEDDING_DIM:
                return emb
        except Exception:
            continue
    return None


def _is_sharp_enough(img_array: np.ndarray, area: dict, min_variance: float = MIN_BLUR_VARIANCE) -> bool:
    try:
        import cv2
        crop = _face_crop(img_array, area)
        gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
        return float(cv2.Laplacian(gray, cv2.CV_64F).var()) >= min_variance
    except Exception:
        return True


def _pick_largest_face(reps: list) -> dict:
    if len(reps) == 1:
        return reps[0]
    return max(reps, key=lambda r: (
        r.get("facial_area", {}).get("w", 0)
        * r.get("facial_area", {}).get("h", 0)
    ))


def _face_big_enough(area: dict, img_shape, min_ratio: float = MIN_FACE_FRAME_RATIO) -> bool:
    if not area:
        return False
    h, w = img_shape[:2]
    face_area = area.get("w", 0) * area.get("h", 0)
    return face_area >= (w * h * min_ratio)


def _represent(
    img_array: np.ndarray,
    strict_only: bool = True,
    min_face_ratio: float = MIN_FACE_FRAME_RATIO,
    min_blur: float = MIN_BLUR_VARIANCE,
) -> Tuple[Optional[np.ndarray], Optional[dict], Optional[str]]:
    """Detect, align face, return 512-d ArcFace embedding + facial area."""
    from deepface import DeepFace

    img_array = _normalize_lighting(img_array)
    temp_path = None
    try:
        temp_path = _save_temp(img_array)
        paths = [img_array, temp_path]
    except Exception:
        paths = [img_array]

    strict_modes = [True] if strict_only else [True, False]
    last_reason = "no_face"

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
                        if strict and len(reps) > 1:
                            last_reason = "multiple_faces"
                            continue
                        best = _pick_largest_face(reps)
                        area = best.get("facial_area")
                        if strict and not _face_big_enough(area, img_array.shape, min_face_ratio):
                            last_reason = "face_too_small"
                            continue
                        if strict and not _is_sharp_enough(img_array, area, min_blur):
                            last_reason = "too_blurry"
                            continue
                        emb = np.array(best["embedding"], dtype=np.float64)
                        if emb.shape[0] != EMBEDDING_DIM:
                            continue
                        if area:
                            crop = _face_crop(img_array, area)
                            crop_emb = _represent_crop_only(crop)
                            if crop_emb is not None:
                                emb = _blend_embeddings(emb, crop_emb)
                        return emb, area, None
                    except Exception as e:
                        logger.debug("represent %s strict=%s: %s", backend, strict, e)
        return None, None, last_reason
    finally:
        if temp_path:
            try:
                os.unlink(temp_path)
            except Exception:
                pass


def _centroid(embs: List[np.ndarray]) -> np.ndarray:
    if len(embs) == 1:
        return _normalize(embs[0])
    stacked = np.stack([_normalize(e) for e in embs], axis=0)
    return _normalize(np.mean(stacked, axis=0))


def _pack_embeddings(embs: List[np.ndarray]) -> bytes:
    centroid = _centroid(embs)
    return pickle.dumps({
        "model": MODEL_NAME,
        "version": PACK_VERSION,
        "centroid": centroid.reshape(-1),
        "embeddings": [e.reshape(-1) for e in embs],
    })


def _unpack(enc_bytes) -> List[np.ndarray]:
    data = pickle.loads(enc_bytes)
    if isinstance(data, dict):
        if data.get("model") and data.get("model") != MODEL_NAME:
            return []
        vectors = []
        centroid = data.get("centroid")
        if centroid is not None:
            arr = np.asarray(centroid, dtype=np.float64).reshape(-1)
            if len(arr) == EMBEDDING_DIM:
                vectors.append(arr)
        for e in data.get("embeddings", []):
            arr = np.asarray(e, dtype=np.float64).reshape(-1)
            if len(arr) == EMBEDDING_DIM:
                vectors.append(arr)
        return vectors
    if isinstance(data, list):
        return [
            np.asarray(e, dtype=np.float64).reshape(-1)
            for e in data
            if len(np.asarray(e).reshape(-1)) == EMBEDDING_DIM
        ]
    arr = np.asarray(data, dtype=np.float64).reshape(-1)
    return [arr] if len(arr) == EMBEDDING_DIM else []


REASON_MESSAGES = {
    "no_face": "No face detected. Look straight at the camera.",
    "multiple_faces": "Only one person should be in the frame.",
    "face_too_small": "Move closer to the camera so your face fills the frame.",
    "too_blurry": "Image is blurry. Hold still and ensure good light.",
}


def _reason_message(reason: Optional[str]) -> str:
    return REASON_MESSAGES.get(reason or "no_face", REASON_MESSAGES["no_face"])


def extract_embedding(base64_image: str) -> Tuple[Optional[np.ndarray], Optional[str]]:
    try:
        img = decode_base64_image(base64_image)
        return _probe_from_image(img)
    except Exception as e:
        logger.exception("extract_embedding")
        return None, f"Face scan failed: {e}"


def build_profile(images: List[str]) -> Tuple[Optional[bytes], Optional[str]]:
    """Build stored face profile from enrollment photos (same pipeline as check-in)."""
    embeddings = []
    last_err = None
    for img in images:
        emb, err = extract_embedding(img)
        if emb is not None:
            embeddings.append(emb)
        else:
            last_err = err
    if not embeddings:
        return None, last_err or "No valid face found. Please try again."
    return _pack_embeddings(embeddings), None


def serialize_embeddings(embeddings: List[np.ndarray]) -> bytes:
    return _pack_embeddings(embeddings)


def encode_face(base64_image: str) -> Tuple[Optional[bytes], Optional[str]]:
    emb, err = extract_embedding(base64_image)
    if emb is None:
        return None, err
    return _pack_embeddings([emb]), None


def _confidence(dist: float) -> float:
    return round(max(0.0, min(100.0, (1.0 - dist / FACE_MATCH_THRESHOLD) * 100)), 2)


def _best_distance(probe: np.ndarray, stored: List[np.ndarray]) -> float:
    return min(_cosine_dist(probe, e) for e in stored)


def find_duplicate(probe: np.ndarray, stored_encodings: list, exclude_emp_id: Optional[int] = None) -> Optional[int]:
    """Return employee id if this face already belongs to someone else."""
    for emp_id, enc_bytes in stored_encodings:
        if exclude_emp_id is not None and emp_id == exclude_emp_id:
            continue
        try:
            embs = _unpack(enc_bytes)
        except Exception:
            continue
        if not embs:
            continue
        if _best_distance(probe, embs) <= DUPLICATE_THRESHOLD:
            return emp_id
    return None


def _probe_from_image(img_array: np.ndarray) -> Tuple[Optional[np.ndarray], Optional[str]]:
    """Extract face embedding for attendance — strict first, then slightly relaxed."""
    emb, _, reason = _represent(img_array, strict_only=True)
    if emb is not None:
        return emb, None
    emb, _, reason2 = _represent(
        img_array,
        strict_only=True,
        min_face_ratio=0.03,
        min_blur=MIN_BLUR_VARIANCE_ATTENDANCE,
    )
    if emb is not None:
        return emb, None
    emb, _, _ = _represent(img_array, strict_only=False, min_face_ratio=0.03, min_blur=MIN_BLUR_VARIANCE_ATTENDANCE)
    if emb is not None:
        return emb, None
    return None, reason or reason2 or "no_face"


def _probe_from_bytes(raw: bytes) -> Tuple[Optional[np.ndarray], Optional[str]]:
    try:
        img = np.array(Image.open(io.BytesIO(raw)).convert("RGB"))
        if img.size == 0 or min(img.shape[:2]) < 60:
            return None, "face_too_small"
        return _probe_from_image(img)
    except Exception:
        logger.exception("_probe_from_bytes")
        return None, "error"


def _score_match(probes: List[np.ndarray], stored_encodings: list) -> Tuple[Optional[int], float, Optional[str]]:
    scores, outdated = [], 0
    for emp_id, enc_bytes in stored_encodings:
        try:
            embs = _unpack(enc_bytes)
        except Exception:
            continue
        if not embs:
            outdated += 1
            continue
        dist = min(_best_distance(p, embs) for p in probes)
        scores.append((emp_id, dist))

    if not scores:
        return None, 0.0, "outdated_profile" if outdated else "no_match"

    scores.sort(key=lambda x: x[1])
    best_id, best_dist = scores[0]
    second_dist = scores[1][1] if len(scores) > 1 else 999.0

    if best_dist > FACE_MATCH_THRESHOLD:
        logger.info("No match: best_dist=%.3f threshold=%.3f employees=%d", best_dist, FACE_MATCH_THRESHOLD, len(scores))
        return None, 0.0, "no_match"

    conf = _confidence(best_dist)

    # Only block ambiguous matches when 2+ people are close — skip for single employee teams.
    if len(scores) > 1 and second_dist <= FACE_MATCH_THRESHOLD:
        if (second_dist - best_dist) < MATCH_MARGIN:
            logger.info("Rejected ambiguous match: best=%.3f second=%.3f", best_dist, second_dist)
            return None, 0.0, "ambiguous"

    return best_id, conf, None


def match_face(base64_image: str, stored_encodings: list) -> Tuple[Optional[int], float, Optional[str]]:
    try:
        img = decode_base64_image(base64_image)
        probe, reason = _probe_from_image(img)
        if probe is None:
            return None, 0.0, reason or "no_face"
        return _score_match([probe], stored_encodings)
    except Exception:
        logger.exception("match_face")
        return None, 0.0, "error"


def match_face_bytes(raw_images: List[bytes], stored_encodings: list) -> Tuple[Optional[int], float, Optional[str]]:
    try:
        probes = []
        last_reason = "no_face"
        for raw in raw_images:
            probe, reason = _probe_from_bytes(raw)
            if probe is not None:
                probes.append(probe)
            elif reason:
                last_reason = reason
        if not probes:
            return None, 0.0, last_reason
        return _score_match(probes, stored_encodings)
    except Exception:
        logger.exception("match_face_bytes")
        return None, 0.0, "error"


def warmup_model():
    try:
        from deepface import DeepFace
        with _quiet():
            DeepFace.build_model(MODEL_NAME)
        logger.info("ArcFace ready")
    except Exception as e:
        logger.warning("Warmup failed: %s", e)
