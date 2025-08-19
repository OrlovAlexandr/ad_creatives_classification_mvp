from celery import Celery
from config import (
    REDIS_URL, MINIO_PUBLIC_URL, MINIO_BUCKET, MINIO_ACCESS_KEY, 
    MINIO_SECRET_KEY, MINIO_SECURE, MINIO_ENDPOINT,
    TOPICS, TOPIC_TRANSLATIONS,
    )
from database import SessionLocal
import database
from minio_client import minio_client
from PIL import Image
import numpy as np
from collections import Counter
import os
from datetime import datetime
import random
import time
from color_utils import get_top_colors, classify_colors_by_palette
from ultralytics import YOLO  
from config import YOLO_CONFIDENCE_THRESHOLD
import torch  
# Загружаем модель один раз при старте
from minio import Minio
import os
from ultralytics import YOLO
import torch
import logging
import cv2

logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "models")
MINIO_SECURE = os.getenv("MINIO_SECURE", "False").lower() == "true"

minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=MINIO_SECURE
)


local_weight_path = "/backend/models/yolo/yolo8m.pt"

# Загружаем, если еще нет
if not os.path.exists(local_weight_path):
    minio_client.fget_object(MINIO_BUCKET, "yolo8m.pt", local_weight_path)

device = "cuda" if torch.cuda.is_available() else "cpu"
yolo_model = YOLO(local_weight_path)
yolo_model.to(device)



TOPIC_TEXTS = {
    'tableware': 'НАБОР ИЗ НЕРЖАВЕЙКИ. ПОСУДА ДЛЯ КУХНИ. 10 ПРЕДМЕТОВ',
    'ties': 'ШЕЛКОВЫЙ ГАЛСТУК. КЛАССИКА. ПОДАРОК МУЖЧИНЕ',
    'bags': 'ЛЕДИ-СУМКА 2025. КОЖА, ЗАСТЕЖКА, ВМЕСТИТЕЛЬНО',
    'cups': 'ФИРМЕННАЯ КЕРАМИКА. ПОДАРОК К ПРАЗДНИКУ. НЕ ТЕРЯЕТ ЦВЕТ',
    'clocks': 'SMART WATCH 8 СЕРИИ. ДОПУСК УВЕДОМЛЕНИЙ. МОЩНАЯ БАТАРЕЯ'
}

COCO_CLASSES = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat",
    "traffic light", "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat",
    "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe", "backpack",
    "umbrella", "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard", "sports ball",
    "kite", "baseball bat", "baseball glove", "skateboard", "surfboard", "tennis racket",
    "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana", "apple",
    "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake",
    "chair", "couch", "potted plant", "bed", "dining table", "toilet", "tv", "laptop",
    "mouse", "remote", "keyboard", "cell phone", "microwave", "oven", "toaster", "sink",
    "refrigerator", "book", "clock", "vase", "scissors", "teddy bear", "hair drier", "toothbrush"
]

celery = Celery("tasks", broker=REDIS_URL, backend=REDIS_URL)


# Имитация ML-обработки
@celery.task(bind=True, max_retries=3)
def process_creative(self, creative_id: str):
    db = SessionLocal()
    temp_local_path = None
    try:
        creative = db.query(database.Creative).filter(
            database.Creative.creative_id == creative_id
            ).first()
        if not creative:
            raise Exception("Креатив не найден")
        
        analysis = db.query(database.CreativeAnalysis).filter(
            database.CreativeAnalysis.creative_id == creative_id).first()

        if not analysis:
            analysis = database.CreativeAnalysis(creative_id=creative_id)
            db.add(analysis)

        analysis.overall_status = "PROCESSING"
        db.commit()

        # Скачиваем изображение из MinIO в локальную папку на период обработки
        try:
            object_name = f"{creative_id}.{creative.file_format}"
            temp_local_path = f"/tmp/{creative_id}.{creative.file_format}"

            response = minio_client.get_object(MINIO_BUCKET, object_name)
            with open(temp_local_path, "wb") as f:
                f.write(response.read())

            if not os.path.exists(temp_local_path):
                raise Exception("Файл не был сохранён локально")

        except Exception as e:
            logger.error(f"Ошибка загрузки изображения из MinIO для {creative_id}: {e}")
            analysis.overall_status = "ERROR"
            analysis.error_message = "Не удалось загрузить изображение"
            db.commit()
            return {"status": "error", "creative_id": creative_id}

        # Получаем размеры изображения
        try:
            with Image.open(temp_local_path) as img:
                width, height = img.size
        except Exception as e:
            logger.error(f"Ошибка чтения изображения {temp_local_path}: {e}")
            analysis.overall_status = "ERROR"
            analysis.error_message = "Некорректное изображение"
            db.commit()
            return {"status": "error", "creative_id": creative_id}


        # 1 - OCR
        analysis.ocr_status = "PROCESSING"
        analysis.ocr_started_at = datetime.utcnow()        
        db.commit()
        
        time.sleep(random.uniform(0.5, 3.0))
        topic = random.choice(TOPICS)
        full_text = TOPIC_TEXTS[topic]
        words = full_text.split(". ")
        blocks = []
        h, w = creative.image_height, creative.image_width
        for word in words:
            confidence = round(random.uniform(0.7, 0.99), 2)
            x1 = random.uniform(0.02, 0.1) * w
            y1 = random.uniform(0.02, 0.8) * h
            x2 = x1 + random.uniform(0.3, 0.7) * w
            y2 = y1 + random.uniform(0.05, 0.15) * h
            blocks.append({
                "text": word,
                "bbox": [x1/w, y1/h, x2/w, y2/h],
                "confidence": confidence
            })
        analysis.ocr_text = full_text
        analysis.ocr_blocks = blocks
        analysis.ocr_status = "SUCCESS"

        analysis.ocr_сompleted_at = datetime.utcnow()
        analysis.ocr_duration = (
            analysis.ocr_сompleted_at - analysis.ocr_started_at
            ).total_seconds()
        
        # 2 - Детекция объектов
        analysis.detection_status = "PROCESSING"
        analysis.detection_started_at = datetime.utcnow()
        db.commit()

        try:
        # Загружаем изображение из файла и преобразуем в numpy
            im_pil = Image.open(temp_local_path).convert("RGB")
            img_array = cv2.cvtColor(np.array(im_pil), cv2.COLOR_RGB2BGR)

            # Прогоняем через YOLO
            results = yolo_model.predict(
                source=img_array,
                batch=1,
                conf=YOLO_CONFIDENCE_THRESHOLD,
                device=device
            )[0]

            # Получаем боксы, классы и уверенность
            bboxes = results.boxes.xyxy.cpu().numpy()
            labels = results.boxes.cls.cpu().numpy()
            confidences = results.boxes.conf.cpu().numpy()

            detected_objects = []
            h, w = im_pil.size[1], im_pil.size[0]
            for box, label, conf in zip(bboxes, labels, confidences):
                x1, y1, x2, y2 = box
                detected_objects.append({
                    "class": COCO_CLASSES[int(label)],
                    "bbox": [x1/w, y1/h, x2/w, y2/h],
                    "confidence": float(conf)
                })

            analysis.detected_objects = detected_objects
            analysis.detection_status = "SUCCESS"

        except Exception as e:
            logger.error(f"Ошибка детекции YOLO для {creative_id}: {e}")
            analysis.detection_status = "ERROR"
        finally:
            analysis.detection_сompleted_at = datetime.utcnow()
            if analysis.detection_started_at:
                analysis.detection_duration = (
                    analysis.detection_сompleted_at - analysis.detection_started_at
                ).total_seconds()
            db.commit()
        # 3 - Классификация
        analysis.classification_status = "PROCESSING"
        analysis.classification_started_at = datetime.utcnow()
        db.commit()

        time.sleep(random.uniform(0.5, 3.0))
        topic_confidence = round(random.uniform(0.6, 0.95), 2)
        analysis.main_topic = topic
        analysis.topic_confidence = topic_confidence
        analysis.classification_status = "SUCCESS"

        analysis.classification_сompleted_at = datetime.utcnow()
        analysis.classification_duration = (
            analysis.classification_сompleted_at - analysis.classification_started_at
            ).total_seconds()

        # 4 - Анализ цветов
        analysis.color_analysis_status = "PROCESSING"
        analysis.color_analysis_started_at = datetime.utcnow()
        db.commit()

        try:
            colors_result = get_top_colors(temp_local_path, n_dominant=3, n_secondary=3, n_coeff=1)
            palette_result = classify_colors_by_palette(colors_result)

            analysis.dominant_colors = colors_result.get("dominant_colors", [])
            analysis.secondary_colors = colors_result.get("secondary_colors", [])
            analysis.palette_colors = palette_result

            analysis.color_analysis_status = "SUCCESS"
        except Exception as e:
            logger.error(f"Ошибка при анализе цветов для {creative_id}: {e}")
            analysis.color_analysis_status = "ERROR"
        finally:
            analysis.color_analysis_completed_at = datetime.utcnow()
            if analysis.color_analysis_started_at:
                analysis.color_analysis_duration = (
                    analysis.color_analysis_completed_at - analysis.color_analysis_started_at
                ).total_seconds()
            db.commit()

        
        # Завершение
        analysis.overall_status = "SUCCESS"
        analysis.analysis_timestamp = datetime.utcnow()
        analysis.total_duration = (
            analysis.analysis_timestamp - analysis.ocr_started_at
        ).total_seconds()
        db.commit()

        return {"status": "success", "creative_id": creative_id}

    except Exception as exc:
        db.rollback()
        analysis = db.query(database.CreativeAnalysis).filter(
            database.CreativeAnalysis.creative_id == creative_id).first()
        if analysis:
            analysis.overall_status = "ERROR"
            analysis.error_message = str(exc)
            db.commit()
        raise self.retry(exc=exc, countdown=30)
    finally:
        db.close()
        # Удаляем временный файл
        if temp_local_path and os.path.exists(temp_local_path):
            try:
                os.remove(temp_local_path)
            except Exception as e:
                logger.warning(f"Не удалось удалить временный файл {temp_local_path}: {e}")
