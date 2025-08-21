from datetime import datetime
import random
import time

from config import COCO_CLASSES
import logging

logger = logging.getLogger(__name__)

def perform_detection(
        creative_id: str, 
        creative,
        analysis, 
        db, 
        temp_local_path: str, 
        ):
    """Выполняет детекцию."""
    logger.info(f"[{creative_id}] Начало детекции...")
    analysis.detection_status = "PROCESSING"
    analysis.detection_started_at = datetime.utcnow()
    db.commit() # Коммитим статус PROCESSING

    try:
        # Имитация детекции
        time.sleep(random.uniform(0.5, 3.0))
        h, w = creative.image_height, creative.image_width
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
        db.commit() # Коммитим статус SUCCESS
    except Exception as e:
        logger.error(f"[{creative_id}] Ошибка детекции: {e}")
        analysis.detection_status = "ERROR"
        analysis.detection_сompleted_at = datetime.utcnow()
        analysis.detection_duration = (
            analysis.detection_сompleted_at - analysis.detection_started_at
            ).total_seconds()
        raise

