from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from database_models.creative import Creative, CreativeAnalysis
from datetime import datetime

router = APIRouter()

@router.get("/status/{creative_id}")
def get_status(creative_id: str, db: Session = Depends(get_db)):
    """Возвращает статус обработки креатива"""
    analysis = db.query(CreativeAnalysis).filter(
        CreativeAnalysis.creative_id == creative_id).first()
    creative = db.query(Creative).filter(
        Creative.creative_id == creative_id).first()

    if not creative:
        raise HTTPException(status_code=404, detail="Креатив не найден")
    
    stages = [
        {
            "name": "ocr",
            "status": "ocr_status",
            "started": "ocr_started_at",
            "completed": "ocr_completed_at",
            "duration": "ocr_duration"
        },
        {
            "name": "detection",
            "status": "detection_status",
            "started": "detection_started_at",
            "completed": "detection_completed_at",
            "duration": "detection_duration"
        },
        {
            "name": "classification",
            "status": "classification_status",
            "started": "classification_started_at",
            "completed": "classification_completed_at",
            "duration": "classification_duration"
        },
        {
            "name": "color",
            "status": "color_analysis_status",
            "started": "color_analysis_started_at",
            "completed": "color_analysis_completed_at",
            "duration": "color_analysis_duration"
        }
    ]

    def format_status_with_time(status, started, completed, duration):
        if status == "SUCCESS" and duration is not None:
            return f"{duration:.1f} sec"  # Без пробела SUCCESS (нужно для подкрашивания ячеек)
        elif status == "PROCESSING" and started:
            elapsed = (datetime.utcnow() - started).total_seconds()
            return f"{elapsed:.1f} sec "  # С пробелом PROCESSING
        elif status == "ERROR":
            return "X"
        return "—"
    
    result = {
        "creative_id": creative_id,
        "original_filename": creative.original_filename,
        "file_size": f"{creative.file_size} байт",
        "image_size": f"{creative.image_width}x{creative.image_height}",
        "upload_timestamp": creative.upload_timestamp.isoformat(),
        "main_topic": analysis.main_topic if analysis else None,
        "topic_confidence": analysis.topic_confidence if analysis else None
    }

    for stage in stages:
        status_val = getattr(analysis, stage["status"], "PENDING") if analysis else "PENDING"
        started_val = getattr(analysis, stage["started"], None) if analysis else None
        completed_val = getattr(analysis, stage["completed"], None) if analysis else None
        duration_val = getattr(analysis, stage["duration"], None) if analysis else None

        formatted = format_status_with_time(status_val, started_val, completed_val, duration_val)
        result[stage["name"] + "_status"] = formatted

    overall_status = "PENDING"
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
