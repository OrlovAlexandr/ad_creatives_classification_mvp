from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from database_models.creative import Creative, CreativeAnalysis
from models import CreativeBase, CreativeDetail
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/creatives/{creative_id}", response_model=CreativeDetail)
def get_creative(creative_id: str, db: Session = Depends(get_db)):
    logger.info(f"GET /creatives/{creative_id}")

    # Поиск и проверка креатива
    creative = db.query(Creative).filter(Creative.creative_id == creative_id).first()
    if not creative:
        logger.error(f"Creative {creative_id} not found")
        raise HTTPException(status_code=404, detail="Креатив не найден")

    # Поиск и проверка анализа
    analysis = db.query(CreativeAnalysis).filter(
        CreativeAnalysis.creative_id == creative_id).first()

    logger.info(f"Creative {creative_id} found")
    if analysis:
        logger.info(f"Статус анализа: {analysis.overall_status}")
        if analysis.overall_status == "ERROR":
            raise HTTPException(status_code=500, detail="Ошибка анализа")
    else:
        raise HTTPException(status_code=404, detail="Анализ не нашелся")

    creative_data = {
        "creative_id": creative.creative_id,
        "group_id": creative.group_id,
        "original_filename": creative.original_filename,
        "file_path": creative.file_path,
        "file_size": creative.file_size,
        "file_format": creative.file_format,
        "image_width": creative.image_width,
        "image_height": creative.image_height,
        "upload_timestamp": creative.upload_timestamp.isoformat()
    }

    if analysis and analysis.overall_status == "SUCCESS":
        analysis_data = {
            "dominant_colors": analysis.dominant_colors,
            "secondary_colors": analysis.secondary_colors,
            "palette_colors": analysis.palette_colors,
            "ocr_text": analysis.ocr_text,
            "ocr_blocks": analysis.ocr_blocks,
            "detected_objects": analysis.detected_objects,
            "main_topic": analysis.main_topic,
            "topic_confidence": analysis.topic_confidence
        }
    else:
        analysis_data = None

    result = CreativeBase(**creative_data) 
    return CreativeDetail(**result.model_dump(), analysis=analysis_data)


@router.get("/groups/{group_id}/creatives")
def get_creatives_by_group(group_id: str, db: Session = Depends(get_db)):
    creatives = db.query(Creative).filter(
        Creative.group_id == group_id
        ).all()

    result = []
    for c in creatives:
        analysis = db.query(CreativeAnalysis).filter(
            CreativeAnalysis.creative_id == c.creative_id
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
            "analysis": analysis is not None and analysis.overall_status == "SUCCESS"
        })
    return result
