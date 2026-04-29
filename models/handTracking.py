import base64
import logging
from pathlib import Path

import cv2
import mediapipe as mp
from mediapipe.tasks.python import vision

logger = logging.getLogger(__name__)

_MODEL_PATH = Path(__file__).parent / "hand_landmarker.task"
_DEBUG_DIR = Path(__file__).parent.parent / "debug" / "frames"


def _draw_landmarks(frame, result):
    annotated = frame.copy()
    h, w = annotated.shape[:2]
    for hand_landmarks in result.hand_landmarks:
        for lm in hand_landmarks:
            cx, cy = int(lm.x * w), int(lm.y * h)
            cv2.circle(annotated, (cx, cy), 5, (0, 255, 0), -1)
    return annotated


class HandTracker:
    _landmarker: "vision.HandLandmarker | None" = None

    @classmethod
    def load(cls) -> None:
        if cls._landmarker is not None:
            return
        logger.info("Loading MediaPipe HandLandmarker from %s", _MODEL_PATH)
        options = vision.HandLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(_MODEL_PATH)),
            running_mode=vision.RunningMode.IMAGE,
            num_hands=2,
        )
        cls._landmarker = vision.HandLandmarker.create_from_options(options)
        logger.info("HandLandmarker ready")

    @classmethod
    def unload(cls) -> None:
        if cls._landmarker is not None:
            cls._landmarker.close()
            cls._landmarker = None
            logger.info("HandLandmarker unloaded")

    @classmethod
    def process_video(cls, video_path: str, video_id: str = "") -> tuple[str, bool]:
        """
        Scan every frame, pick the one with the most hand landmarks visible,
        draw the landmarks on it, save a debug PNG, and return (base64_jpg, landmarks_found).
        """
        if cls._landmarker is None:
            raise RuntimeError("HandTracker not loaded — call HandTracker.load() at startup")

        cap = cv2.VideoCapture(video_path)
        best_frame = None
        best_annotated = None
        best_count = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = cls._landmarker.detect(mp_img)
            count = sum(len(hand) for hand in result.hand_landmarks)
            if count > best_count:
                best_count = count
                best_frame = frame.copy()
                best_annotated = _draw_landmarks(frame, result)

        cap.release()

        if best_frame is None:
            logger.warning("No frames could be read from %s", video_path)
            return "", False

        # Fall back to un-annotated frame if no hands found
        if best_annotated is None:
            best_annotated = best_frame

        # Save debug PNG so you can open it and see what goes to Gemini
        _DEBUG_DIR.mkdir(parents=True, exist_ok=True)
        tag = video_id or Path(video_path).stem
        debug_path = _DEBUG_DIR / f"{tag}.png"
        cv2.imwrite(str(debug_path), best_annotated)
        logger.info("Debug frame saved → %s  (landmarks detected: %d)", debug_path, best_count)

        _, buf = cv2.imencode(".jpg", best_annotated)
        b64 = base64.b64encode(buf).decode()
        return b64, best_count > 0
