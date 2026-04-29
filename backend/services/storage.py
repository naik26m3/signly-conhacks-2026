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
    video_id = str(uuid.uuid4())
    contents = await file.read()

    if len(contents) > MAX_FILE_SIZE:
        raise ValueError(f"file exceeds 50MB limit")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.seaweedfs_filer_url}/videos/{video_id}.mp4",
            files={"file": (f"{video_id}.mp4", contents, file.content_type)},
        )
        response.raise_for_status()

    url = f"{settings.seaweedfs_filer_url}/videos/{video_id}.mp4"
    logger.info(f"saved video {video_id} to seaweedfs")
    return {"video_id": video_id, "url": url}
