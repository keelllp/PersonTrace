"""Six-stage pipeline orchestrator. All external effects (storage, DB,
models) are injectable; defaults wire the real thing."""
import logging
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import cv2
import numpy as np

from ..jobs import JobCancelled
from ..models import Job, Person, Sighting
from ..storage import job_key
from . import config
from .logic import TrackletStore, match_tracklets, merge_intervals
from .video import (
    VideoProbeError,
    annotate,
    downscale,
    extract_frame_at,
    iter_frames,
    probe_video,
    save_jpeg_pair,
)

logger = logging.getLogger(__name__)

STAGE_WINDOWS = {
    "probe": (0, 5),
    "gallery": (5, 15),
    "detect": (15, 70),
    "embed": (70, 85),
    "match": (85, 88),
    "render": (88, 100),
}


@dataclass
class PipelineModels:
    detector: Any  # .track(frame), .detect(image)
    face: Any      # .best_embedding(bgr), .faces(bgr)
    body: Any      # .embed_crop(crop)


def default_models() -> PipelineModels:
    from .ml import PersonDetector, get_body_embedder, get_face_engine

    return PipelineModels(
        detector=PersonDetector(), face=get_face_engine(), body=get_body_embedder()
    )


def _mean_normed(vectors: list[np.ndarray]) -> np.ndarray | None:
    if not vectors:
        return None
    mean = np.mean(np.stack(vectors), axis=0)
    norm = float(np.linalg.norm(mean))
    return (mean / norm).astype(np.float32) if norm > 0 else None


def run_pipeline(
    job_id: str,
    cancel_check: Callable[[], bool],
    *,
    storage=None,
    session_factory=None,
    models: PipelineModels | None = None,
) -> None:
    if storage is None:
        from ..storage import Storage

        storage = Storage.from_settings()
    if session_factory is None:
        from ..db import SessionLocal

        session_factory = SessionLocal
    if models is None:
        models = default_models()

    db = session_factory()
    workdir = Path(tempfile.mkdtemp(prefix=f"persontrace_{job_id}_"))
    try:
        job = db.get(Job, job_id)
        if job is None:
            return
        persons = list(db.query(Person).filter_by(job_id=job_id))

        def progress(stage: str, fraction: float) -> None:
            if cancel_check():
                raise JobCancelled()
            lo, hi = STAGE_WINDOWS[stage]
            job.stage = stage
            job.progress_pct = round(lo + (hi - lo) * min(max(fraction, 0.0), 1.0), 1)
            db.commit()

        # ---- Stage 1: probe ----------------------------------------------
        progress("probe", 0.0)
        video_path = workdir / "video"
        try:
            with open(video_path, "wb") as f:
                for chunk in storage.stream(job.video_key):
                    f.write(chunk)
        except KeyError as exc:
            raise RuntimeError("Video file is missing from storage") from exc
        info = probe_video(video_path)
        job.duration_s, job.fps = info.duration_s, info.fps
        job.width, job.height = info.width, info.height
        progress("probe", 1.0)

        # ---- Stage 2: reference galleries --------------------------------
        face_galleries: dict[str, list[np.ndarray]] = {}
        body_galleries: dict[str, list[np.ndarray]] = {}
        for i, person in enumerate(persons):
            faces, bodies = [], []
            for key in person.photo_keys:
                array = np.frombuffer(storage.get_bytes(key), dtype=np.uint8)
                photo = cv2.imdecode(array, cv2.IMREAD_COLOR)
                if photo is None:
                    continue
                emb = models.face.best_embedding(photo)
                if emb is not None:
                    faces.append(emb)
                for box, _conf in models.detector.detect(photo)[:1]:
                    x1, y1, x2, y2 = (int(v) for v in box)
                    crop = photo[max(y1, 0):y2, max(x1, 0):x2]
                    if crop.size:
                        bodies.append(models.body.embed_crop(crop))
            person.face_gallery_ok = bool(faces)
            person.body_gallery_ok = bool(bodies)
            if faces:
                face_galleries[person.id] = faces
            if bodies:
                body_galleries[person.id] = bodies
            progress("gallery", (i + 1) / max(len(persons), 1))

        # ---- Stage 3: detect & track --------------------------------------
        stride = max(1, round(info.fps / config.SAMPLE_FPS))
        store = TrackletStore(config.CROPS_PER_TRACKLET)
        sampled_total = max(info.frame_count // stride, 1)
        frames = iter_frames(video_path, stride)
        try:
            for n, (index, time_s, frame) in enumerate(frames):
                small, scale = downscale(frame, config.DOWNSCALE_WIDTH)
                for track_id, box, _conf in models.detector.track(small):
                    x1, y1, x2, y2 = (int(v) for v in box)
                    crop = small[max(y1, 0):y2, max(x1, 0):x2]
                    if not crop.size:
                        continue
                    original_box = tuple(v * scale for v in box)
                    # crop is downscaled while the box is in original coords; the
                    # resulting score mixes scales but the scale factor is constant
                    # per video, so crop RANKING (all we use) is unaffected.
                    store.add(track_id, time_s, crop, original_box)
                if n % 10 == 0:
                    progress("detect", n / sampled_total)
        finally:
            frames.close()
        progress("detect", 1.0)

        # ---- Stage 4: embed tracklets --------------------------------------
        tracklets = [
            t for t in store.tracklets() if len(t.times) >= config.MIN_TRACKLET_FRAMES
        ]
        for i, tracklet in enumerate(tracklets):
            face_vecs = [
                emb
                for c in tracklet.crops
                if (emb := models.face.best_embedding(c.crop)) is not None
            ]
            tracklet.face_emb = _mean_normed(face_vecs)
            tracklet.body_emb = _mean_normed(
                [models.body.embed_crop(c.crop) for c in tracklet.crops]
            )
            progress("embed", (i + 1) / max(len(tracklets), 1))

        # ---- Stage 5: match -------------------------------------------------
        matches = match_tracklets(
            tracklets,
            face_galleries,
            body_galleries,
            face_threshold=config.FACE_MATCH_THRESHOLD,
            body_threshold=config.BODY_MATCH_THRESHOLD,
            body_confidence_cap=config.BODY_CONFIDENCE_CAP,
        )
        progress("match", 1.0)

        # ---- Stage 6: render ------------------------------------------------
        pending_sightings: list[Sighting] = []
        by_person: dict[str, list] = {}
        tracklet_by_id = {t.track_id: t for t in tracklets}
        for track_id, match in matches.items():
            by_person.setdefault(match.person_id, []).append(
                (tracklet_by_id[track_id], match)
            )

        for pi, (person_id, matched) in enumerate(by_person.items()):
            person = next(p for p in persons if p.id == person_id)
            all_times = [t for tracklet, _ in matched for t in tracklet.times]
            intervals = merge_intervals(all_times, config.GAP_MERGE_SECONDS)
            for si, (start_s, end_s) in enumerate(intervals):
                contributors = [
                    (tracklet, m)
                    for tracklet, m in matched
                    if any(start_s <= t <= end_s for t in tracklet.times)
                ]
                best_tracklet, best_match = max(
                    contributors,
                    key=lambda tm: (tm[1].match_type == "face", tm[1].confidence),
                )
                candidates = [
                    c for c in best_tracklet.crops if start_s <= c.time_s <= end_s
                ] or best_tracklet.crops
                shot = max(candidates, key=lambda c: c.score)

                frame = extract_frame_at(video_path, shot.time_s)
                if frame is None:
                    continue
                label = f"{person.name} · {best_match.confidence:.0%}"
                annotated = annotate(frame, shot.box, label, person.color)
                shot_path = workdir / f"{person_id}_{si:03d}.jpg"
                thumb_path = workdir / f"{person_id}_{si:03d}_thumb.jpg"
                save_jpeg_pair(annotated, shot_path, thumb_path)

                screenshot_key = job_key(
                    job.user_id, job.id, f"screenshots/{person_id}_{si:03d}.jpg"
                )
                thumbnail_key = job_key(
                    job.user_id, job.id, f"screenshots/{person_id}_{si:03d}_thumb.jpg"
                )
                storage.put_bytes(screenshot_key, shot_path.read_bytes(), "image/jpeg")
                storage.put_bytes(thumbnail_key, thumb_path.read_bytes(), "image/jpeg")

                x1, y1, x2, y2 = shot.box
                pending_sightings.append(
                    Sighting(
                        person_id=person_id,
                        start_s=round(start_s, 2),
                        end_s=round(end_s, 2),
                        confidence=round(best_match.confidence, 4),
                        match_type=best_match.match_type,
                        screenshot_key=screenshot_key,
                        thumbnail_key=thumbnail_key,
                        box={
                            "x": round(x1, 1),
                            "y": round(y1, 1),
                            "w": round(x2 - x1, 1),
                            "h": round(y2 - y1, 1),
                            "frame_s": round(shot.time_s, 2),
                        },
                    )
                )
            progress("render", (pi + 1) / max(len(by_person), 1))
        db.add_all(pending_sightings)
        job.stage = "render"
        db.commit()
    except VideoProbeError as exc:
        db.rollback()
        raise RuntimeError(str(exc)) from exc
    finally:
        db.close()
        shutil.rmtree(workdir, ignore_errors=True)
