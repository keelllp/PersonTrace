"""Pure pipeline logic: crop scoring, tracklet bookkeeping, interval math,
hierarchical face-then-body matching. No ML imports — fully unit-testable."""
import heapq
import itertools
from dataclasses import dataclass, field

import cv2
import numpy as np


def laplacian_sharpness(bgr: np.ndarray) -> float:
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def crop_score(bgr: np.ndarray, box_area: float) -> float:
    return box_area * (1.0 + laplacian_sharpness(bgr))


@dataclass
class CropCandidate:
    time_s: float
    crop: np.ndarray
    box: tuple[float, float, float, float]  # xyxy, original video coords
    score: float


@dataclass
class Tracklet:
    track_id: int
    times: list[float]
    boxes: list[tuple[float, tuple[float, float, float, float]]]
    crops: list[CropCandidate]
    face_emb: np.ndarray | None = None
    body_emb: np.ndarray | None = None


class TrackletStore:
    """Accumulates detections per track id, keeping only the top-K crops."""

    def __init__(self, max_crops: int):
        self._max_crops = max_crops
        self._tracklets: dict[int, Tracklet] = {}
        self._heaps: dict[int, list] = {}
        self._counter = itertools.count()

    def add(
        self,
        track_id: int,
        time_s: float,
        crop: np.ndarray,
        box: tuple[float, float, float, float],
    ) -> None:
        t = self._tracklets.get(track_id)
        if t is None:
            t = Tracklet(track_id, [], [], [])
            self._tracklets[track_id] = t
            self._heaps[track_id] = []
        t.times.append(time_s)
        t.boxes.append((time_s, box))

        area = max((box[2] - box[0]) * (box[3] - box[1]), 1.0)
        candidate = CropCandidate(time_s, crop, box, crop_score(crop, area))
        heap = self._heaps[track_id]
        entry = (candidate.score, next(self._counter), candidate)
        if len(heap) < self._max_crops:
            heapq.heappush(heap, entry)
        else:
            heapq.heappushpop(heap, entry)
        t.crops = [e[2] for e in heap]

    def tracklets(self) -> list[Tracklet]:
        return list(self._tracklets.values())


@dataclass
class Match:
    person_id: str
    confidence: float
    match_type: str  # "face" | "body"


def _best_gallery_hit(
    vec: np.ndarray, galleries: dict[str, list[np.ndarray]]
) -> tuple[str, float] | None:
    best: tuple[str, float] | None = None
    for person_id, vectors in galleries.items():
        for g in vectors:
            score = float(np.dot(vec, g))
            if best is None or score > best[1]:
                best = (person_id, score)
    return best


def match_tracklets(
    tracklets: list[Tracklet],
    face_galleries: dict[str, list[np.ndarray]],
    body_galleries: dict[str, list[np.ndarray]],
    *,
    face_threshold: float,
    body_threshold: float,
    body_confidence_cap: float,
) -> dict[int, Match]:
    session_body: dict[str, list[np.ndarray]] = {
        pid: list(vectors) for pid, vectors in body_galleries.items()
    }
    results: dict[int, Match] = {}

    # Face pass, strongest first so confident matches enroll their body
    # embeddings before weaker ones are considered.
    face_hits = []
    for t in tracklets:
        if t.face_emb is None:
            continue
        hit = _best_gallery_hit(t.face_emb, face_galleries)
        if hit is not None and hit[1] >= face_threshold:
            face_hits.append((hit[1], t, hit[0]))
    for score, t, person_id in sorted(face_hits, key=lambda x: -x[0]):
        results[t.track_id] = Match(person_id, min(score, 1.0), "face")
        if t.body_emb is not None:
            session_body.setdefault(person_id, []).append(t.body_emb)

    # Body fallback for everyone the face pass didn't claim.
    for t in tracklets:
        if t.track_id in results or t.body_emb is None:
            continue
        hit = _best_gallery_hit(t.body_emb, session_body)
        if hit is not None and hit[1] >= body_threshold:
            results[t.track_id] = Match(
                hit[0], min(hit[1], body_confidence_cap), "body"
            )
    return results


def merge_intervals(times: list[float], max_gap: float) -> list[tuple[float, float]]:
    if not times:
        return []
    ts = sorted(times)
    out: list[list[float]] = [[ts[0], ts[0]]]
    for t in ts[1:]:
        if t - out[-1][1] <= max_gap:
            out[-1][1] = t
        else:
            out.append([t, t])
    return [(a, b) for a, b in out]
