import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.models import PostureLog
from models.schemas import PostureFrameRequest, PostureResult
from utils.auth import get_current_user
from posture_service import analyze_frame_base64, is_mediapipe_available

router = APIRouter()


@router.get("/status")
async def posture_status():
    available = is_mediapipe_available()
    return {
        "mediapipe_available": available,
        "message": (
            "Posture analysis active (MediaPipe pose + face mesh)"
            if available
            else "Posture analysis unavailable — install mediapipe and opencv-python"
        ),
    }


@router.post("/analyze-frame", response_model=PostureResult)
async def analyze_frame(
    payload: PostureFrameRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not payload.frame_base64:
        raise HTTPException(status_code=400, detail="No frame data provided")

    # MediaPipe is CPU-bound — run off the event loop so it never blocks other requests.
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, analyze_frame_base64, payload.frame_base64)

    log = PostureLog(
        session_id=payload.session_id,
        timestamp_sec=payload.timestamp_sec,
        mediapipe_label=result.get("mediapipe_label"),
        mediapipe_eye=result.get("mediapipe_eye"),
        mediapipe_conf=result.get("mediapipe_conf"),
        deepface_emotion=result.get("deepface_emotion"),
        deepface_conf=result.get("deepface_conf"),
        posture_label=result.get("posture_label"),
        eye_contact=result.get("eye_contact"),
        confidence_level=result.get("confidence_level"),
        raw_landmarks=payload.landmarks or {},
    )
    db.add(log)
    db.commit()

    return PostureResult(
        posture_label=result.get("posture_label", "unknown"),
        eye_contact=result.get("eye_contact", True),
        confidence_level=result.get("confidence_level", 0.7),
        emotion=result.get("deepface_emotion"),
        feedback=result.get("feedback", ""),
    )


@router.websocket("/ws/{session_id}")
async def posture_websocket(
    websocket: WebSocket,
    session_id: int,
    db: Session = Depends(get_db),
):
    await websocket.accept()
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"error": "Invalid JSON"})
                continue

            frame_b64 = msg.get("frame")
            timestamp = float(msg.get("timestamp", 0.0))

            if not frame_b64:
                await websocket.send_json({"error": "No frame provided"})
                continue

            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, analyze_frame_base64, frame_b64)

            log = PostureLog(
                session_id=session_id,
                timestamp_sec=timestamp,
                mediapipe_label=result.get("mediapipe_label"),
                mediapipe_eye=result.get("mediapipe_eye"),
                mediapipe_conf=result.get("mediapipe_conf"),
                deepface_emotion=result.get("deepface_emotion"),
                deepface_conf=result.get("deepface_conf"),
                posture_label=result.get("posture_label"),
                eye_contact=result.get("eye_contact"),
                confidence_level=result.get("confidence_level"),
                raw_landmarks={},
            )
            db.add(log)
            db.commit()

            await websocket.send_json({
                "posture":     result.get("posture_label"),
                "eye_contact": result.get("eye_contact"),
                "confidence":  result.get("confidence_level"),
                "head_tilt":   result.get("head_tilt_deg"),
                "feedback":    result.get("feedback"),
                "mp_available": result.get("mediapipe_label") not in (None, "unknown"),
            })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"error": str(e)})
        except Exception:
            pass
