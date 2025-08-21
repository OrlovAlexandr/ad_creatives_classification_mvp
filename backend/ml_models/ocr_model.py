from config import TOPICS, TOPIC_TEXTS
from datetime import datetime
import random
import time
import logging

logger = logging.getLogger(__name__)

def perform_ocr(
        creative_id: str, 
        creative,
        analysis, 
        db, 
        temp_local_path: str
        ):
    """Выполняет OCR."""
    logger.info(f"[{creative_id}] Начало OCR...")
    analysis.ocr_status = "PROCESSING"
    analysis.ocr_started_at = datetime.utcnow()
    db.commit() # Коммитим статус PROCESSING

    try:
        # Имитация OCR
        time.sleep(random.uniform(0.5, 3.0))
        topic = random.choice(TOPICS)
        full_text = TOPIC_TEXTS.get(topic, "Текст не найден")
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
        analysis.ocr_completed_at = datetime.utcnow()
        analysis.ocr_duration = (
            analysis.ocr_completed_at - analysis.ocr_started_at
            ).total_seconds()
        db.commit()
        logger.info(f"[{creative_id}] OCR завершен успешно.")
    except Exception as e:
        logger.error(f"[{creative_id}] Ошибка OCR: {e}")
        analysis.ocr_status = "ERROR"
        analysis.ocr_completed_at = datetime.utcnow()
        analysis.ocr_duration = (
            analysis.ocr_completed_at - analysis.ocr_started_at
            ).total_seconds()
        db.commit()
        raise