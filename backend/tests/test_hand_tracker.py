import numpy as np
import pytest
from unittest.mock import MagicMock, patch


def _make_landmark(x, y, z):
    lm = MagicMock()
    lm.x, lm.y, lm.z = x, y, z
    return lm


def _make_handedness(name):
    cat = MagicMock()
    cat.category_name = name
    return [cat]


def _make_detection_result(right_landmarks=None, left_landmarks=None):
    result = MagicMock()
    hand_landmarks = []
    handedness = []
    if right_landmarks:
        hand_landmarks.append(right_landmarks)
        handedness.append(_make_handedness("Right"))
    if left_landmarks:
        hand_landmarks.append(left_landmarks)
        handedness.append(_make_handedness("Left"))
    result.hand_landmarks = hand_landmarks
    result.handedness = handedness
    return result


def test_process_video_returns_landmark_sequence_and_found():
    """process_video returns (list[dict], True) when hands detected."""
    fake_landmarks = [_make_landmark(0.1 * i, 0.2 * i, 0.0) for i in range(21)]
    result_with_hands = _make_detection_result(right_landmarks=fake_landmarks)

    import sys
    sys.path.insert(0, "/home/dat/Documents/signly-conhacks-2026")
    from models.handTracking import HandTracker

    mock_cap = MagicMock()
    frames = [
        (True, np.zeros((480, 640, 3), dtype=np.uint8)),
        (True, np.zeros((480, 640, 3), dtype=np.uint8)),
        (True, np.zeros((480, 640, 3), dtype=np.uint8)),
        (False, None),
    ]
    mock_cap.isOpened.side_effect = [True, True, True, True, False]
    mock_cap.read.side_effect = frames
    mock_cap.get.return_value = 30.0

    mock_landmarker = MagicMock()
    mock_landmarker.detect_for_video.side_effect = [
        result_with_hands,
        result_with_hands,
        result_with_hands,
    ]

    with patch("cv2.VideoCapture", return_value=mock_cap), \
         patch("cv2.cvtColor", return_value=np.zeros((480, 640, 3), dtype=np.uint8)), \
         patch("cv2.imencode", return_value=(True, np.array([1, 2, 3]))), \
         patch("cv2.imwrite"), \
         patch.object(HandTracker, "_landmarker", mock_landmarker):
        sequence, found = HandTracker.process_video("/fake/video.mp4", "test_id")

    assert found is True
    assert isinstance(sequence, list)
    assert len(sequence) > 0
    first = sequence[0]
    assert "frame" in first
    assert "right" in first
    assert len(first["right"]) == 21
    assert len(first["right"][0]) == 3  # [x, y, z]


def test_process_video_returns_empty_when_no_hands():
    """process_video returns ([], False) when no hands detected."""
    import numpy as np
    import sys
    sys.path.insert(0, "/home/dat/Documents/signly-conhacks-2026")
    from models.handTracking import HandTracker

    result_no_hands = _make_detection_result()
    mock_cap = MagicMock()
    mock_cap.isOpened.side_effect = [True, False]
    mock_cap.read.side_effect = [(True, np.zeros((480, 640, 3), dtype=np.uint8)), (False, None)]
    mock_cap.get.return_value = 30.0

    mock_landmarker = MagicMock()
    mock_landmarker.detect_for_video.return_value = result_no_hands

    with patch("cv2.VideoCapture", return_value=mock_cap), \
         patch("cv2.cvtColor", return_value=np.zeros((480, 640, 3), dtype=np.uint8)), \
         patch("cv2.imwrite"), \
         patch.object(HandTracker, "_landmarker", mock_landmarker):
        sequence, found = HandTracker.process_video("/fake/video.mp4", "test_id")

    assert found is False
    assert sequence == []


def test_samples_every_third_frame():
    """Only frames at index 0, 3, 6, ... are included in the sequence."""
    import numpy as np
    import sys
    sys.path.insert(0, "/home/dat/Documents/signly-conhacks-2026")
    from models.handTracking import HandTracker

    fake_landmarks = [_make_landmark(0.1, 0.2, 0.0) for _ in range(21)]
    result_with_hands = _make_detection_result(right_landmarks=fake_landmarks)

    mock_cap = MagicMock()
    mock_cap.isOpened.side_effect = [True] * 7 + [False]
    mock_cap.read.side_effect = [(True, np.zeros((480, 640, 3), dtype=np.uint8))] * 7 + [(False, None)]
    mock_cap.get.return_value = 30.0

    mock_landmarker = MagicMock()
    mock_landmarker.detect_for_video.return_value = result_with_hands

    with patch("cv2.VideoCapture", return_value=mock_cap), \
         patch("cv2.cvtColor", return_value=np.zeros((480, 640, 3), dtype=np.uint8)), \
         patch("cv2.imencode", return_value=(True, np.array([1, 2, 3]))), \
         patch("cv2.imwrite"), \
         patch.object(HandTracker, "_landmarker", mock_landmarker):
        sequence, found = HandTracker.process_video("/fake/video.mp4", "test_id")

    frame_indices = [entry["frame"] for entry in sequence]
    for idx in frame_indices:
        assert idx % 3 == 0, f"frame {idx} is not a multiple of 3"
