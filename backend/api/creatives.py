import logging

from config import settings
from database import get_db
from database_models.creative import Creative
from database_models.creative import CreativeAnalysis
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from models import CreativeDetail
from sqlalchemy.orm import Session


logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/creatives/{creative_id}", response_model=CreativeDetail)
def get_creative(creative_id: str, db: Session = Depends(get_db)):
    logger.info(f"GET /creatives/{creative_id}")

    # Поиск и проверка креатива
    creative = db.query(Creative).filter(Creative.creative_id == creative_id).first()
    if not creative:
        logger.error(f"Креатив {creative_id} не найден")
        raise HTTPException(status_code=404, detail="Креатив не найден")

    # Поиск и проверка анализа
    analysis = db.query(CreativeAnalysis).filter(
        CreativeAnalysis.creative_id == creative_id).first()

    logger.info(f"Креатив {creative_id} найден")
    if analysis:
        logger.info(f"Статус анализа: {analysis.overall_status}")
        if analysis.overall_status == "ERROR":
            raise HTTPException(status_code=500, detail="Ошибка анализа")
    else:
        raise HTTPException(status_code=404, detail="Анализ не нашелся")

    public_file_url = f"{settings.MINIO_PUBLIC_URL}/{creative.file_path}"

    creative_data = {
        "creative_id": creative.creative_id,
        "group_id": creative.group_id,
        "original_filename": creative.original_filename,
        "file_path": public_file_url,
        "file_size": creative.file_size,
        "file_format": creative.file_format,
        "image_width": creative.image_width,
        "image_height": creative.image_height,
        "upload_timestamp": creative.upload_timestamp.isoformat(),
        "overall_status": None,
        "ocr_text": None,
        "ocr_blocks": None,
        "detected_objects": None,
        "main_topic": None,
        "topic_confidence": None,
        "dominant_colors": None,
        "secondary_colors": None,
        "palette_colors": None,
    }

    if analysis and analysis.overall_status == "SUCCESS":
        logger.info("Заполнение данных анализа")
        creative_data.update(
            {
                "overall_status": analysis.overall_status,
                "ocr_text": analysis.ocr_text,
                "ocr_blocks": analysis.ocr_blocks,
                "detected_objects": analysis.detected_objects,
                "main_topic": analysis.main_topic,
                "topic_confidence": analysis.topic_confidence,
                "dominant_colors": analysis.dominant_colors,
                "secondary_colors": analysis.secondary_colors,
                "palette_colors": analysis.palette_colors,
            },
        )
    elif analysis:
        logger.info(
            f"Заполнение данных анализа с ошибкой. Статус анализа: {analysis.overall_status}",
        )
        creative_data.update(
            {
                "overall_status": analysis.overall_status,
            },
        )

    return CreativeDetail(**creative_data)


@router.get("/groups/{group_id}/creatives")
def get_creatives_by_group(group_id: str, db: Session = Depends(get_db)):
    creatives = db.query(Creative).filter(
        Creative.group_id == group_id,
        ).all()

    result = []
    for c in creatives:
        analysis = db.query(CreativeAnalysis).filter(
            CreativeAnalysis.creative_id == c.creative_id,
        ).first()

        result.append({
            "creative_id": c.creative_id,
            "original_filename": c.original_filename,
            "file_path": c.file_path,
            "file_size": c.file_size,
            "file_format": c.file_format,
            "image_width": c.image_width,
            "image_height": c.image_height,
            "upload_timestamp": c.upload_timestamp.isoformat(),
            "analysis": analysis is not None and analysis.overall_status == "SUCCESS",
        })
    return result
