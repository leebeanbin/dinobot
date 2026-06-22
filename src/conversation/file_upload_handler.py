"""Download a Discord attachment and relay it to CareerOS."""

import httpx
from src.core.logger import get_logger
from src.service.careeros import careeros_client

logger = get_logger("conversation.file_upload")


async def download_attachment(url: str) -> bytes:
    """Fetch raw bytes from a Discord CDN URL."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.content


async def handle_pdf_attachment(attachment_url: str, filename: str) -> str:
    """Download the PDF from Discord and upload it to CareerOS.

    Returns the resumeId assigned by CareerOS.
    """
    pdf_bytes = await download_attachment(attachment_url)
    logger.info("Downloaded attachment %s (%d bytes)", filename, len(pdf_bytes))
    resume_id = await careeros_client.upload_resume(pdf_bytes, filename=filename)
    return resume_id
