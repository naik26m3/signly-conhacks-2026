from models.handTracking import HandTracker


def extract_frame(video_path: str, video_id: str = "") -> tuple[str, bool]:
    """Extract best hand-landmark frame. Returns (base64_jpg, landmarks_found)."""
    return HandTracker.process_video(video_path, video_id)
