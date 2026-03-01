"""Shared dataclasses for cross-module data contracts."""
from dataclasses import dataclass, field
from typing import Literal

StatusLabel = Literal[
    "Rising & Healthy",
    "Mature & Stable",
    "Hype-Driven",
    "Niche but Strong",
    "At Risk",
]


@dataclass
class RepoScore:
    full_name: str          # e.g. "owner/repo"
    url: str
    description: str
    score_growth: float     # 0–100
    score_health: float
    score_quality: float
    score_adoption: float
    score_total: float
    status: StatusLabel
    stars: int
    forks: int
    recent_commits: int


@dataclass
class ResearchResult:
    full_name: str
    url: str
    status: StatusLabel
    score_total: float
    key_changes: list[str] = field(default_factory=list)
    implications: list[str] = field(default_factory=list)
    recommendation: str = ""


@dataclass
class EpisodeRecord:
    title: str
    guid: str               # stable unique identifier
    pub_date: str           # RFC 2822
    mp3_url: str            # absolute URL to hosted audio
    file_size_bytes: int
    duration_seconds: int = 0
