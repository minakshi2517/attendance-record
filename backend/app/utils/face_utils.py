import numpy as np
import base64
import io
import pickle
import os
import sys
import contextlib
import logging
from PIL import Image
from typing import Optional, Tuple

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")

logger = logging.getLogger(__name__)

# Facenet produces a 128-d embedding. We crop + align the real face first,
# otherwise the whole photo (background, clothes) leaks into the embedding and
# different people start matching each other.
MODEL_NAME = "Facenet"

# Detectors tried in order. opencv ships with opencv-python (no download),
# ssd is a good fallback. We deliberately DO NOT use "skip" here.
DETECTOR_BACKENDS = ["opencv", "ssd"]

# Cosine-distance threshold for a confident match. Lower = stricter.
# DeepFace's default for Facenet is 0.40; we use 0.34 to avoid false matches.
FACE_MATCH_THRESHOLD = 0.34

# The best candidate must beat the runner-up by at least this margin,
# otherwise the result is too ambiguous to trust.
MATCH_MARGIN = 0.06


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
    """Return a face embedding, or None if no real face could be detected.

    When require_face is True we enforce detection so non-face images are
    rejected instead of silently embedding the whole picture.
    """
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

            # If multiple faces are found, keep the largest (closest to camera).
            if len(reps) > 1:
                def area(r):
                    fa = r.get("facial_area", {})
                    return fa.get("w", 0) * fa.get("h", 0)
                reps = sorted(reps, key=area, reverse=True)

            return np.array(reps[0]["embedding"], dtype=np.float64)
        except Exception as e:
            logger.warning("DeepFace detector '%s' failed: %s", backend, e)
            continue

    return None


def encode_face(base64_image: str) -> Tuple[Optional[bytes], Optional[str]]:
    """Used at registration time. Requires a clearly detectable face."""
    try:
        img_array = decode_base64_image(base64_image)
        if img_array.size == 0 or min(img_array.shape[:2]) < 80:
            return None, "The photo is too small. Please capture again."

        enc = _represent(img_array, require_face=True)
        if enc is None:
            return None, ("No face detected. Move closer, face the camera "
                          "directly, and make sure the lighting is good.")
        return pickle.dumps(enc), None
    except Exception as e:
        logger.exception("encode_face error")
        return None, f"Face processing error: {str(e)}"


def match_face(base64_image: str, stored_encodings: list) -> Tuple[Optional[int], float]:
    """Used at check-in/out. Returns (employee_id, confidence%) or (None, 0)."""
    try:
        img_array = decode_base64_image(base64_image)
        probe = _represent(img_array, require_face=True)
        if probe is None:
            return None, 0.0

        scored = []
        for emp_id, enc_bytes in stored_encodings:
            known = pickle.loads(enc_bytes)
            known = np.asarray(known, dtype=np.float64).reshape(-1)
            # Skip encodings whose dimension does not match (old/incompatible).
            if known.shape != probe.shape:
                logger.warning("Skipping employee %s: encoding dim mismatch", emp_id)
                continue
            scored.append((emp_id, _cosine_distance(probe, known)))

        if not scored:
            return None, 0.0

        scored.sort(key=lambda x: x[1])
        best_id, best_dist = scored[0]
        second_dist = scored[1][1] if len(scored) > 1 else float("inf")

        # Reject if not confident enough, or too close to the runner-up.
        if best_dist > FACE_MATCH_THRESHOLD:
            return None, 0.0
        if (second_dist - best_dist) < MATCH_MARGIN and second_dist <= FACE_MATCH_THRESHOLD:
            logger.info("Ambiguous match (best=%.3f, second=%.3f) — rejected",
                        best_dist, second_dist)
            return None, 0.0

        confidence = round(max(0.0, (1.0 - best_dist)) * 100, 2)
        return best_id, confidence
    except Exception:
        logger.exception("match_face error")
        return None, 0.0


def warmup_model():
    """Load the model weights once at startup so the first request is fast."""
    try:
        from deepface import DeepFace
        img = (np.random.rand(160, 160, 3) * 255).astype("uint8")
        with _quiet_deepface():
            DeepFace.represent(
                img_path=img,
                model_name=MODEL_NAME,
                detector_backend="skip",
                enforce_detection=False,
                align=False,
            )
        logger.info("DeepFace model warmed up")
    except Exception as e:
        logger.warning("Model warmup failed: %s", e)
