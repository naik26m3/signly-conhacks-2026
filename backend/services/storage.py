import uuid
import httpx
import logging
from fastapi import UploadFile
from config.settings import settings

logger = logging.getLogger(__name__)

ALLOWED_MIME_TYPES = {"video/mp4", "video/quicktime", "video/webm"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

WEBM_MAGIC = b"\x1a\x45\xdf\xa3"


async def validate(file: UploadFile) -> tuple[bool, str]:
    if file.content_type not in ALLOWED_MIME_TYPES:
        return False, f"file type not allowed: {file.content_type}"

    header = await file.read(32)
    await file.seek(0)

    is_isobmff = len(header) >= 8 and header[4:8] == b"ftyp"
    is_webm = header.startswith(WEBM_MAGIC)
    if not (is_isobmff or is_webm):
        return False, "file content does not match a valid video format"

    return True, ""


async def save(file: UploadFile) -> dict:
    file_id = str(uuid.uuid4())
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise ValueError("file exceeds 50MB limit")
    return await save_bytes(contents, file_id, file.content_type or "video/mp4")


async def save_bytes(
    contents: bytes,
    file_id: str,
    content_type: str = "video/mp4",
    *,
    folder: str = "videos",
    ext: str = "mp4",
) -> dict:
    """Save bytes to SeaweedFS. Returns {"file_id": ..., "url": ...}.

    Defaults to /videos/{file_id}.mp4. Pass folder="audio", ext="mp3" for TTS audio.
    """
    if len(contents) > MAX_FILE_SIZE:
        raise ValueError("file exceeds 50MB limit")

    url = f"{settings.seaweedfs_filer_url}/{folder}/{file_id}.{ext}"
    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            files={"file": (f"{file_id}.{ext}", contents, content_type)},
        )
        response.raise_for_status()

    logger.info("saved %s/%s.%s to seaweedfs", folder, file_id, ext)
    return {"file_id": file_id, "url": url}
