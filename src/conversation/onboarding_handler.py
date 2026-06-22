"""Onboarding conversation state machine."""

from __future__ import annotations

from typing import Optional

from src.core.logger import get_logger
from src.service.careeros import careeros_client
from .state import (
    ConversationSession,
    OnboardingState,
    ChannelType,
    get_session,
    save_session,
    delete_session,
)
from .file_upload_handler import handle_pdf_attachment

logger = get_logger("conversation.onboarding")

WELCOME_MSG = (
    "안녕하세요! 커리어OS에 오신 것을 환영합니다 🦕\n"
    "어떤 개발자가 되고 싶으신가요?\n"
    "*(예: 백엔드, DevOps, ML 엔지니어 등 자유롭게 입력해 주세요)*"
)

RESUME_PROMPT = (
    "좋아요! 이력서 PDF를 업로드해 주세요.\n"
    "*(없으시면 `/skip` 입력)*"
)

GITHUB_PROMPT = (
    "GitHub 아이디를 알려주세요.\n"
    "*(없으시면 `/skip` 입력)*"
)

COMPLETE_MSG = (
    "✅ 커리어 프로필 생성 완료!\n"
    "매일 아침 맞춤 공고를 보내드릴게요."
)


class OnboardingHandler:
    """Stateless handler — state lives in MongoDB via ConversationSession."""

    async def start(
        self,
        channel_user_id: str,
        channel_type: str = ChannelType.DISCORD,
        careeros_user_id: Optional[int] = None,
    ) -> str:
        """Create (or reset) a session and return the first prompt."""
        session = ConversationSession(
            channel_type=channel_type,
            channel_user_id=channel_user_id,
            state=OnboardingState.CAREER_GOAL,
            careeros_user_id=careeros_user_id,
        )
        await save_session(session)
        return WELCOME_MSG

    async def handle_message(
        self,
        channel_user_id: str,
        channel_type: str = ChannelType.DISCORD,
        text: str = "",
        attachment_url: Optional[str] = None,
        attachment_name: Optional[str] = None,
    ) -> Optional[str]:
        """Process an incoming message and advance the state machine.

        Returns the bot reply, or None if the user has no active session.
        """
        session = await get_session(channel_user_id, channel_type)
        if not session or session.state == OnboardingState.COMPLETE:
            return None

        state = session.state

        if state == OnboardingState.CAREER_GOAL:
            return await self._handle_career_goal(session, text)

        if state == OnboardingState.RESUME:
            return await self._handle_resume(session, text, attachment_url, attachment_name)

        if state == OnboardingState.GITHUB:
            return await self._handle_github(session, text)

        return None

    async def get_session(
        self, channel_user_id: str, channel_type: str = ChannelType.DISCORD
    ) -> Optional[ConversationSession]:
        return await get_session(channel_user_id, channel_type)

    async def delete_session(
        self, channel_user_id: str, channel_type: str = ChannelType.DISCORD
    ) -> None:
        await delete_session(channel_user_id, channel_type)

    # ── private helpers ──────────────────────────────────────────

    async def _handle_career_goal(self, session: ConversationSession, text: str) -> str:
        if not text.strip():
            return "커리어 목표를 입력해 주세요 😊"
        session.career_goal_text = text.strip()
        session.state = OnboardingState.RESUME
        await save_session(session)
        return RESUME_PROMPT

    async def _handle_resume(
        self,
        session: ConversationSession,
        text: str,
        attachment_url: Optional[str],
        attachment_name: Optional[str],
    ) -> str:
        if text.strip().lower() == "/skip":
            session.state = OnboardingState.GITHUB
            await save_session(session)
            return GITHUB_PROMPT

        if attachment_url and attachment_name and attachment_name.lower().endswith(".pdf"):
            try:
                resume_id = await handle_pdf_attachment(attachment_url, attachment_name)
                session.resume_id = resume_id
                session.state = OnboardingState.GITHUB
                await save_session(session)
                return f"이력서 분석 중... ⏳\n\n{GITHUB_PROMPT}"
            except Exception as exc:
                logger.error("Resume upload failed: %s", exc)
                return "❌ 이력서 업로드 중 오류가 발생했습니다. 다시 시도하거나 `/skip` 을 입력해 주세요."

        return "PDF 파일을 첨부하거나 `/skip` 을 입력해 주세요."

    async def _handle_github(self, session: ConversationSession, text: str) -> str:
        if text.strip().lower() == "/skip":
            session.state = OnboardingState.COMPLETE
            await save_session(session)
            return COMPLETE_MSG

        github_username = text.strip().lstrip("@")
        if not github_username:
            return "GitHub 아이디를 입력해 주세요 (예: leebeanbin)"

        session.github_username = github_username
        session.state = OnboardingState.COMPLETE
        await save_session(session)

        if session.careeros_user_id:
            try:
                await careeros_client.trigger_github_sync(
                    session.careeros_user_id, github_username
                )
                return f"GitHub `{github_username}` 분석 중... 🔍\n\n{COMPLETE_MSG}"
            except Exception as exc:
                logger.warning("GitHub sync trigger failed: %s", exc)

        return COMPLETE_MSG


onboarding_handler = OnboardingHandler()
