from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str


class PersonSummary(BaseModel):
    id: str
    name: str
    color: str
    photo_url: str | None


class JobListItem(BaseModel):
    id: str
    video_filename: str
    status: str
    stage: str | None
    progress_pct: float
    created_at: datetime
    duration_s: float | None
    persons: list[PersonSummary]


class JobDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    video_filename: str
    status: str
    stage: str | None
    progress_pct: float
    error: str | None
    created_at: datetime
    finished_at: datetime | None
    duration_s: float | None


class SightingOut(BaseModel):
    start_s: float
    end_s: float
    confidence: float
    match_type: str
    screenshot_url: str
    thumbnail_url: str
    box: dict


class PersonOut(BaseModel):
    id: str
    name: str
    color: str
    photo_urls: list[str]
    sightings: list[SightingOut]


class VideoInfo(BaseModel):
    duration_s: float | None
    fps: float | None
    width: int | None
    height: int | None
    url: str


class ResultsOut(BaseModel):
    video: VideoInfo
    persons: list[PersonOut]
