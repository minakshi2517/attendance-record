import face_recognition
import numpy as np
import base64, io, pickle
from PIL import Image
from typing import Optional, Tuple

def decode_base64_image(b64: str) -> np.ndarray:
    if "," in b64:
        b64 = b64.split(",")[1]          # "data:image/jpeg;base64,..." ka prefix hata
    img = Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")
    return np.array(img)

def encode_face(base64_image: str) -> Optional[bytes]:
    """
    Camera se aaye image mein se face ka encoding nikalta hai.
    Returns: numpy bytes ya None agar face nahi mila
    """
    img      = decode_base64_image(base64_image)
    locs     = face_recognition.face_locations(img, model="hog")
    if not locs:
        return None
    encodings = face_recognition.face_encodings(img, locs)
    if not encodings:
        return None
    return pickle.dumps(encodings[0])

def match_face(base64_image: str, stored_encodings: list) -> Tuple[Optional[int], float]:
    """
    Image ko DB ke saare encodings se compare karta hai.
    Returns: (employee_id, confidence%) ya (None, 0.0)
    """
    img      = decode_base64_image(base64_image)
    locs     = face_recognition.face_locations(img, model="hog")
    if not locs:
        return None, 0.0
    unknown  = face_recognition.face_encodings(img, locs)
    if not unknown:
        return None, 0.0

    best_id  = None
    best_dist = 1.0

    for emp_id, enc_bytes in stored_encodings:
        known = pickle.loads(enc_bytes)
        dist  = face_recognition.face_distance([known], unknown[0])[0]
        if dist < best_dist:
            best_dist = dist
            best_id   = emp_id

    if best_dist <= 0.6:              # 0.6 = standard threshold, kam = zyada strict
        confidence = round((1 - best_dist) * 100, 2)
        return best_id, confidence

    return None, 0.0