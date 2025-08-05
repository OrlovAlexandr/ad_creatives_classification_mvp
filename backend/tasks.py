from celery import Celery
from config import REDIS_URL
from database import SessionLocal
import database
from PIL import Image
import os
import datetime

celery = Celery("tasks", broker=REDIS_URL, backend=REDIS_URL)


# Имитация ML-обработки
@celery.task(bind=True, max_retries=3)
def process_creative(self, creative_id: int):
    db = SessionLocal()
    try:
        creative = db.query(database.Creative).filter(database.Creative.creative_id == creative_id).first()
        if not creative:
            raise Exception("Креатив не найден")

        # Имитация обработки
        img_path = creative.file_path
        width, height = creative.image_width, creative.image_height

        # Открываем изображение, чтобы получить размеры
        if os.path.exists(img_path):
            with Image.open(img_path) as img:
                width, height = img.size

        # mock-данные
        dominant_colors = [
            {"hex": "#FF0000", "rgb": [255, 0, 0], "percent": 40.0},
            {"hex": "#000000", "rgb": [0, 0, 0], "percent": 35.0},
            {"hex": "#FFFFFF", "rgb": [255, 255, 255], "percent": 25.0},
        ]

        ocr_text = "КОМПЛЕКТ ФУТБОЛОК. ПРОИЗВОДСТВО РОССИЯ. РАЗМЕРЫ 104-164"
        ocr_blocks = [
            {"text": "КОМПЛЕКТ ФУТБОЛОК", "bbox": [0.02, 0.02, 0.5, 0.14], "confidence": 0.98},
            {"text": "ПРОИЗВОДСТВО РОССИЯ", "bbox": [0.02, 0.17, 0.36, 0.24], "confidence": 0.99},
            {"text": "РАЗМЕРЫ 104-164", "bbox": [0.02, 0.27, 0.3, 0.36], "confidence": 0.94},
        ]

        text_topics = [
            {"topic": "Одежда", "confidence": 0.85},
            {"topic": "Футболки", "confidence": 0.96},
            {"topic": "Товары", "confidence": 0.7},
        ]

        detected_objects = [
            {"class": "t-shirt", "bbox": [0.3, 0.25, 0.7, 0.58], "confidence": 0.92},
            {"class": "t-shirt", "bbox": [0.58, 0.2, 0.91, 0.5], "confidence": 0.72},
            {"class": "jeans", "bbox": [0.18, 0.58, 0.68, 0.9], "confidence": 0.93},
            {"class": "jeans", "bbox": [0.6, 0.5, 0.94, 0.86], "confidence": 0.81},
            {"class": "human", "bbox": [0.16, 0.1, 0.72, 0.97], "confidence": 0.88},
            {"class": "human", "bbox": [0.52, 0.04, 0.95, 0.9], "confidence": 0.78},
        ]

        main_topic = "Футболки"

        # Сохраняем в БД
        analysis = database.CreativeAnalysis(
            creative_id=creative_id,
            dominant_colors=dominant_colors,
            ocr_text=ocr_text,
            ocr_blocks=ocr_blocks,
            text_topics=text_topics,
            detected_objects=detected_objects,
            main_topic=main_topic,
            analysis_timestamp=datetime.datetime.utcnow(),
            analysis_status="SUCCESS"
        )
        db.add(analysis)
        db.commit()

        return {"status": "success", "creative_id": creative_id}

    except Exception as exc:
        db.rollback()
        analysis = db.query(database.CreativeAnalysis).filter(
            database.CreativeAnalysis.creative_id == creative_id).first()
        if analysis:
            analysis.analysis_status = "ERROR"
            analysis.error_message = str(exc)
            db.commit()
        raise self.retry(exc=exc, countdown=30)  # Повторить через 30 сек
    finally:
        db.close()
