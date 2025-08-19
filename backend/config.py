# backend/config.py
import os
from dotenv import load_dotenv

load_dotenv()

# Database
DATABASE_URL = os.getenv("DATABASE_URL")
REDIS_URL = os.getenv("REDIS_URL")

# Uploads
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "/app/uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# MinIO Configuration
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "creatives")
MODELS_BUCKET = os.getenv("MODELS_BUCKET", "models")

if MINIO_SECURE:
    MINIO_BASE_URL = f"https://{MINIO_ENDPOINT}"
else:
    MINIO_BASE_URL = f"http://{MINIO_ENDPOINT}"

MINIO_PUBLIC_URL = os.getenv("MINIO_PUBLIC_URL", MINIO_BASE_URL)

# Models Configuration
MODELS_DIR = os.getenv("MODELS_DIR", "/app/models")
os.makedirs(MODELS_DIR, exist_ok=True)

# Model-specific paths
BERT_MODEL_PATH = os.path.join(MODELS_DIR, "bert")
EASYOCR_MODEL_PATH = os.path.join(MODELS_DIR, "easyocr") 
YOLO_MODEL_PATH = os.path.join(MODELS_DIR, "yolo", "yolov8n.pt")

# Ensure model directories exist
os.makedirs(os.path.dirname(BERT_MODEL_PATH), exist_ok=True)
os.makedirs(os.path.dirname(EASYOCR_MODEL_PATH), exist_ok=True)
os.makedirs(os.path.dirname(YOLO_MODEL_PATH), exist_ok=True)

# Model configuration for MinIO
MODEL_CONFIG = {
    "bert": {
        "bucket": MODELS_BUCKET,
        "remote_path": "bert/",
        "local_path": BERT_MODEL_PATH,
        "files": ["config.json", "pytorch_model.bin", "vocab.txt", "special_tokens_map.json"]
    },
    "easyocr": {
        "bucket": MODELS_BUCKET,
        "remote_path": "easyocr/",
        "local_path": EASYOCR_MODEL_PATH,
        "files": ["craft_mlt_25k.pth", "english_g2.pth", "russian.pth"]
    },
    "yolo": {
        "bucket": MODELS_BUCKET,
        "remote_path": "yolo/yolov8n.pt",
        "local_path": YOLO_MODEL_PATH
    }
}

# Topics for classification
TOPICS = ['tableware', 'ties', 'bags', 'cups', 'clocks']

TOPIC_TRANSLATIONS = {
    'tableware': 'Столовые приборы',
    'ties': 'Галстуки', 
    'bags': 'Сумки',
    'cups': 'Чашки',
    'clocks': 'Часы'
}

# Model parameters
YOLO_CONFIDENCE_THRESHOLD = 0.35
# OCR_CONFIDENCE_THRESHOLD = 0.7
# TOPIC_CONFIDENCE_THRESHOLD = 0.3

PROCESSING_TIMEOUT = 300 