# PersonTrace

Find people in videos. Upload a video and reference photos of one or more people — PersonTrace analyzes the video and shows exactly when and where each person appears: time intervals, annotated screenshots with labeled bounding boxes, and confidence scores, all on a seekable timeline.

## How it works

- **Detection & tracking:** YOLO11n person detection + ByteTrack tracking group raw detections into per-person tracklets.
- **Hybrid identification:** InsightFace face embeddings (primary, high accuracy) with OSNet body re-identification as a fallback for turned-away or distant appearances. Face matches bootstrap the body gallery.
- **CPU-only:** all models run on CPU via ONNX Runtime — no GPU required.

## Stack

- **Backend:** FastAPI (Python 3.11+), SQLAlchemy + PostgreSQL, SeaweedFS (S3 API) for blob storage
- **Frontend:** Vite + React + TypeScript + Tailwind CSS
- **Infra:** docker-compose (PostgreSQL + SeaweedFS)

## Status

Under active development.
