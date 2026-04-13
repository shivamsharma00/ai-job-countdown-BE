"""Pydantic models for API request and response schemas."""

from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.sanitize import sanitize_text


# ── Sanitized text helper ──

def _sanitize(v: str) -> str:
    return sanitize_text(v)


# ── Geo models ──

class GeoResponse(BaseModel):
    city: str
    region: str
    country: str


# ── Suggestion request/response models ──

class RoleSuggestionsRequest(BaseModel):
    city: str = Field(default="", max_length=100)
    region: str = Field(default="", max_length=100)

    @field_validator("city", "region")
    @classmethod
    def sanitize_geo_fields(cls, v: str) -> str:
        return _sanitize(v)


class RoleSuggestionsResponse(BaseModel):
    roles: list[str]


class CitySuggestionsRequest(BaseModel):
    city: str = Field(default="", max_length=100)
    region: str = Field(default="", max_length=100)

    @field_validator("city", "region")
    @classmethod
    def sanitize_geo_fields(cls, v: str) -> str:
        return _sanitize(v)


class CitySuggestionsResponse(BaseModel):
    cities: list[str]


class TaskSuggestionsRequest(BaseModel):
    role: str = Field(..., min_length=1, max_length=200)
    company_size: str = Field(default="", max_length=50)

    @field_validator("role", "company_size")
    @classmethod
    def sanitize_fields(cls, v: str) -> str:
        return _sanitize(v)


class TaskSuggestionsResponse(BaseModel):
    tasks: list[str]


# ── Existing request models (with sanitization added) ──

class EstimateRequest(BaseModel):
    role: str = Field(..., min_length=1, max_length=200, description="Job title")
    location: str = Field(..., min_length=1, max_length=200, description="Geographic location")
    company_size: str = Field(default="", max_length=50, description="e.g. 1-10, 11-100, 100-1000, 1000+")
    company_name: str = Field(default="", max_length=200, description="Optional company name")
    tasks: list[str] = Field(default_factory=list, description="List of daily task categories")
    ai_usage: int = Field(default=20, ge=0, le=100, description="Current AI usage percentage")

    @field_validator("role", "company_name")
    @classmethod
    def sanitize_text_fields(cls, v: str) -> str:
        return _sanitize(v)


class FeedRequest(BaseModel):
    role: str = Field(..., min_length=1, max_length=200)
    location: str = Field(..., min_length=1, max_length=200)
    company_size: str = Field(default="", max_length=50)
    tasks: list[str] = Field(default_factory=list)

    @field_validator("role")
    @classmethod
    def sanitize_role(cls, v: str) -> str:
        return _sanitize(v)


# ── Existing response models (unchanged) ──

class Factor(BaseModel):
    name: str
    value: int = Field(ge=0, le=100)


class Tip(BaseModel):
    icon: str
    title: str
    text: str


class OccupationMatch(BaseModel):
    soc_code: str
    title: str
    matched: bool


class DataSources(BaseModel):
    eloundou_alpha: Optional[float] = None
    eloundou_beta: Optional[float] = None
    eloundou_score: float
    eloundou_available: bool
    aioe_raw: Optional[float] = None
    aioe_normalized: float
    aioe_available: bool
    task_exposure: Optional[float] = None
    tasks_analyzed: int
    company_modifier: float
    ai_usage_modifier: float
    bls_employment_national: Optional[int] = None
    bls_median_wage_national: Optional[int] = None
    final_exposure: float


class EstimateResponse(BaseModel):
    years: int = Field(ge=1, le=30)
    risk: str = Field(pattern=r"^(critical|high|moderate|low)$")
    description: str
    factors: list[Factor]
    tips: list[Tip]
    occupation: Optional[OccupationMatch] = None
    data_sources: Optional[DataSources] = None


class FeedItem(BaseModel):
    type: str = Field(pattern=r"^(news|social|research)$")
    title: str
    source: str
    url: str = ""
    time: str
    tag: str


class FeedResponse(BaseModel):
    items: list[FeedItem]
