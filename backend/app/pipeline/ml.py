"""Model wrappers. Heavy libraries are imported lazily inside constructors so
importing app modules never loads torch/onnxruntime. FaceEngine and
BodyEmbedder are process-wide singletons (expensive to load); PersonDetector
is created fresh per video because ByteTrack state is per-stream."""
import numpy as np

from .config import (
    DETECTOR_WEIGHTS,
    FACE_PACK,
    MIN_FACE_DET_SCORE,
    MIN_PERSON_DET_CONF,
    REID_WEIGHTS,
)


class PersonDetector:
    def __init__(self):
        from ultralytics import YOLO

        self._model = YOLO(DETECTOR_WEIGHTS)

    def track(self, frame_bgr):
        result = self._model.track(
            frame_bgr,
            imgsz=640,
            classes=[0],
            conf=MIN_PERSON_DET_CONF,
            persist=True,
            verbose=False,
            tracker="bytetrack.yaml",
        )[0]
        out = []
        boxes = result.boxes
        if boxes is None or boxes.id is None:
            return out
        for xyxy, track_id, conf in zip(
            boxes.xyxy.tolist(), boxes.id.int().tolist(), boxes.conf.tolist()
        ):
            out.append((int(track_id), tuple(float(v) for v in xyxy), float(conf)))
        return out

    def detect(self, image_bgr):
        result = self._model.predict(
            image_bgr, imgsz=640, classes=[0], conf=MIN_PERSON_DET_CONF, verbose=False
        )[0]
        out = []
        if result.boxes is None:
            return out
        for xyxy, conf in zip(result.boxes.xyxy.tolist(), result.boxes.conf.tolist()):
            out.append((tuple(float(v) for v in xyxy), float(conf)))
        return out


class FaceEngine:
    def __init__(self):
        from insightface.app import FaceAnalysis

        self._app = FaceAnalysis(
            name=FACE_PACK,
            providers=["CPUExecutionProvider"],
            allowed_modules=["detection", "recognition"],
        )
        self._app.prepare(ctx_id=-1, det_size=(640, 640))

    def faces(self, bgr):
        found = self._app.get(bgr)
        out = []
        for f in found:
            if f.det_score < MIN_FACE_DET_SCORE:
                continue
            emb = f.normed_embedding.astype(np.float32)
            out.append((tuple(float(v) for v in f.bbox), float(f.det_score), emb))
        return out

    def best_embedding(self, bgr):
        found = self.faces(bgr)
        if not found:
            return None
        largest = max(
            found, key=lambda x: (x[0][2] - x[0][0]) * (x[0][3] - x[0][1])
        )
        return largest[2]

    def validate_photo_bytes(self, image_bytes: bytes) -> bool:
        import cv2

        array = np.frombuffer(image_bytes, dtype=np.uint8)
        bgr = cv2.imdecode(array, cv2.IMREAD_COLOR)
        if bgr is None:
            return False
        return self.best_embedding(bgr) is not None


class BodyEmbedder:
    def __init__(self):
        from boxmot.reid.core.reid import ReID

        self._reid = ReID(REID_WEIGHTS, device="cpu")

    def embed_crop(self, crop_bgr) -> np.ndarray:
        h, w = crop_bgr.shape[:2]
        boxes = np.array([[0.0, 0.0, float(w), float(h)]])
        features = np.asarray(self._reid.model.get_features(boxes, crop_bgr))
        vec = features[0].astype(np.float32)
        norm = float(np.linalg.norm(vec))
        return vec / norm if norm > 0 else vec


_face_engine: FaceEngine | None = None
_body_embedder: BodyEmbedder | None = None


def get_face_engine() -> FaceEngine:
    global _face_engine
    if _face_engine is None:
        _face_engine = FaceEngine()
    return _face_engine


def get_body_embedder() -> BodyEmbedder:
    global _body_embedder
    if _body_embedder is None:
        _body_embedder = BodyEmbedder()
    return _body_embedder
