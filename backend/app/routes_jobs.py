import json
import os

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.datastructures import UploadFile

from .auth import get_current_user
from .db import get_db
from .models import Job, Person, User
from .schemas import (
    JobDetail,
    JobListItem,
    PersonOut,
    ResultsOut,
    SightingOut,
    VideoInfo,
)
from .storage import job_key

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

PERSON_COLORS = ["#e05252", "#4f9cf0", "#4fc07a", "#e0a34f", "#a06fe0", "#e05c9c"]
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_PERSONS = 6


def get_owned_job(
    job_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Job:
    job = db.get(Job, job_id)
    if job is None or job.user_id != user.id:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


def _media_url(job: Job, key: str) -> str:
    prefix = job_key(job.user_id, job.id) + "/"
    return f"/api/media/{job.id}/{key.removeprefix(prefix)}"


@router.post("", status_code=201)
async def create_job(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    form = await request.form()

    video = form.get("video")
    if not isinstance(video, UploadFile):
        raise HTTPException(status_code=422, detail="A video file is required")
    video_ext = os.path.splitext(video.filename or "")[1].lower()
    if video_ext not in VIDEO_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported video type '{video_ext}'. Allowed: {sorted(VIDEO_EXTENSIONS)}",
        )

    try:
        persons_meta = json.loads(form.get("persons") or "")
    except (json.JSONDecodeError, TypeError):
        raise HTTPException(status_code=422, detail="'persons' must be a JSON array")
    if not isinstance(persons_meta, list) or not 1 <= len(persons_meta) <= MAX_PERSONS:
        raise HTTPException(
            status_code=422, detail=f"Between 1 and {MAX_PERSONS} persons required"
        )

    storage = request.app.state.storage
    validator = request.app.state.photo_validator

    job = Job(user_id=user.id, video_filename=video.filename or "video", video_key="")
    db.add(job)
    db.flush()

    job.video_key = job_key(user.id, job.id, f"video{video_ext}")
    storage.put_bytes(job.video_key, await video.read(), content_type=video.content_type)

    warnings: list[str] = []
    for i, meta in enumerate(persons_meta):
        name = (meta.get("name") or "").strip() if isinstance(meta, dict) else ""
        if not name:
            raise HTTPException(status_code=422, detail=f"Person {i + 1} needs a name")
        photos = [p for p in form.getlist(f"photos_{i}") if isinstance(p, UploadFile)]
        if not 1 <= len(photos) <= 3:
            raise HTTPException(
                status_code=422, detail=f"'{name}' needs between 1 and 3 photos"
            )

        person = Person(
            job_id=job.id, name=name, color=PERSON_COLORS[i % len(PERSON_COLORS)],
            photo_keys=[],
        )
        db.add(person)
        db.flush()

        keys = []
        for n, photo in enumerate(photos):
            ext = os.path.splitext(photo.filename or "")[1].lower()
            if ext not in IMAGE_EXTENSIONS:
                raise HTTPException(
                    status_code=422, detail=f"Unsupported image type '{ext}' for '{name}'"
                )
            data = await photo.read()
            key = job_key(user.id, job.id, f"persons/{person.id}/photo_{n}{ext}")
            storage.put_bytes(key, data, content_type=photo.content_type)
            keys.append(key)
            if not validator(data):
                warnings.append(f"No face detected in photo {n + 1} of {name}")
        person.photo_keys = keys

    db.commit()
    request.app.state.job_queue.submit(job.id)
    return {"job_id": job.id, "warnings": warnings}


@router.get("", response_model=list[JobListItem])
def list_jobs(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    jobs = db.scalars(
        select(Job).where(Job.user_id == user.id).order_by(Job.created_at.desc())
    ).all()
    return [
        JobListItem(
            id=j.id, video_filename=j.video_filename, status=j.status, stage=j.stage,
            progress_pct=j.progress_pct, created_at=j.created_at,
            person_names=[p.name for p in j.persons],
        )
        for j in jobs
    ]


@router.get("/{job_id}", response_model=JobDetail)
def get_job(job: Job = Depends(get_owned_job)):
    return job


@router.post("/{job_id}/cancel")
def cancel_job(request: Request, job: Job = Depends(get_owned_job), db: Session = Depends(get_db)):
    if job.status == "queued":
        job.status = "cancelled"
        db.commit()
    elif job.status == "processing":
        request.app.state.job_queue.request_cancel(job.id)
    else:
        raise HTTPException(status_code=409, detail=f"Job is already {job.status}")
    return {"status": job.status}


@router.get("/{job_id}/results", response_model=ResultsOut)
def get_results(job: Job = Depends(get_owned_job)):
    if job.status != "done":
        raise HTTPException(status_code=409, detail=f"Job is {job.status}, not done")
    return ResultsOut(
        video=VideoInfo(
            duration_s=job.duration_s, fps=job.fps, width=job.width, height=job.height,
            url=_media_url(job, job.video_key),
        ),
        persons=[
            PersonOut(
                id=p.id, name=p.name, color=p.color,
                photo_urls=[_media_url(job, k) for k in p.photo_keys],
                sightings=[
                    SightingOut(
                        start_s=s.start_s, end_s=s.end_s, confidence=s.confidence,
                        match_type=s.match_type,
                        screenshot_url=_media_url(job, s.screenshot_key),
                        thumbnail_url=_media_url(job, s.thumbnail_key),
                        box=s.box,
                    )
                    for s in sorted(p.sightings, key=lambda s: s.start_s)
                ],
            )
            for p in job.persons
        ],
    )


@router.delete("/{job_id}", status_code=204)
def delete_job(
    request: Request,
    job: Job = Depends(get_owned_job),
    db: Session = Depends(get_db),
):
    request.app.state.storage.delete_prefix(job_key(job.user_id, job.id) + "/")
    db.delete(job)
    db.commit()
