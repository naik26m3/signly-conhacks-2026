import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).parent.parent / "data" / "raw"


class CollectorService:
    """Appends inference and correction records to local JSONL files.

    All I/O is offloaded to a thread via ``asyncio.to_thread`` so the event
    loop stays unblocked even on slower disks.
    """

    async def log_inference(
        self,
        video_id: str,
        gloss: str,
        english: str,
        confidence: float,
        landmarks_found: bool,
    ) -> None:
        """Append one inference record to ``data/raw/inferences.jsonl``."""
        record = {
            "video_id": video_id,
            "gloss": gloss,
            "english": english,
            "confidence": confidence,
            "landmarks_found": landmarks_found,
            "ts": datetime.now(timezone.utc).isoformat(),
        }
        await self._append(_DATA_DIR / "inferences.jsonl", record)
        logger.info("log_inference: video_id=%s gloss=%s", video_id, gloss)

    async def log_correction(
        self,
        video_id: str,
        correct_gloss: str,
        notes: str = "",
    ) -> str:
        """Append one correction record to ``data/raw/corrections.jsonl``.

        Returns the auto-generated UUID of the new record.
        """
        record = {
            "id": str(uuid.uuid4()),
            "video_id": video_id,
            "correct_gloss": correct_gloss,
            "notes": notes,
            "ts": datetime.now(timezone.utc).isoformat(),
        }
        await self._append(_DATA_DIR / "corrections.jsonl", record)
        logger.info("log_correction: video_id=%s gloss=%s id=%s", video_id, correct_gloss, record["id"])
        return record["id"]

    @staticmethod
    async def _append(path: Path, record: dict) -> None:
        """Serialise *record* as a JSON line and append it to *path*."""
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(record) + "\n"
        await asyncio.to_thread(_write_line, str(path), line)


def _write_line(path: str, line: str) -> None:
    """Synchronous helper called from a thread pool via ``asyncio.to_thread``."""
    with open(path, "a", encoding="utf-8") as f:
        f.write(line)


collector = CollectorService()
