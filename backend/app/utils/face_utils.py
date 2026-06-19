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

DEEPFACE_OPTS = {
    "model_name": "Facenet",
    "enforce_detection": False,
    "detector_backend": "skip",
    "align": False,
}


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


def _represent(img_array: np.ndarray) -> Optional[np.ndarray]:
    from deepface import DeepFace
    import tempfile

    backends = [
        {"detector_backend": "skip", "align": False},
        {"detector_backend": "opencv", "align": True, "enforce_detection": False},
        {"detector_backend": "ssd", "align": True, "enforce_detection": False},
    ]

    for opts in backends:
        try:
            with _quiet_deepface():
                embedding = DeepFace.represent(
                    img_path=img_array,
                    model_name=DEEPFACE_OPTS["model_name"],
                    enforce_detection=opts.get("enforce_detection", False),
                    detector_backend=opts["detector_backend"],
                    align=opts.get("align", False),
                )
            if embedding:
                return np.array(embedding[0]["embedding"])
        except Exception as e:
            logger.warning("DeepFace %s failed: %s", opts["detector_backend"], e)

    # Windows pe kabhi-kabhi numpy array direct pass fail hota hai — file se try karo
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        Image.fromarray(img_array).save(f.name, quality=95)
        temp_path = f.name

    try:
        with _quiet_deepface():
            embedding = DeepFace.represent(
                img_path=temp_path,
                model_name=DEEPFACE_OPTS["model_name"],
                enforce_detection=False,
                detector_backend="skip",
                align=False,
            )
        if embedding:
            return np.array(embedding[0]["embedding"])
    except Exception as e:
        logger.warning("DeepFace file fallback failed: %s", e)
    finally:
        os.unlink(temp_path)

    return None


def encode_face(base64_image: str) -> Tuple[Optional[bytes], Optional[str]]:
    try:
        img_array = decode_base64_image(base64_image)
        if img_array.size == 0 or min(img_array.shape[:2]) < 80:
            return None, "Photo bahut chhoti hai. Dobara lo."

        enc = _represent(img_array)
        if enc is None:
            return None, "Face process nahi hua. Camera seedha face pe rakho aur achhi light mein photo lo."
        return pickle.dumps(enc), None
    except Exception as e:
        logger.exception("encode_face error")
        return None, f"Face error: {str(e)}"


def match_face(base64_image: str, stored_encodings: list) -> Tuple[Optional[int], float]:
    try:
        img_array = decode_base64_image(base64_image)
        unknown_enc = _represent(img_array)
        if unknown_enc is None:
            return None, 0.0

        best_id = None
        best_dist = float("inf")

        for emp_id, enc_bytes in stored_encodings:
            known_enc = pickle.loads(enc_bytes)
            dist = float(np.linalg.norm(unknown_enc - known_enc))

            if dist < best_dist:
                best_dist = dist
                best_id = emp_id

        if best_dist < 10.0:
            confidence = round(max(0, (10.0 - best_dist) / 10.0 * 100), 2)
            return best_id, confidence

        return None, 0.0
    except Exception:
        logger.exception("match_face error")
        return None, 0.0


def warmup_model():
    try:
        img = Image.new("RGB", (224, 224), color=(200, 180, 160))
        _represent(np.array(img))
        logger.info("DeepFace model warmed up")
    except Exception as e:
        logger.warning("Model warmup failed: %s", e)
