"""Onboarding conversation state definitions and MongoDB persistence."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

from src.core.database import mongodb_connection
from src.core.logger import get_logger

logger = get_logger("conversation.state")

COLLECTION = "onboarding_sessions"
SESSION_TTL_DAYS = 7


class OnboardingState(str, Enum):
    CAREER_GOAL = "CAREER_GOAL"
    RESUME = "RESUME"
    GITHUB = "GITHUB"
    COMPLETE = "COMPLETE"


class ChannelType(str, Enum):
    DISCORD = "DISCORD"
    TELEGRAM = "TELEGRAM"


@dataclass
class ConversationSession:
    channel_type: str
    channel_user_id: str
    state: str = OnboardingState.CAREER_GOAL
    career_goal_text: Optional[str] = None
    resume_id: Optional[str] = None
    github_username: Optional[str] = None
    careeros_user_id: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_doc(self) -> dict:
        return {
            "channel_type": self.channel_type,
            "channel_user_id": self.channel_user_id,
            "state": self.state,
            "career_goal_text": self.career_goal_text,
            "resume_id": self.resume_id,
            "github_username": self.github_username,
            "careeros_user_id": self.careeros_user_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "expires_at": self.updated_at + timedelta(days=SESSION_TTL_DAYS),
        }

    @classmethod
    def from_doc(cls, doc: dict) -> ConversationSession:
        return cls(
            channel_type=doc["channel_type"],
            channel_user_id=doc["channel_user_id"],
            state=doc.get("state", OnboardingState.CAREER_GOAL),
            career_goal_text=doc.get("career_goal_text"),
            resume_id=doc.get("resume_id"),
            github_username=doc.get("github_username"),
            careeros_user_id=doc.get("careeros_user_id"),
            created_at=doc.get("created_at", datetime.utcnow()),
            updated_at=doc.get("updated_at", datetime.utcnow()),
        )


def _col():
    return mongodb_connection.main_database[COLLECTION]


async def get_session(channel_user_id: str, channel_type: str) -> Optional[ConversationSession]:
    doc = await _col().find_one(
        {"channel_user_id": channel_user_id, "channel_type": channel_type}
    )
    return ConversationSession.from_doc(doc) if doc else None


async def save_session(session: ConversationSession) -> None:
    session.updated_at = datetime.utcnow()
    doc = session.to_doc()
    await _col().update_one(
        {"channel_user_id": session.channel_user_id, "channel_type": session.channel_type},
        {"$set": doc},
        upsert=True,
    )


async def delete_session(channel_user_id: str, channel_type: str) -> None:
    await _col().delete_one(
        {"channel_user_id": channel_user_id, "channel_type": channel_type}
    )
