from datetime import datetime
import random
import time

from config import TOPICS
import logging

logger = logging.getLogger(__name__)

def perform_classification(
        creative_id: str, 
        analysis, 
        db,
        ):
    """Выполняет классификацию."""
    logger.info(f"[{creative_id}] Начало классификации...")
    analysis.classification_status = "PROCESSING"
    analysis.classification_started_at = datetime.utcnow()
    db.commit() # Коммитим статус PROCESSING

    try:
        # Имитация классификации
        time.sleep(random.uniform(0.5, 3.0))
        topic = random.choice(TOPICS)
        analysis.topic = topic

        topic_confidence = round(random.uniform(0.6, 0.95), 2)
        analysis.main_topic = topic
        analysis.topic_confidence = topic_confidence
        analysis.classification_status = "SUCCESS"

        analysis.classification_сompleted_at = datetime.utcnow()
        analysis.classification_duration = (
            analysis.classification_сompleted_at - analysis.classification_started_at
            ).total_seconds()
        db.commit()
    except Exception as e:
        logger.error(f"[{creative_id}] Ошибка в классификации: {str(e)}")
        analysis.classification_status = "ERROR"
        analysis.classification_сompleted_at = datetime.utcnow()
        analysis.classification_duration = (
            analysis.classification_сompleted_at - analysis.classification_started_at
            ).total_seconds()
        db.commit()
        raise