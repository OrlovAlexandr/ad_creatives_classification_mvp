import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
REDIS_URL = os.getenv("REDIS_URL")
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
MINIO_SECURE = os.getenv("MINIO_SECURE").lower() == "true"
MINIO_BUCKET = os.getenv("MINIO_BUCKET")
if MINIO_SECURE:
    MINIO_BASE_URL = f"https://{MINIO_ENDPOINT}"
else:
    MINIO_BASE_URL = f"http://{MINIO_ENDPOINT}"

MINIO_PUBLIC_URL = os.getenv("MINIO_PUBLIC_URL")
if not MINIO_PUBLIC_URL:
    MINIO_PUBLIC_URL = MINIO_BASE_URL 

TOPICS = ['tableware', 'ties', 'bags', 'cups', 'clocks']

TOPIC_TRANSLATIONS = {
    'tableware': 'Столовые приборы',
    'ties': 'Галстуки',
    'bags': 'Сумки',
    'cups': 'Чашки',
    'clocks': 'Часы'
}
