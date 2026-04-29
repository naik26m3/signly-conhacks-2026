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
            running_mode=vision.RunningMode.VIDEO,
            num_hands=2,
        )
        cls._landmarker = vision.HandLandmarker.create_from_options(options)
        logger.info("HandLandmarker ready (VIDEO mode)")

    @classmethod
    def unload(cls) -> None:
        if cls._landmarker is not None:
            cls._landmarker.close()
            cls._landmarker = None
            logger.info("HandLandmarker unloaded")

    @classmethod
    def process_video(cls, video_path: str, video_id: str = "") -> tuple[list[dict], bool]:
        """Process video in VIDEO mode, return (landmark_sequence, landmarks_found).

        landmark_sequence: list of per-frame dicts sampled every 3rd frame.
        Each entry: {"frame": int, "right": [[x,y,z]x21], "left": [[x,y,z]x21]}
        landmarks_found: True if any hand was detected in any frame.
        """
        if cls._landmarker is None:
            raise RuntimeError("HandTracker not loaded — call HandTracker.load() at startup")

        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        if not cap.isOpened():
            cap.release()
            raise ValueError(f"Cannot open video: {video_path}")

        landmark_sequence: list[dict] = []
        best_annotated = None
        best_count = 0
        frame_idx = 0

        try:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                timestamp_ms = int((frame_idx / fps) * 1000)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                result = cls._landmarker.detect_for_video(mp_img, timestamp_ms)

                count = sum(len(hand) for hand in result.hand_landmarks)
                if count > best_count:
                    best_count = count
                    best_annotated = _draw_landmarks(frame, result)

                if frame_idx % 3 == 0 and result.hand_landmarks:
                    entry: dict = {"frame": frame_idx}
                    for hand_landmarks, handedness in zip(result.hand_landmarks, result.handedness):
                        side = "right" if handedness[0].category_name == "Right" else "left"
                        entry[side] = [
                            [round(lm.x, 4), round(lm.y, 4), round(lm.z, 4)]
                            for lm in hand_landmarks
                        ]
                    landmark_sequence.append(entry)

                frame_idx += 1
        finally:
            cap.release()

        landmarks_found = best_count > 0

        if best_annotated is not None:
            _DEBUG_DIR.mkdir(parents=True, exist_ok=True)
            tag = video_id or Path(video_path).stem
            debug_path = _DEBUG_DIR / f"{tag}.png"
            cv2.imwrite(str(debug_path), best_annotated)
            logger.info("Debug frame saved → %s  (landmarks: %d)", debug_path, best_count)

        return landmark_sequence, landmarks_found
