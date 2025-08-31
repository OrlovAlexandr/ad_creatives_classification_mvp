from datetime import datetime

from config import ML_STAGES
from database import get_db
from database_models.creative import Creative
from database_models.creative import CreativeAnalysis
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from sqlalchemy.orm import Session


router = APIRouter()


@router.get("/status/{creative_id}")
def get_status(creative_id: str, db: Session = Depends(get_db)):
    """Возвращает статус обработки креатива."""

    def format_status_with_time(status, started, duration):
        if status == "SUCCESS" and duration is not None:
            return f"{duration:.1f} sec"  # Без пробела SUCCESS (нужно для подкрашивания ячеек)
        if status == "PROCESSING" and started:
            _elapsed = (datetime.utcnow() - started).total_seconds()
            return f"{_elapsed:.1f} sec "  # С пробелом PROCESSING
        if status == "ERROR":
            return "X"
        return "—"

    analysis = db.query(CreativeAnalysis).filter(
        CreativeAnalysis.creative_id == creative_id).first()
    creative = db.query(Creative).filter(
        Creative.creative_id == creative_id).first()

    if not creative:
        raise HTTPException(status_code=404, detail="Креатив не найден")

    result = {
        "creative_id": creative_id,
        "original_filename": creative.original_filename,
        "file_size": f"{creative.file_size} байт",
        "image_size": f"{creative.image_width}x{creative.image_height}",
        "upload_timestamp": creative.upload_timestamp.isoformat(),
        "main_topic": analysis.main_topic if analysis else None,
        "topic_confidence": analysis.topic_confidence if analysis else None,
    }

    for stage in ML_STAGES:
        status_val = getattr(analysis, stage["status"], "PENDING") if analysis else "PENDING"
        started_val = getattr(analysis, stage["started"], None) if analysis else None
        duration_val = getattr(analysis, stage["duration"], None) if analysis else None

        formatted = format_status_with_time(status_val, started_val, duration_val)
        result[stage["name"] + "_status"] = formatted

    total_time_str = "—"

    if analysis:
        if analysis.overall_status == "SUCCESS" and analysis.total_duration is not None:
            total_time_str = f"{analysis.total_duration:.1f} sec"
        elif analysis.overall_status == "PROCESSING":
            if analysis.ocr_started_at:
                elapsed = (datetime.utcnow() - analysis.ocr_started_at).total_seconds()
                total_time_str = f"{elapsed:.1f} sec "
        elif analysis.overall_status == "ERROR":
            total_time_str = "X"
        else:
            total_time_str = "—"
    else:
        total_time_str = "—"
    result["overall_status"] = total_time_str

    return result
