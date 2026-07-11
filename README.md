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

## Running PersonTrace

```bash
docker compose up -d                # Postgres + SeaweedFS (S3)
cd backend
uv venv .venv && source .venv/Scripts/activate   # Windows Git Bash
uv pip install -r requirements.lock
alembic upgrade head
uvicorn app.main:app --port 8000
```

### Frontend

Dev (hot reload): `cd frontend && npm install && npm run dev` → http://localhost:5173
(the dev server proxies `/api` to the backend on :8000).

Production: `cd frontend && npm run build`, then the backend at
http://localhost:8000 serves the built app directly.

On the first analysis job the pipeline downloads its models (~300 MB total,
cached afterwards): YOLO11n (~5 MB, to `backend/`), InsightFace buffalo_l
(~280 MB, to `~/.insightface/models/`), and OSNet x1_0 (~17 MB, into the
venv's `models/` dir via boxmot).

### Tests

```bash
python -m pytest            # fast suite + model contract tests
python -m pytest -m slow    # full-pipeline E2E with real models (~1-3 min)
```

### Model licensing

InsightFace's pretrained models (buffalo_l) are released for **non-commercial
research** use. This project uses them accordingly; a commercial deployment
would require a licensed or self-trained face recognition model.

## Status

All three phases complete: backend, ML pipeline, and frontend.
