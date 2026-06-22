"""Discord embed builders for CareerOS daily digest payloads."""

from __future__ import annotations

import discord
from typing import List

from src.dto.careeros.careeros_dtos import CareerOsJobDigestPayload, JobCard, UserDigestSection


def build_job_card_embed(job: JobCard, *, color: discord.Color = discord.Color.blue()) -> discord.Embed:
    """Build a Discord embed for a single job card."""
    embed = discord.Embed(
        title=f"[{job.score:.0f}점] {job.title} @ {job.company_name}",
        url=job.apply_url,
        color=color,
    )

    if job.matched_skills:
        embed.add_field(
            name="✅ 매칭 스킬",
            value=", ".join(job.matched_skills[:8]),
            inline=False,
        )
    if job.missing_skills:
        embed.add_field(
            name="❌ 부족 스킬",
            value=", ".join(job.missing_skills[:5]),
            inline=False,
        )

    meta_parts = []
    if job.role_category:
        meta_parts.append(job.role_category)
    if job.country:
        meta_parts.append(job.country)
    if job.remote_type:
        meta_parts.append(job.remote_type)
    if meta_parts:
        embed.set_footer(text=" · ".join(meta_parts))

    return embed


def build_digest_embeds(
    section: UserDigestSection,
    digest_date: str,
) -> List[discord.Embed]:
    """Build a list of embeds for one user's digest section."""
    if not section.jobs:
        return []

    header = discord.Embed(
        title=f"🔍 오늘의 채용 공고 — {digest_date}",
        description=f"총 {len(section.jobs)}개 공고가 선별되었습니다.",
        color=discord.Color.green(),
    )

    job_embeds = [
        build_job_card_embed(job, color=discord.Color.blue())
        for job in section.jobs
    ]

    return [header, *job_embeds]


def build_digest_embeds_from_payload(
    payload: CareerOsJobDigestPayload,
) -> dict[int, List[discord.Embed]]:
    """Map userId → embed list for the entire payload."""
    return {
        section.user_id: build_digest_embeds(section, payload.digest_date)
        for section in payload.sections
        if section.jobs
    }
