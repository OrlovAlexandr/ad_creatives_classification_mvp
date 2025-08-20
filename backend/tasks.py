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

        time.sleep(random.uniform(0.5, 3.0))
        num_objects = random.randint(2, 6)
        detected_objects = []
        for _ in range(num_objects):
            cls = random.choice(COCO_CLASSES)
            confidence = round(random.uniform(0.5, 0.99), 2)
            x1 = random.uniform(0.05, 0.7) * w
            y1 = random.uniform(0.05, 0.7) * h
            x2 = x1 + random.uniform(0.1, 0.3) * w
            y2 = y1 + random.uniform(0.1, 0.3) * h
            detected_objects.append({
                "class": cls,
                "bbox": [x1/w, y1/h, x2/w, y2/h],
                "confidence": confidence
            })
        analysis.detected_objects = detected_objects
        analysis.detection_status = "SUCCESS"

        analysis.detection_сompleted_at = datetime.utcnow()
        analysis.detection_duration = (
            analysis.detection_сompleted_at - analysis.detection_started_at
            ).total_seconds()


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
