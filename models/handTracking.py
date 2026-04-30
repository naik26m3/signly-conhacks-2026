import logging
import threading
from pathlib import Path

import cv2
import mediapipe as mp
from mediapipe.tasks.python import vision

logger = logging.getLogger(__name__)

_MODEL_PATH = Path(__file__).parent / "hand_landmarker.task"
_FACE_MODEL_PATH = Path(__file__).parent / "face_landmarker.task"


# MediaPipe FaceLandmarker indices for the points we care about for ASL sign location.
# Reference: https://developers.google.com/mediapipe/solutions/vision/face_landmarker
_KEY_FACE_LANDMARKS: dict[str, int] = {
    "forehead":      10,   # top center of forehead
    "chin":          152,  # tip of chin
    "nose_tip":      1,
    "left_cheek":    454,  # signer's left side (right side of frame)
    "right_cheek":   234,
    "mouth_left":    78,
    "mouth_right":   308,
    "left_eyebrow":  336,
    "right_eyebrow": 107,
}


class FaceTracker:
    """MediaPipe FaceLandmarker wrapper. Returns normalized [x, y] for key sign-relevant points."""
    _landmarker: "vision.FaceLandmarker | None" = None
    _last_timestamp_ms: int = -1

    @classmethod
    def load(cls) -> None:
        if cls._landmarker is not None:
            return
        logger.info("Loading MediaPipe FaceLandmarker from %s", _FACE_MODEL_PATH)
        options = vision.FaceLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(_FACE_MODEL_PATH)),
            running_mode=vision.RunningMode.VIDEO,
            num_faces=1,
        )
        cls._landmarker = vision.FaceLandmarker.create_from_options(options)
        logger.info("FaceLandmarker ready (VIDEO mode)")

    @classmethod
    def unload(cls) -> None:
        if cls._landmarker is not None:
            cls._landmarker.close()
            cls._landmarker = None
            cls._last_timestamp_ms = -1
            logger.info("FaceLandmarker unloaded")

    @classmethod
    def detect(cls, mp_img, timestamp_ms: int) -> dict | None:
        """Run FaceLandmarker on an already-prepared mp.Image. Returns dict of {name: [x, y]} or None."""
        if cls._landmarker is None:
            return None
        # Timestamps must be strictly increasing for VIDEO mode
        if timestamp_ms <= cls._last_timestamp_ms:
            timestamp_ms = cls._last_timestamp_ms + 1
        cls._last_timestamp_ms = timestamp_ms
        result = cls._landmarker.detect_for_video(mp_img, timestamp_ms)
        if not result.face_landmarks:
            return None
        face = result.face_landmarks[0]
        return {
            name: [round(face[idx].x, 4), round(face[idx].y, 4)]
            for name, idx in _KEY_FACE_LANDMARKS.items()
            if idx < len(face)
        }


class HandTracker:
    _landmarker: "vision.HandLandmarker | None" = None
    _landmarker_image: "vision.HandLandmarker | None" = None
    _last_timestamp_ms: int = -1
    _image_lock = threading.Lock()

    @classmethod
    def load(cls) -> None:
        if cls._landmarker is None:
            logger.info("Loading MediaPipe HandLandmarker from %s", _MODEL_PATH)
            options = vision.HandLandmarkerOptions(
                base_options=mp.tasks.BaseOptions(model_asset_path=str(_MODEL_PATH)),
                running_mode=vision.RunningMode.VIDEO,
                num_hands=2,
            )
            cls._landmarker = vision.HandLandmarker.create_from_options(options)
            logger.info("HandLandmarker ready (VIDEO mode)")

        if cls._landmarker_image is None:
            options_image = vision.HandLandmarkerOptions(
                base_options=mp.tasks.BaseOptions(model_asset_path=str(_MODEL_PATH)),
                running_mode=vision.RunningMode.IMAGE,
                num_hands=1,
            )
            cls._landmarker_image = vision.HandLandmarker.create_from_options(options_image)
            logger.info("HandLandmarker ready (IMAGE mode)")

    @classmethod
    def unload(cls) -> None:
        if cls._landmarker is not None:
            cls._landmarker.close()
            cls._landmarker = None
            cls._last_timestamp_ms = -1
            logger.info("HandLandmarker unloaded")
        if cls._landmarker_image is not None:
            cls._landmarker_image.close()
            cls._landmarker_image = None

    @classmethod
    def quick_detect(cls, video_path: str, samples: int = 6) -> bool:
        """Sample N evenly-spaced frames; return True as soon as one has a hand.

        Designed to be fast (< 1s on a 10s clip) — used as a pre-flight check
        before sending video to Gemini.
        """
        if cls._landmarker_image is None:
            raise RuntimeError("HandTracker not loaded — call HandTracker.load() at startup")

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            cap.release()
            return False
        try:
            total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if total <= 0:
                return False
            indices = [int(total * i / (samples + 1)) for i in range(1, samples + 1)]
            for idx in indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                ret, frame = cap.read()
                if not ret:
                    continue
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                with cls._image_lock:
                    result = cls._landmarker_image.detect(mp_img)
                if result.hand_landmarks:
                    return True
            return False
        finally:
            cap.release()

    @classmethod
    def process_video(cls, video_path: str, video_id: str = "") -> tuple[list[dict], bool]:
        """Return (landmark_sequence, landmarks_found).

        Each entry: {
          "frame": int,
          "face": {"forehead":[x,y], "chin":[x,y], "nose_tip":[x,y],
                   "left_cheek":[x,y], "right_cheek":[x,y],
                   "mouth_left":[x,y], "mouth_right":[x,y],
                   "left_eyebrow":[x,y], "right_eyebrow":[x,y]} or absent,
          "right": [[x,y,z]x21],        # dominant hand landmarks
          "left":  [[x,y,z]x21],        # non-dominant (if present)
          "right_vel": [dx, dy],         # wrist delta from previous sample
          "left_vel":  [dx, dy],
        }
        """
        if cls._landmarker is None:
            raise RuntimeError("HandTracker not loaded — call HandTracker.load() at startup")

        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        if not cap.isOpened():
            cap.release()
            raise ValueError(f"Cannot open video: {video_path}")

        landmark_sequence: list[dict] = []
        best_count = 0
        frame_idx = 0
        frames_with_hands = 0
        timestamp_ms = cls._last_timestamp_ms
        face_box: dict | None = None

        logger.info("process_video: start video=%s fps=%.1f last_ts=%d", video_path, fps, timestamp_ms)

        try:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                next_timestamp_ms = int((frame_idx / fps) * 1000)
                if next_timestamp_ms <= timestamp_ms:
                    next_timestamp_ms = timestamp_ms + 1
                timestamp_ms = next_timestamp_ms

                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                result = cls._landmarker.detect_for_video(mp_img, timestamp_ms)

                # Face landmarks every 4th frame; last value carried forward.
                # Faces barely move frame-to-frame, so 7-8fps is plenty of resolution
                # and saves ~2-3s vs running every other frame.
                if frame_idx % 4 == 0:
                    face_box = FaceTracker.detect(mp_img, timestamp_ms)

                count = sum(len(hand) for hand in result.hand_landmarks)
                if count > best_count:
                    best_count = count

                if result.hand_landmarks:
                    frames_with_hands += 1

                if frame_idx % 2 == 0 and result.hand_landmarks:
                    entry: dict = {"frame": frame_idx}

                    # Named face landmarks (forehead/chin/etc.) — see FaceTracker.
                    if face_box is not None:
                        entry["face"] = face_box

                    # Hand landmarks
                    for hand_landmarks, handedness in zip(result.hand_landmarks, result.handedness):
                        side = "right" if handedness[0].category_name == "Right" else "left"
                        entry[side] = [
                            [round(lm.x, 4), round(lm.y, 4), round(lm.z, 4)]
                            for lm in hand_landmarks
                        ]

                    # Wrist velocity (explicit motion — wrist is landmark index 0)
                    if landmark_sequence:
                        prev = landmark_sequence[-1]
                        for side in ("right", "left"):
                            if side in entry and side in prev:
                                pw = prev[side][0]
                                cw = entry[side][0]
                                entry[f"{side}_vel"] = [
                                    round(cw[0] - pw[0], 4),
                                    round(cw[1] - pw[1], 4),
                                ]

                    landmark_sequence.append(entry)

                frame_idx += 1
        finally:
            cap.release()
            cls._last_timestamp_ms = timestamp_ms

        logger.info(
            "process_video: done video=%s total_frames=%d frames_with_hands=%d"
            " sampled_landmark_frames=%d best_landmark_count=%d",
            video_path, frame_idx, frames_with_hands, len(landmark_sequence), best_count,
        )

        landmarks_found = best_count > 0
        return landmark_sequence, landmarks_found
