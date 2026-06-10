import numpy as np
import base64
import io
import pickle
from PIL import Image
from typing import Optional, Tuple


def decode_base64_image(b64: str) -> np.ndarray:
    if "," in b64:
        b64 = b64.split(",")[1]

    img = Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")
    return np.array(img)


def encode_face(base64_image: str) -> Optional[bytes]:
    try:
        from deepface import DeepFace
        import tempfile
        import os

        img_array = decode_base64_image(base64_image)

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            Image.fromarray(img_array).save(f.name)
            temp_path = f.name

        try:
            embedding = DeepFace.represent(
                img_path=temp_path,
                model_name="Facenet",
                enforce_detection=False
            )

            if embedding:
                return pickle.dumps(np.array(embedding[0]["embedding"]))

            return None

        except Exception as e:
            print("encode_face DeepFace error:", e)
            return None

        finally:
            os.unlink(temp_path)

    except Exception as e:
        print("encode_face main error:", e)
        return None


def match_face(base64_image: str, stored_encodings: list) -> Tuple[Optional[int], float]:
    try:
        from deepface import DeepFace
        import tempfile
        import os

        img_array = decode_base64_image(base64_image)

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            Image.fromarray(img_array).save(f.name)
            temp_path = f.name

        try:
            embedding = DeepFace.represent(
                img_path=temp_path,
                model_name="Facenet",
                enforce_detection=False
            )

            if not embedding:
                return None, 0.0

            unknown_enc = np.array(embedding[0]["embedding"])

        except Exception as e:
            print("match_face DeepFace error:", e)
            return None, 0.0

        finally:
            os.unlink(temp_path)

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

    except Exception as e:
        print("match_face main error:", e)
        return None, 0.0
