"""CareerOS MCP tools exposed as FastAPI routes.

Claude Code (or any MCP client) can call these endpoints to:
  - Toggle notification channels (Discord / Telegram)
  - Trigger an on-demand job digest
  - Query the last digest run status
"""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.core.database import mongodb_connection
from src.core.logger import get_logger

logger = get_logger("mcp.careeros")

careeros_mcp_router = APIRouter(prefix="/mcp/careeros", tags=["careeros-mcp"])

MCP_CONFIG_COLLECTION = "careeros_mcp_config"


# ── request / response models ──────────────────────────────────────

class ConfigureChannelRequest(BaseModel):
    channel_type: str  # "discord" | "telegram"
    enabled: bool


class SendDigestRequest(BaseModel):
    channel_type: str = "discord"
    user_id: Optional[int] = None


# ── helpers ────────────────────────────────────────────────────────

def _config_col():
    return mongodb_connection.main_database[MCP_CONFIG_COLLECTION]


# ── endpoints ──────────────────────────────────────────────────────

@careeros_mcp_router.post("/configure_channel")
async def configure_channel(body: ConfigureChannelRequest) -> dict:
    """careeros.configure_channel — Toggle a notification channel on/off.

    Stores the setting in MongoDB so it survives restarts.
    CareerOS reads `app.telegram.enabled` / `app.dinobot.*` from its own config;
    this endpoint records the *dinobot-side* preference and can be read by Claude
    when it needs to know which channels are active.
    """
    channel_type = body.channel_type.lower()
    if channel_type not in ("discord", "telegram"):
        raise HTTPException(status_code=400, detail="channel_type must be 'discord' or 'telegram'")

    await _config_col().update_one(
        {"key": f"channel.{channel_type}"},
        {"$set": {"key": f"channel.{channel_type}", "enabled": body.enabled}},
        upsert=True,
    )
    logger.info("MCP: channel '%s' set to enabled=%s", channel_type, body.enabled)
    return {"channel_type": channel_type, "enabled": body.enabled}


@careeros_mcp_router.post("/send_digest")
async def send_digest(body: SendDigestRequest) -> dict:
    """careeros.send_digest — Trigger an on-demand job digest.

    Calls the CareerOS digest trigger endpoint and returns the result.
    """
    try:
        from src.service.careeros import careeros_client
        result = await careeros_client.trigger_digest(user_id=body.user_id)
        logger.info("MCP: digest triggered for channel=%s, user=%s", body.channel_type, body.user_id)
        return {"triggered": True, "channel_type": body.channel_type, "detail": result}
    except Exception as exc:
        logger.error("MCP send_digest failed: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc))


@careeros_mcp_router.get("/digest_status")
async def digest_status() -> dict:
    """careeros.digest_status — Return last digest run metadata.

    Combines CareerOS-side status with dinobot channel config.
    """
    try:
        from src.service.careeros import careeros_client
        careeros_status = await careeros_client.get_digest_status()
    except Exception as exc:
        logger.warning("Could not fetch CareerOS digest status: %s", exc)
        careeros_status = {"error": str(exc)}

    # read channel config from MongoDB
    channels = {}
    async for doc in _config_col().find({"key": {"$regex": "^channel\\."}}):
        key = doc["key"].replace("channel.", "")
        channels[key] = doc.get("enabled", False)

    return {
        "careeros": careeros_status,
        "channels": channels,
    }
