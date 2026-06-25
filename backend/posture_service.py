"""
Posture & presence analysis using MediaPipe (Pose + FaceMesh).

Analyses a single webcam JPEG frame for:
  • Sitting posture (slouch / shoulder alignment)
  • Eye contact / facing the camera
  • Whether the candidate is in frame

DeepFace emotion analysis was removed — it depended on a broken
TensorFlow/tf-keras combination, added ~50 s to startup, and contributed
nothing reliable. Posture scoring is now based purely on the MediaPipe
signals, which is honest and actually works on CPU.
"""

import base64
import logging
import threading
from typing import Tuple

logger = logging.getLogger(__name__)

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    np = None
    NUMPY_AVAILABLE = False
    logger.warning("NumPy not available — posture frame decoding disabled")


# MediaPipe pulls in TensorFlow (~15 s to import), so we load it lazily on the
# first frame instead of at startup. warm_up() can preload it in a background
# thread so the first interview frame isn't slow.
mp = None
cv2 = None
_mp_loaded = False
_mp_ok = False
_mp_lock = threading.Lock()


def _ensure_mp() -> bool:
    """Lazily import mediapipe + cv2. Returns True if available."""
    global mp, cv2, _mp_loaded, _mp_ok
    if _mp_loaded:
        return _mp_ok
    with _mp_lock:
        if not _mp_loaded:
            try:
                import mediapipe as _mp
                import cv2 as _cv2
                mp = _mp
                cv2 = _cv2
                _mp_ok = True
                logger.info("MediaPipe + OpenCV loaded ✓")
            except Exception as e:
                _mp_ok = False
                logger.warning(f"MediaPipe / OpenCV unavailable — posture disabled: {e}")
            finally:
                _mp_loaded = True
    return _mp_ok


def is_mediapipe_available() -> bool:
    return _ensure_mp()


def warm_up() -> None:
    """Preload MediaPipe (call in a background thread at startup)."""
    _ensure_mp()


_FEEDBACK = {
    "good":         "Great posture — keep eye contact with the camera.",
    "slouching":    "Sit up straight — keep your shoulders level.",
    "looking_away": "Look at the camera to maintain eye contact.",
    "off_frame":    "Move closer — your face isn't fully in frame.",
    "no_person":    "No person detected — make sure you're visible on camera.",
    "unknown":      "",
}


def _decode_frame(frame_b64: str):
    if not NUMPY_AVAILABLE or not _ensure_mp():
        return None
    try:
        if "," in frame_b64:                # strip data URL prefix if present
            frame_b64 = frame_b64.split(",", 1)[1]
        img_data = base64.b64decode(frame_b64)
        nparr = np.frombuffer(img_data, np.uint8)
        return cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    except Exception as e:
        logger.error(f"Frame decode error: {e}")
        return None


def analyze_frame_base64(frame_b64: str) -> dict:
    """Analyse one frame. Always returns a stable dict."""
    result = {
        "posture_label":    "unknown",
        "eye_contact":      True,
        "confidence_level": 0.7,
        "mediapipe_label":  None,
        "mediapipe_eye":    None,
        "mediapipe_conf":   None,
        "deepface_emotion": None,   # kept for DB column compatibility (always None)
        "deepface_conf":    None,
        "feedback":         "",
        "head_tilt_deg":    0.0,
    }

    if not _ensure_mp():
        result["feedback"] = "Posture analysis unavailable"
        return result

    frame = _decode_frame(frame_b64)
    if frame is None:
        result["feedback"] = "Could not decode frame"
        return result

    try:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        mp_pose = mp.solutions.pose
        with mp_pose.Pose(static_image_mode=True, min_detection_confidence=0.5) as pose:
            pr = pose.process(rgb)

        mp_face = mp.solutions.face_mesh
        with mp_face.FaceMesh(static_image_mode=True, max_num_faces=1) as face_mesh:
            fr = face_mesh.process(rgb)

        posture_label = "good"
        eye_contact = True
        conf = 0.8
        head_tilt = 0.0
        person_seen = False

        if pr.pose_landmarks:
            person_seen = True
            lm = pr.pose_landmarks.landmark
            left_sh  = lm[mp_pose.PoseLandmark.LEFT_SHOULDER]
            right_sh = lm[mp_pose.PoseLandmark.RIGHT_SHOULDER]
            nose     = lm[mp_pose.PoseLandmark.NOSE]

            # Uneven shoulders → slouch / lean
            if abs(left_sh.y - right_sh.y) > 0.06:
                posture_label = "slouching"
                conf = 0.75

            # Nose not confidently visible → out of frame
            if getattr(nose, "visibility", 1.0) < 0.5:
                posture_label = "off_frame"
                eye_contact = False
                conf = 0.6

        if fr.multi_face_landmarks:
            person_seen = True
            face_lm = fr.multi_face_landmarks[0].landmark
            nose_x = face_lm[1].x
            # Head tilt from eye-level difference (landmarks 33 / 263 = outer eyes)
            left_eye_y  = face_lm[33].y
            right_eye_y = face_lm[263].y
            head_tilt = round(abs(left_eye_y - right_eye_y) * 180, 1)

            if nose_x < 0.30 or nose_x > 0.70:
                eye_contact = False
                if posture_label == "good":
                    posture_label = "looking_away"

        if not person_seen:
            posture_label = "no_person"
            eye_contact = False
            conf = 0.5

        result.update({
            "mediapipe_label":  posture_label,
            "mediapipe_eye":    eye_contact,
            "mediapipe_conf":   round(conf, 3),
            "posture_label":    posture_label,
            "eye_contact":      eye_contact,
            "confidence_level": round(conf, 3),
            "head_tilt_deg":    head_tilt,
            "feedback":         _FEEDBACK.get(posture_label, ""),
        })
    except Exception as e:
        logger.error(f"MediaPipe error: {e}")
        result["feedback"] = "Posture analysis error"

    return result


def compute_posture_session_score(logs: list) -> Tuple[float, str]:
    """Overall posture score (0–100) and summary from a session's frame logs."""
    if not logs:
        return 70.0, "No posture data recorded (camera off or no frames captured)."

    total      = len(logs)
    good_count = sum(1 for l in logs if l.get("posture_label") == "good")
    eye_count  = sum(1 for l in logs if l.get("eye_contact"))

    posture_pct = good_count / total * 100
    eye_pct     = eye_count / total * 100
    score       = round(posture_pct * 0.5 + eye_pct * 0.5, 1)

    summary = (
        f"Good posture {posture_pct:.0f}% of the time; "
        f"eye contact maintained {eye_pct:.0f}% of the time "
        f"across {total} samples."
    )
    return score, summary
