"""All pipeline tunables. Change values here, nowhere else."""

DOWNSCALE_WIDTH = 960          # inference frame width cap (px)
SAMPLE_FPS = 4.0               # effective detection sampling rate
CROPS_PER_TRACKLET = 5         # best crops embedded per tracklet
MIN_TRACKLET_FRAMES = 3        # shorter tracklets are noise, dropped
FACE_MATCH_THRESHOLD = 0.40    # cosine, buffalo_l embeddings
BODY_MATCH_THRESHOLD = 0.70    # cosine, OSNet embeddings (they run high)
BODY_CONFIDENCE_CAP = 0.75     # body matches always rank below face matches
GAP_MERGE_SECONDS = 1.5        # bridge gaps up to this when merging intervals
MIN_FACE_DET_SCORE = 0.5       # ignore weaker face detections
MIN_PERSON_DET_CONF = 0.35     # ignore weaker person detections

DETECTOR_WEIGHTS = "yolo11n.pt"
FACE_PACK = "buffalo_l"
REID_WEIGHTS = "osnet_x1_0_msmt17.pt"
