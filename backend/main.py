import logging
import os
import shutil
from typing import List

from PIL import Image
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Form

from sqlalchemy.orm import Session

import database
import tasks
from contextlib import asynccontextmanager
from database import SessionLocal, engine, Base
from models import CreativeBase, CreativeDetail, UploadResponse, AnalyticsResponse, UploadRequest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(title="Creative Classification API", lifespan=lifespan)


def get_db():
    """Подключение к базе данных. Создание сессии"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/upload", response_model=UploadResponse)
async def upload_files(
    files: List[UploadFile] = File(...), 
    group_id: str = Form(...),
    creative_ids: List[str] = Form(...),
    original_filenames: List[str] = Form(...),
    db: Session = Depends(get_db)
    ):
    """Загрузка и сохранение файлов"""
    logger.info(
        f"Received: group_id={group_id}, creative_ids={creative_ids}, filenames={original_filenames}"
        )
    
    if len(creative_ids) != len(files) or len(creative_ids) != len(original_filenames):
        raise HTTPException(
            status_code=400, 
            detail="Количество creative_ids не совпадает с количеством файлов"
            )
    
    uploaded = 0
    errors = []

    for file, creative_id, orig_filename in zip(files, creative_ids, original_filenames):
        try:
            # Проверка формата
            ext = file.filename.split(".")[-1].lower()
            if ext not in ["jpg", "jpeg", "png", "webp"]:
                errors.append(f"{orig_filename}: неподдерживаемый формат")
                continue
            
            # Уникальное имя файла — UUID
            file_path = os.path.join("uploads", f"{creative_id}.{ext}")
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)  # TODO: сохранить на Minio

            # Получение метаданных
            with Image.open(file_path) as img:
                width, height = img.size

            # Сохранение в БД
            creative = database.Creative(
                creative_id=creative_id,
                group_id=group_id,
                original_filename=orig_filename,
                file_path=file_path,
                file_size=os.path.getsize(file_path),
                file_format=ext,
                image_width=width,
                image_height=height
            )
            db.add(creative)
            db.commit()

            # Запуск задачи
            tasks.process_creative.delay(creative_id)

            uploaded += 1
        except Exception as e:
            errors.append(f"{orig_filename}: {str(e)}")

    return UploadResponse(uploaded=uploaded, group_id=group_id, errors=errors)


@app.get("/groups")
def get_groups(db: Session = Depends(get_db)):
    """Список групп креативов"""
    groups = db.query(database.Creative.group_id).distinct().all()
    result = []
    for (group_id,) in groups:
        # Количество креативов в группе
        count = db.query(database.Creative).filter(
            database.Creative.group_id == group_id
            ).count()

        # Первый креатив в группе (дата создания)
        first = db.query(database.Creative.upload_timestamp).filter(
            database.Creative.group_id == group_id).order_by(
            database.Creative.upload_timestamp).first()
        result.append({
            "group_id": group_id,
            "count": count,
            "created_at": first[0].isoformat() if first else None
        })

    result.sort(key=lambda x: x["created_at"] or "", reverse=True)  # Сортировка
    return result


@app.get("/creatives/{creative_id}", response_model=CreativeDetail)
def get_creative(creative_id: str, db: Session = Depends(get_db)):
    """Детали креатива"""
    logger.info(f"GET /creatives/{creative_id}")

    # Поиск и проверка креатива
    creative = db.query(database.Creative).filter(database.Creative.creative_id == creative_id).first()
    if not creative:
        logger.error(f"Creative {creative_id} not found")
        raise HTTPException(status_code=404, detail="Креатив не найден")

    # Поиск и проверка анализа
    analysis = db.query(database.CreativeAnalysis).filter(
        database.CreativeAnalysis.creative_id == creative_id).first()

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
            "ocr_text": analysis.ocr_text,
            "ocr_blocks": analysis.ocr_blocks,
            "detected_objects": analysis.detected_objects,
            "main_topic": analysis.main_topic,
            "topic_confidence": analysis.topic_confidence
        }
    else:
        analysis_data = None

    # Конвертация ORM в Pydantic
    result = CreativeBase(**creative_data) 
    return CreativeDetail(**result.model_dump(), analysis=analysis_data)


@app.get("/groups/{group_id}/creatives")
def get_creatives_by_group(group_id: str, db: Session = Depends(get_db)):
    """Возвращает список креативов в группе с данными и результатом анализа"""
    
    creatives = db.query(database.Creative).filter(
        database.Creative.group_id == group_id
        ).all()

    result = []
    for c in creatives:
        analysis = db.query(database.CreativeAnalysis).filter(
            database.CreativeAnalysis.creative_id == c.creative_id
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


@app.get("/status/{creative_id}")
def get_status(creative_id: str, db: Session = Depends(get_db)):
    """Возвращает статус обработки креатива"""
    analysis = db.query(database.CreativeAnalysis).filter(
        database.CreativeAnalysis.creative_id == creative_id).first()
    creative = db.query(database.Creative).filter(
        database.Creative.creative_id == creative_id).first()

    if not creative:
        raise HTTPException(status_code=404, detail="Креатив не найден")

    if not analysis:
        return {
            "creative_id": creative_id,
            "original_filename": creative.original_filename,
            "file_size": f"{creative.file_size} байт",
            "image_size": f"{creative.image_width}x{creative.image_height}",
            "upload_timestamp": creative.upload_timestamp.isoformat().split(".")[0].replace("T", " "),
            "ocr_status": "PENDING",
            "detection_status": "PENDING",
            "classification_status": "PENDING",
            "overall_status": "PENDING",
            "main_topic": None,
            "topic_confidence": None
        }

    return {
        "creative_id": creative_id,
        "original_filename": creative.original_filename,
        "file_size": f"{creative.file_size} байт",
        "image_size": f"{creative.image_width}×{creative.image_height}",
        "upload_timestamp": creative.upload_timestamp.isoformat().split(".")[0].replace("T", " "),
        "ocr_status": analysis.ocr_status,
        "detection_status": analysis.detection_status,
        "classification_status": analysis.classification_status,
        "overall_status": analysis.overall_status,
        "main_topic": analysis.main_topic,
        "topic_confidence": analysis.topic_confidence
    }


@app.get("/analytics/group/{group_id}", response_model=AnalyticsResponse)
def get_analytics(group_id: str, db: Session = Depends(get_db)):
    """
    Аналитика группы креативов.
    TODO: продумать что показывать в аналитике, и что возвращать на фронт
    """
    # Поиск и проверка группы
    creatives = db.query(database.Creative).filter(database.Creative.group_id == group_id).all()
    if not creatives:
        raise HTTPException(status_code=404, detail="Группа не найдена")

    analyses = db.query(database.CreativeAnalysis).join(database.Creative).filter(
        database.Creative.group_id == group_id,
        database.CreativeAnalysis.overall_status == "SUCCESS"
    ).all()

    total = len(analyses)
    avg_ocr_conf = 0.0
    avg_obj_conf = 0.0
    topics = {}
    colors = {}
    objects = {}

    for a in analyses:
        # OCR confidence (среднее по блокам)
        if a.ocr_blocks:
            confs = [b["confidence"] for b in a.ocr_blocks]
            avg_ocr_conf += sum(confs) / len(confs)

        # Object confidence
        if a.detected_objects:
            confs = [o["confidence"] for o in a.detected_objects]
            avg_obj_conf += sum(confs) / len(confs)

        # Топики
        if a.main_topic:
            topic = a.main_topic
            topics[topic] = topics.get(topic, 0) + 1

        # Цвета
        for c in a.dominant_colors:
            hex_color = c["hex"]
            colors[hex_color] = colors.get(hex_color, 0) + 1

        # Объекты
        for o in a.detected_objects:
            cls = o["class"]
            objects[cls] = objects.get(cls, 0) + 1

    avg_ocr_conf = avg_ocr_conf / total if total else 0
    avg_obj_conf = avg_obj_conf / total if total else 0

    return {
        "summary": {
            "total_creatives": total,
            "first_upload": min(c.upload_timestamp for c in creatives).isoformat(),
            "avg_ocr_confidence": round(avg_ocr_conf, 2),
            "avg_object_confidence": round(avg_obj_conf, 2)
        },
        "topics": [{"topic": k, "count": v} for k, v in topics.items()],
        "dominant_colors": [{"hex": k, "count": v} for k, v in colors.items()],
        "objects": [{"class": k, "count": v} for k, v in objects.items()]
    }
