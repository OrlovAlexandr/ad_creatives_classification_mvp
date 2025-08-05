import logging
import os
import shutil
from typing import List

from PIL import Image
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from sqlalchemy.orm import Session

import database
import tasks
from database import SessionLocal
from models import CreativeBase, CreativeDetail, UploadResponse, AnalyticsResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Creative Classification API")


def get_db():
    """Подключение к базе данных. Создание сессии"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/upload", response_model=UploadResponse)
async def upload_files(files: List[UploadFile] = File(...), group_id: str = "1", db: Session = Depends(get_db)):
    """Загрузка и сохранение файлов"""
    uploaded = 0
    errors = []

    for file in files:
        try:
            # Проверка формата
            ext = file.filename.split(".")[-1].lower()
            if ext not in ["jpg", "jpeg", "png", "webp"]:
                errors.append(f"{file.filename}: неподдерживаемый формат")
                continue

            # Генерация ID
            creative_id = db.query(database.Creative).count() + 1  # TODO: перенести генерацию на фронт (maybe)

            # Путь сохранения
            filename = f"{creative_id}.{ext}"  # TODO: придумать как лучше назвать файл
            file_path = os.path.join("uploads", filename)

            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)  # TODO: сохранить на Minio

            # Получение метаданных
            with Image.open(file_path) as img:
                width, height = img.size

            # Сохранение в БД
            creative = database.Creative(
                creative_id=creative_id,
                group_id=int(group_id),
                original_filename=file.filename,
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
            errors.append(f"{file.filename}: {str(e)}")

    return UploadResponse(uploaded=uploaded, group_id=group_id, errors=errors)


@app.get("/groups")
def get_groups(db: Session = Depends(get_db)):
    """Список групп креативов"""
    groups = db.query(database.Creative.group_id).distinct().all()
    result = []
    for (group_id,) in groups:
        # Количество креативов в группе
        count = db.query(database.Creative).filter(database.Creative.group_id == group_id).count()

        # Первый креатив в группе (дата создания)
        first = db.query(database.Creative.upload_timestamp).filter(
            database.Creative.group_id == group_id).order_by(
            database.Creative.upload_timestamp).first()
        result.append({
            "group_id": group_id,
            "count": count,
            "created_at": first[0].isoformat() if first else None
        })
    return result


@app.get("/creatives/{creative_id}", response_model=CreativeDetail)
def get_creative(creative_id: int, db: Session = Depends(get_db)):
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
        logger.info(f"Статус анализа: {analysis.analysis_status}")
        if analysis.analysis_status == "ERROR":
            raise HTTPException(status_code=500, detail="Ошибка анализа")
    else:
        raise HTTPException(status_code=404, detail="Анализ не нашелся")

    if analysis and analysis.analysis_status == "SUCCESS":
        analysis_data = {
            "dominant_colors": analysis.dominant_colors,
            "ocr_text": analysis.ocr_text,
            "ocr_blocks": analysis.ocr_blocks,
            "text_topics": analysis.text_topics,
            "detected_objects": analysis.detected_objects,
            "main_topic": analysis.main_topic
        }
    else:
        analysis_data = None

    # Конвертация ORM в Pydantic
    result = CreativeBase.model_validate(creative)
    return CreativeDetail(**result.model_dump(), analysis=analysis_data)


@app.get("/analytics/group/{group_id}", response_model=AnalyticsResponse)
def get_analytics(group_id: int, db: Session = Depends(get_db)):
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
        database.CreativeAnalysis.analysis_status == "SUCCESS"
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
        if a.text_topics:
            main = max(a.text_topics, key=lambda x: x["confidence"])
            topic = main["topic"]
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
