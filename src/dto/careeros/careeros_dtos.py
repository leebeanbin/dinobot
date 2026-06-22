"""DTOs for CareerOS ↔ dinobot webhook payloads."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class JobCard:
    job_id: str
    title: str
    company_name: str
    apply_url: str
    score: float
    matched_skills: List[str] = field(default_factory=list)
    missing_skills: List[str] = field(default_factory=list)
    role_category: Optional[str] = None
    country: Optional[str] = None
    remote_type: Optional[str] = None

    @classmethod
    def from_dict(cls, d: dict) -> JobCard:
        return cls(
            job_id=d.get("jobId", ""),
            title=d.get("title", ""),
            company_name=d.get("companyName", ""),
            apply_url=d.get("applyUrl", ""),
            score=float(d.get("score", 0)),
            matched_skills=d.get("matchedSkills", []),
            missing_skills=d.get("missingSkills", []),
            role_category=d.get("roleCategory"),
            country=d.get("country"),
            remote_type=d.get("remoteType"),
        )


@dataclass
class UserDigestSection:
    user_id: int
    jobs: List[JobCard] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> UserDigestSection:
        return cls(
            user_id=int(d.get("userId", 0)),
            jobs=[JobCard.from_dict(j) for j in d.get("jobs", [])],
        )


@dataclass
class CareerOsJobDigestPayload:
    digest_date: str
    sections: List[UserDigestSection] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> CareerOsJobDigestPayload:
        return cls(
            digest_date=d.get("digestDate", ""),
            sections=[UserDigestSection.from_dict(s) for s in d.get("sections", [])],
        )
