import logging
from datetime import datetime
from pathlib import Path

from database import SessionLocal
from database_models.creative import Creative
from database_models.creative import CreativeAnalysis
from ml_models import classifier
from ml_models import ocr_model
from ml_models import yolo_detector
from PIL import Image
from services.settings_service import get_setting
from sqlalchemy.orm import Session
from utils.color_utils import classify_colors_by_palette
from utils.color_utils import get_top_colors


logger = logging.getLogger(__name__)


class CreativeNotFoundError(Exception):
    def __init__(self, creative_id: str):
        message = f"Креатив с ID {creative_id} не найден"
        super().__init__(message)


def get_creative_and_analysis(
        db, creative_id: str,
) -> tuple[Creative, CreativeAnalysis]:
    creative = db.query(Creative).filter(Creative.creative_id == creative_id).first()
    if not creative:
        raise CreativeNotFoundError(creative_id)

    analysis = (
        db.query(CreativeAnalysis)
        .filter(CreativeAnalysis.creative_id == creative_id)
        .first()
    )
    if not analysis:
        analysis = CreativeAnalysis(creative_id=creative_id)
        db.add(analysis)
    return creative, analysis


def get_image_dimensions(temp_local_path: str) -> tuple[bool, tuple[int, int]]:
    temp_local_path = Path(temp_local_path)
    try:
        with Image.open(temp_local_path) as img:
            return True, img.size
    except Exception:
        logger.exception("Ошибка чтения изображения {temp_local_path}")

    if temp_local_path.exists():
        try:
            temp_local_path.unlink()
            logger.info(f"Удален повреждённый временный файл {temp_local_path}")
        except Exception:
            logger.exception("Ошибка при удалении временного файла {temp_local_path}")
    return False, (0, 0)


def perform_ocr(
        creative_id: str,
        creative: Creative,
        analysis: CreativeAnalysis,
        db: Session,
        temp_local_path: str,
):
    logger.info(f"[{creative_id}] Начало OCR...")
    analysis.ocr_status = "PROCESSING"
    analysis.ocr_started_at = datetime.utcnow()
    db.commit()

    try:
        ocr_text, ocr_blocks = ocr_model.extract_text_and_blocks(
            temp_local_path, creative=creative,
        )

        analysis.ocr_text = ocr_text
        analysis.ocr_blocks = ocr_blocks
        analysis.ocr_status = "SUCCESS"
        analysis.ocr_completed_at = datetime.utcnow()
        analysis.ocr_duration = (
                analysis.ocr_completed_at - analysis.ocr_started_at
        ).total_seconds()
        db.commit()
        logger.info(f"[{creative_id}] OCR завершен успешно.")
    except Exception as e:
        logger.exception(f"[{creative_id}] Ошибка OCR")
        analysis.ocr_status = "ERROR"
        analysis.error_message = f"OCR Error: {e!s}"
        db.commit()


def perform_detection(
        creative_id: str,
        analysis: CreativeAnalysis,
        db: Session,
        temp_local_path: str,
):
    logger.info(f"[{creative_id}] Начало детекции...")
    analysis.detection_status = "PROCESSING"
    analysis.detection_started_at = datetime.utcnow()
    db.commit()

    try:
        detected_objects = yolo_detector.detect_objects(
            temp_local_path, conf_threshold=0.35,
        )

        analysis.detected_objects = detected_objects
        analysis.detection_status = "SUCCESS"
        analysis.detection_completed_at = datetime.utcnow()
        analysis.detection_duration = (
                analysis.detection_completed_at - analysis.detection_started_at
        ).total_seconds()
        db.commit()
        logger.info(f"[{creative_id}] Детекция завершена успешно.")
    except Exception as e:
        logger.exception(f"[{creative_id}] Ошибка детекции")
        analysis.detection_status = "ERROR"
        analysis.error_message = f"Detection Error: {e!s}"
        db.commit()


def perform_classification(creative_id: str, analysis: CreativeAnalysis, db: Session):
    logger.info(f"[{creative_id}] Начало классификации...")
    analysis.classification_status = "PROCESSING"
    analysis.classification_started_at = datetime.utcnow()
    db.commit()

    try:
        ocr_text = analysis.ocr_text if analysis.ocr_text else ""
        detected_objects = (
            analysis.detected_objects if analysis.detected_objects else []
        )

        main_topic, topic_confidence = classifier.classify_creative(
            ocr_text, detected_objects,
        )

        if main_topic is not None:
            analysis.main_topic = main_topic
            analysis.topic_confidence = topic_confidence
            analysis.classification_status = "SUCCESS"
        else:
            analysis.classification_status = "ERROR"
            analysis.error_message = "Classification returned None"

        analysis.classification_completed_at = datetime.utcnow()
        analysis.classification_duration = (
                analysis.classification_completed_at - analysis.classification_started_at
        ).total_seconds()
        db.commit()
        logger.info(
            f"[{creative_id}] Классификация завершена. Тема: {main_topic}, Уверенность: {topic_confidence:.4f}",
        )
    except Exception as e:
        logger.exception(f"[{creative_id}] Ошибка классификации")
        analysis.classification_status = "ERROR"
        analysis.error_message = f"Classification Error: {e!s}"
        db.commit()


def perform_color_analysis(
        creative_id: str,
        analysis,
        db,
        temp_local_path: str,
):
    db_session = SessionLocal()
    try:
        n_dominant = get_setting(db_session, "DOMINANT_COLORS_COUNT", 3)
        n_secondary = get_setting(db_session, "SECONDARY_COLORS_COUNT", 3)
    finally:
        db_session.close()

    logger.info(f"[{creative_id}] Начало анализа цветов...")
    analysis.color_analysis_status = "PROCESSING"
    analysis.color_analysis_started_at = datetime.utcnow()
    db.commit()

    try:
        colors_result = get_top_colors(
            temp_local_path, n_dominant=n_dominant, n_secondary=n_secondary, n_coeff=1,
        )
        palette_result = classify_colors_by_palette(colors_result)

        analysis.dominant_colors = colors_result.get("dominant_colors", [])
        analysis.secondary_colors = colors_result.get("secondary_colors", [])
        analysis.palette_colors = palette_result

        analysis.color_analysis_status = "SUCCESS"
    except Exception:
        logger.exception(f"Ошибка при анализе цветов для {creative_id}")
        analysis.color_analysis_status = "ERROR"
        raise
    finally:
        analysis.color_analysis_completed_at = datetime.utcnow()
        if analysis.color_analysis_started_at:
            analysis.color_analysis_duration = (
                    analysis.color_analysis_completed_at
                    - analysis.color_analysis_started_at
            ).total_seconds()
        db.commit()
