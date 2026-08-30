from pathlib import Path

APP_NAME = "FaceSort"
DEFAULT_MODEL = "buffalo_l"
DEFAULT_DET_THRESH = 0.5
DEFAULT_DET_SIZE = (640, 640)

# Recognition tuning (cosine similarity in [-1, 1]; higher = more similar)
MATCH_THRESHOLD = 0.4        # face <-> reference person match (similarity)
CLUSTER_EPS = 0.6            # clustering connect threshold as COSINE DISTANCE (1 - sim)
CLUSTER_MIN_SAMPLES = 2      # min faces to form a cluster
UNKNOWN_LABEL = "Unknown"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}

INSIGHTFACE_ROOT = Path.home() / ".insightface"
