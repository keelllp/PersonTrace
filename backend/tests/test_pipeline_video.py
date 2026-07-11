import cv2
import numpy as np
import pytest

from app.pipeline.video import (
    VideoProbeError,
    annotate,
    downscale,
    extract_frame_at,
    iter_frames,
    probe_video,
    save_jpeg_pair,
)

from .video_utils import make_test_video


@pytest.fixture(scope="module")
def video_path(tmp_path_factory):
    return make_test_video(tmp_path_factory.mktemp("vid") / "clip.mp4")


def test_probe_reads_metadata(video_path):
    info = probe_video(video_path)
    assert info.width == 320 and info.height == 240
    assert 23 <= info.fps <= 25
    assert 1.8 <= info.duration_s <= 2.2
    assert info.frame_count == 48


def test_probe_rejects_garbage(tmp_path):
    bad = tmp_path / "bad.mp4"
    bad.write_bytes(b"this is not a video")
    with pytest.raises(VideoProbeError):
        probe_video(bad)


def test_iter_frames_stride(video_path):
    frames = list(iter_frames(video_path, stride=6))
    assert len(frames) == 8
    indices = [i for i, _, _ in frames]
    assert indices == [0, 6, 12, 18, 24, 30, 36, 42]
    times = [t for _, t, _ in frames]
    assert times == pytest.approx([i / 24 for i in indices], abs=0.01)
    assert frames[0][2].shape == (240, 320, 3)


def test_downscale_caps_width_and_reports_inverse_scale():
    frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    small, scale = downscale(frame, 960)
    assert small.shape[1] == 960
    assert scale == pytest.approx(2.0)
    untouched, scale1 = downscale(np.zeros((240, 320, 3), dtype=np.uint8), 960)
    assert untouched.shape[1] == 320 and scale1 == 1.0


def test_extract_frame_at(video_path):
    frame = extract_frame_at(video_path, 1.0)
    assert frame is not None and frame.shape == (240, 320, 3)
    assert extract_frame_at(video_path, 99.0) is None


def test_annotate_draws_box_and_label():
    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    out = annotate(frame, (50, 50, 150, 200), "Alice · 87%", "#e05252")
    assert out is not frame
    assert int(out.sum()) > 0
    assert int(frame.sum()) == 0  # original untouched


def test_save_jpeg_pair(tmp_path):
    frame = np.random.default_rng(0).integers(0, 255, (480, 640, 3)).astype(np.uint8)
    shot, thumb = tmp_path / "s.jpg", tmp_path / "t.jpg"
    save_jpeg_pair(frame, shot, thumb, thumb_width=320)
    assert cv2.imread(str(shot)).shape == (480, 640, 3)
    assert cv2.imread(str(thumb)).shape[1] == 320
