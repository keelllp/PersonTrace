import numpy as np
import pytest

from app.pipeline.logic import (
    CropCandidate,
    Match,
    Tracklet,
    TrackletStore,
    crop_score,
    laplacian_sharpness,
    match_tracklets,
    merge_intervals,
)


def unit(seed):
    rng = np.random.default_rng(seed)
    v = rng.normal(size=512).astype(np.float32)
    return v / np.linalg.norm(v)


def near(v, eps=0.05):
    """A distinct vector with cosine similarity ≈ 1-eps to v."""
    w = v + eps * unit(hash(str(eps)) % 2**32)
    return (w / np.linalg.norm(w)).astype(np.float32)


class TestMergeIntervals:
    def test_empty(self):
        assert merge_intervals([], 1.5) == []

    def test_single_time_zero_length_interval(self):
        assert merge_intervals([3.0], 1.5) == [(3.0, 3.0)]

    def test_bridges_gaps_within_tolerance(self):
        times = [0.0, 0.5, 1.0, 2.4, 5.0, 5.5]
        assert merge_intervals(times, 1.5) == [(0.0, 2.4), (5.0, 5.5)]

    def test_unsorted_input(self):
        assert merge_intervals([5.0, 0.0, 0.5], 1.0) == [(0.0, 0.5), (5.0, 5.0)]


class TestCropScoring:
    def test_sharp_beats_blurry(self):
        rng = np.random.default_rng(0)
        sharp = rng.integers(0, 255, (64, 32, 3)).astype(np.uint8)
        blurry = np.full((64, 32, 3), 128, dtype=np.uint8)
        assert laplacian_sharpness(sharp) > laplacian_sharpness(blurry)
        assert crop_score(sharp, 64 * 32) > crop_score(blurry, 64 * 32)


class TestTrackletStore:
    def make_crop(self, sharp: bool):
        if sharp:
            return np.random.default_rng(1).integers(0, 255, (64, 32, 3)).astype(np.uint8)
        return np.full((64, 32, 3), 100, dtype=np.uint8)

    def test_keeps_only_top_k_crops_by_score(self):
        store = TrackletStore(max_crops=2)
        for i in range(5):
            store.add(7, float(i), self.make_crop(sharp=(i in (1, 3))), (0, 0, 32, 64))
        (t,) = store.tracklets()
        assert t.track_id == 7
        assert t.times == [0.0, 1.0, 2.0, 3.0, 4.0]
        assert len(t.crops) == 2
        assert {c.time_s for c in t.crops} == {1.0, 3.0}  # the sharp ones

    def test_boxes_recorded_with_times(self):
        store = TrackletStore(max_crops=3)
        store.add(1, 0.5, self.make_crop(True), (10, 20, 30, 80))
        (t,) = store.tracklets()
        assert t.boxes == [(0.5, (10, 20, 30, 80))]


class TestMatchTracklets:
    def kw(self):
        return dict(face_threshold=0.40, body_threshold=0.70, body_confidence_cap=0.75)

    def test_face_match_wins_and_reports_face_type(self):
        alice_face = unit(1)
        t = Tracklet(1, [0.0], [], [], face_emb=near(alice_face), body_emb=unit(9))
        result = match_tracklets([t], {"alice": [alice_face]}, {}, **self.kw())
        assert result[1].person_id == "alice"
        assert result[1].match_type == "face"
        assert result[1].confidence > 0.9

    def test_below_face_threshold_is_unmatched(self):
        t = Tracklet(1, [0.0], [], [], face_emb=unit(2), body_emb=None)
        assert match_tracklets([t], {"alice": [unit(1)]}, {}, **self.kw()) == {}

    def test_bootstrap_enrolls_body_from_face_match(self):
        alice_face, alice_body = unit(1), unit(3)
        t_front = Tracklet(1, [0.0], [], [], face_emb=near(alice_face), body_emb=alice_body)
        t_back = Tracklet(2, [5.0], [], [], face_emb=None, body_emb=near(alice_body, 0.02))
        result = match_tracklets(
            [t_front, t_back], {"alice": [alice_face]}, {}, **self.kw()
        )
        assert result[2].person_id == "alice"
        assert result[2].match_type == "body"
        assert result[2].confidence <= 0.75  # capped

    def test_body_only_reference_gallery_matches(self):
        bob_body = unit(4)
        t = Tracklet(1, [0.0], [], [], face_emb=None, body_emb=near(bob_body, 0.02))
        result = match_tracklets([t], {}, {"bob": [bob_body]}, **self.kw())
        assert result[1].person_id == "bob"
        assert result[1].match_type == "body"

    def test_dissimilar_body_stays_unmatched(self):
        t = Tracklet(1, [0.0], [], [], face_emb=None, body_emb=unit(5))
        assert match_tracklets([t], {}, {"bob": [unit(4)]}, **self.kw()) == {}

    def test_face_beats_closer_body_match(self):
        alice_face = unit(1)
        bob_body = unit(4)
        t = Tracklet(
            1, [0.0], [], [], face_emb=near(alice_face), body_emb=near(bob_body, 0.01)
        )
        result = match_tracklets(
            [t], {"alice": [alice_face]}, {"bob": [bob_body]}, **self.kw()
        )
        assert result[1].person_id == "alice"
        assert result[1].match_type == "face"
