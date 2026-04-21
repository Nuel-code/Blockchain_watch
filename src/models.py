from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field


class Socials(BaseModel):
    twitter: Optional[str] = None
    telegram: Optional[str] = None
    discord: Optional[str] = None
    github: Optional[str] = None
    docs: Optional[str] = None


class Candidate(BaseModel):
    id: str
    chain: str
    first_seen: str
    snapshot_date: str
    object_type: str
    address: str

    deployer: Optional[str] = None
    name: Optional[str] = None
    symbol: Optional[str] = None
    decimals: Optional[int] = None

    website: Optional[str] = None
    socials: Socials = Field(default_factory=Socials)
    social_source: str = "none"
    social_confidence: float = 0.0

    liquidity_usd: float = 0.0
    unique_external_wallets_1h: int = 0
    tx_count_1h: int = 0
    time_to_first_liquidity: Optional[int] = None

    recognized_factory: bool = False
    recognized_factory_name: Optional[str] = None
    source_verified: bool = False

    deployer_quality_score: float = 0.0

    spam_score: float = 0.0
    scam_score: float = 0.0

    relevance_score: float = 0.0
    confidence_score: float = 0.0
    momentum_score: float = 0.0

    why_kept: list[str] = Field(default_factory=list)
    why_flagged: list[str] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)
    action: str = "ignore"

    raw_refs: dict = Field(default_factory=dict)
