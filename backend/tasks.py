from celery import Celery
from celery.signals import worker_ready
from database import SessionLocal
import os
from datetime import datetime, timezone
from config import settings
from utils.minio_utils import download_file_from_minio
from services.processing_service import (
    get_creative_and_analysis, 
    get_image_dimensions,
    perform_classification, 
    perform_color_analysis, 
    perform_ocr, 
    perform_detection
    )
from ml_models import ocr_model, yolo_detector, classifier
from services.model_loader import load_models

import logging

logger = logging.getLogger(__name__)


celery = Celery("tasks", broker=settings.REDIS_URL, backend=settings.REDIS_URL)

logger.info("Инициализация ML моделей...")
if not load_models():
    logger.error("Критическая ошибка при копировании моделей. Worker может работать некорректно.")
else:
    logger.info("ML модели готовы к использованию.")

@worker_ready.connect
def preload_models(**kwargs):
    logger.info("Celery worker готов. Начинается предзагрузка моделей...")
    try:
        logger.info("Предзагрузка EasyOCR...")
        ocr_model.get_ocr_reader()
        logger.info("Модель EasyOCR предзагружена.")

        logger.info("Предзагрузка YOLO...")
        yolo_detector.get_yolo_model()
        logger.info("Модель YOLO предзагружена.")

        logger.info("Предзагрузка BERT...")
        classifier.get_bert_model_and_tokenizer()
        logger.info("Модель BERT предзагружена.")

        logger.info("Все модели успешно Загружены. Worker готов.")
    except Exception as e:
        logger.error(f"Ошибка при предзагрузке моделей: {e}", exc_info=True)

@celery.task(bind=True, max_retries=3)
def process_creative(self, creative_id: str):
    db = None
    temp_local_path = None
    try:
        db = SessionLocal()
        logger.info(f"Начало обработки задачи {creative_id}")

        # Получаем креатив и его анализ
        creative, analysis = get_creative_and_analysis(db, creative_id)

        analysis.overall_status = "PROCESSING"
        db.commit()

        # Скачиваем изображение из MinIO в локальную папку на период обработки
        temp_local_path = f"/tmp/{creative_id}.{creative.file_format}"
        if not download_file_from_minio(creative, analysis, db, temp_local_path):
            return {"status": "error", "creative_id": creative_id}

        # Получаем размеры изображения
        success, dimensions = get_image_dimensions(temp_local_path)
        if not success:
            logger.error(f"Ошибка чтения изображения {temp_local_path}: {dimensions}")
            analysis.overall_status = "ERROR"
            analysis.error_message = "Некорректное изображение"
            db.commit()
            return {"status": "error", "creative_id": creative_id}
        
        creative.image_width, creative.image_height = dimensions
        db.add(creative)
        db.commit()


        # OCR
        perform_ocr(creative_id, creative, analysis, db, temp_local_path)
        
        # Детекция объектов
        perform_detection(creative_id, creative, analysis, db, temp_local_path)

        # Классификация
        perform_classification(creative_id, analysis, db)

        # Анализ цветов
        perform_color_analysis(
            creative_id, 
            analysis, 
            db, 
            temp_local_path, 
            )
        
        # Завершение
        analysis.overall_status = "SUCCESS"
        analysis.analysis_timestamp = datetime.utcnow()  # noqa: UP017
        analysis.total_duration = (
            analysis.analysis_timestamp - analysis.ocr_started_at
        ).total_seconds()
        db.commit()
        logger.info(f"[{creative_id}] Анализ завершен")
        return {"status": "success", "creative_id": creative_id}

    except Exception as exc:
        logger.error(f"[{creative_id}] Критическая ошибка: {exc}", exc_info=True)
        if db:
            db.rollback()
            _, analysis = get_creative_and_analysis(creative_id, db)
            if analysis:
                analysis.overall_status = "ERROR"
                analysis.error_message = str(exc)
                db.commit()
            raise self.retry(exc=exc, countdown=5)
    finally:
        if db:
            db.close()
        # Удаляем временный файл
        if temp_local_path and os.path.exists(temp_local_path):
            try:
                os.remove(temp_local_path)
                logger.debug(f"[{creative_id}] Удален временный файл {temp_local_path}")
            except Exception as e:
                logger.warning(f"[{creative_id}] Не удалось удалить временный файл {temp_local_path}: {e}")
