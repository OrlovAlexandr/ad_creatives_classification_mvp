import logging
from datetime import datetime
from pathlib import Path

from celery import Celery
from config import settings
from database import SessionLocal
from services.model_loader import load_models
from services.processing_service import get_creative_and_analysis
from services.processing_service import get_image_dimensions
from services.processing_service import perform_classification
from services.processing_service import perform_color_analysis
from services.processing_service import perform_detection
from services.processing_service import perform_ocr
from utils.minio_utils import download_file_from_minio


logger = logging.getLogger(__name__)

celery = Celery("tasks", broker=settings.REDIS_URL, backend=settings.REDIS_URL)

logger.info("Инициализация ML моделей...")
if not load_models():
    logger.error("Критическая ошибка при копировании моделей. Worker может работать некорректно.")
else:
    logger.info("ML модели готовы к использованию.")


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
        perform_detection(creative_id, analysis, db, temp_local_path)

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
        analysis.analysis_timestamp = datetime.utcnow()
        analysis.total_duration = (
                analysis.analysis_timestamp - analysis.ocr_started_at
        ).total_seconds()
        db.commit()
        logger.info(f"[{creative_id}] Анализ завершен")

    except Exception as exc:
        logger.error(f"[{creative_id}] Критическая ошибка: {exc}", exc_info=True)
        if db:
            db.rollback()
            _, analysis = get_creative_and_analysis(creative_id, db)
            if analysis:
                analysis.overall_status = "ERROR"
                analysis.error_message = str(exc)
                db.commit()
            raise self.retry(exc=exc, countdown=5) from exc
    else:
        return {"status": "success", "creative_id": creative_id}

    finally:
        if db:
            db.close()
        # Удаляем временный файл
        if temp_local_path and Path(temp_local_path).exists():
            try:
                Path(temp_local_path).unlink()
                logger.debug(f"[{creative_id}] Удален временный файл {temp_local_path}")
            except OSError as e:
                logger.warning(f"[{creative_id}] Не удалось удалить временный файл {temp_local_path}: {e}")
