import logging
import os
import shutil
from typing import List
from datetime import datetime

from PIL import Image
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Form
from minio import Minio
from minio.error import S3Error
from sqlalchemy.orm import Session
from config import TOPICS, TOPIC_TRANSLATIONS

import database
import tasks
from contextlib import asynccontextmanager
from database import SessionLocal, engine, Base
from models import CreativeBase, CreativeDetail, UploadResponse, AnalyticsResponse, UploadRequest
from color_utils import COLOR_CLASSES, COLOR_VISUAL_CLASSES, HEX_TO_CLASS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация MinIO
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_SECURE = os.getenv("MINIO_SECURE", "False").lower() == "true"
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "creatives")

# Инициализация клиента MinIO
minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=MINIO_SECURE
)

# Создание бакета, если он не существует
try:
    if not minio_client.bucket_exists(MINIO_BUCKET):
        minio_client.make_bucket(MINIO_BUCKET)
except S3Error as e:
    logger.error(f"Ошибка при создании бакета MinIO: {e}")
    raise

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


def upload_to_minio(file_path: str, object_name: str) -> str:
    try:
        # Проверяем существование бакета
        if not minio_client.bucket_exists(MINIO_BUCKET):
            minio_client.make_bucket(MINIO_BUCKET)
            
        minio_client.fput_object(MINIO_BUCKET, object_name, file_path)
        return f"{MINIO_BUCKET}/{object_name}"
    except S3Error as e:
        logger.error(f"MinIO error: {e}")
        raise

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

    # Создаем временную директорию, если ее нет
    os.makedirs("uploads", exist_ok=True)

    for file, creative_id, orig_filename in zip(files, creative_ids, original_filenames):
        try:
            # Проверка формата
            ext = file.filename.split(".")[-1].lower()
            if ext not in ["jpg", "jpeg", "png", "webp"]:
                errors.append(f"{orig_filename}: неподдерживаемый формат")
                continue
            
            # Сохраняем временно файл локально
            temp_file_path = os.path.join("uploads", f"{creative_id}.{ext}")
            with open(temp_file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            # Получение метаданных
            with Image.open(temp_file_path) as img:
                width, height = img.size

            # Загрузка в MinIO
            object_name = f"{creative_id}.{ext}"
            minio_path = upload_to_minio(temp_file_path, object_name)

            # Удаляем временный файл
            # os.remove(temp_file_path)

            # Сохранение в БД
            creative = database.Creative(
                creative_id=creative_id,
                group_id=group_id,
                original_filename=orig_filename,
                file_path=minio_path,  # Сохраняем путь в MinIO
                file_size=os.path.getsize(temp_file_path),
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
            # Удаляем временный файл, если он был создан
            #if os.path.exists(temp_file_path):
            #    os.remove(temp_file_path)
            
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


def calculate_group_processing_time(db: Session, group_id: str) -> tuple[float, int]:
    analyses = db.query(
        database.CreativeAnalysis.ocr_started_at,
        database.CreativeAnalysis.analysis_timestamp
    ).join(
        database.Creative,
        database.Creative.creative_id == database.CreativeAnalysis.creative_id
    ).filter(
        database.Creative.group_id == group_id,
        database.CreativeAnalysis.overall_status == "SUCCESS"
    ).all()

    if not analyses:
        return 0.0, 0

    start_times = [a.ocr_started_at for a in analyses if a.ocr_started_at]
    end_times = [a.analysis_timestamp for a in analyses if a.analysis_timestamp]

    if not start_times or not end_times:
        return 0.0, len(analyses)

    min_start = min(start_times)
    max_end = max(end_times)
    total_time = (max_end - min_start).total_seconds()

    return total_time, len(analyses)

def get_color_class_distribution(analyses):
    class_distribution = {}

    for analysis in analyses:
        palette_colors = analysis.palette_colors or {}
        for class_name, info in palette_colors.items():
            if class_name in COLOR_CLASSES:
                class_distribution[class_name] = class_distribution.get(class_name, 0) + info["percent"]

    return class_distribution

def get_topic_color_distribution(analyses, top_n=5):
    topic_data = {}

    for a in analyses:
        if not a.main_topic or a.overall_status != "SUCCESS":
            continue

        topic = a.main_topic
        if topic not in topic_data:
            topic_data[topic] = {}

        palette_colors = a.palette_colors or {}
        for class_name, info in palette_colors.items():
            if class_name in COLOR_VISUAL_CLASSES:
                hex_list = list(COLOR_VISUAL_CLASSES[class_name])
                hex_color = f"#{hex_list[0].upper()}" if hex_list else "#CCCCCC"
                if class_name not in topic_data[topic]:
                    topic_data[topic][class_name] = {"hex": hex_color, "percent": 0.0}
                topic_data[topic][class_name]["percent"] += info["percent"]

    result = {}
    for topic, colors in topic_data.items():
        sorted_colors = sorted(colors.items(), key=lambda x: x[1]["percent"], reverse=True)
        top_colors = sorted_colors[:top_n]

        percents = [item[1]["percent"] for item in top_colors]
        total = sum(percents)

        if total > 0:
            normalized = [p / total * 100 for p in percents]
        else:
            normalized = [100 / len(percents)] * len(percents)  # на случай, если все нули

        result[topic] = []
        for (class_name, data), norm_percent in zip(top_colors, normalized):
            result[topic].append({
                "class": class_name,
                "hex": data["hex"],
                "percent": norm_percent
            })

    return result

@app.get("/analytics/group/{group_id}", response_model=AnalyticsResponse)
def get_analytics(group_id: str, db: Session = Depends(get_db)):
    creatives = db.query(database.Creative).filter(database.Creative.group_id == group_id).all()
    if not creatives:
        raise HTTPException(status_code=404, detail="Группа не найдена")

    analyses = db.query(database.CreativeAnalysis).join(database.Creative).filter(
        database.Creative.group_id == group_id,
        database.CreativeAnalysis.overall_status == "SUCCESS"
    ).all()

    total_analyses = len(analyses)
    avg_ocr_conf = 0.0
    avg_obj_conf = 0.0
    topics = {}
    colors = {}
    topic_stats = {}

    for topic in TOPICS:
        topic_stats[topic] = {
            "count": 0,
            "ocr_conf": 0.0,
            "obj_conf": 0.0
        }

    for a in analyses:
        if a.ocr_blocks:
            confs = [b["confidence"] for b in a.ocr_blocks]
            avg_ocr_conf += sum(confs) / len(confs)
            if a.main_topic:
                topic_stats[a.main_topic]["ocr_conf"] += sum(confs) / len(confs)

        if a.detected_objects:
            confs = [o["confidence"] for o in a.detected_objects]
            avg_obj_conf += sum(confs) / len(confs)
            if a.main_topic:
                topic_stats[a.main_topic]["obj_conf"] += sum(confs) / len(confs)

        if a.main_topic:
            topic = a.main_topic
            topics[topic] = topics.get(topic, 0) + 1
            topic_stats[topic]["count"] += 1

        for c in a.dominant_colors or []:
            hex_color = c.get("hex")
            if hex_color:
                colors[hex_color] = colors.get(hex_color, 0) + 1

    avg_ocr_conf = avg_ocr_conf / total_analyses if total_analyses else 0
    avg_obj_conf = avg_obj_conf / total_analyses if total_analyses else 0

    # таблица по тематикам
    topics_table = []
    for topic, stats in topic_stats.items():
        if stats["count"] == 0:
            continue
        topics_table.append({
            "Тематики": TOPIC_TRANSLATIONS.get(topic, topic),
            "Кол-во": stats["count"],
            "Ср. уверенность (OCR)": f"{stats['ocr_conf'] / stats['count']:.2f}" if stats["count"] else "—",
            "Ср. уверенность (объекты)": f"{stats['obj_conf'] / stats['count']:.2f}" if stats["count"] else "—"
        })

    # Общее время обработки группы
    total_processing_time, total_creatives = calculate_group_processing_time(db, group_id)

    color_class_dist = get_color_class_distribution(analyses)
    topic_color_distribution = get_topic_color_distribution(analyses, top_n=5)


    return {
        "summary": {
            "total_creatives": total_analyses,
            "avg_ocr_confidence": round(avg_ocr_conf, 2),
            "avg_object_confidence": round(avg_obj_conf, 2)
        },
        "topics": [{"topic": k, "count": v} for k, v in topics.items()],
        "dominant_colors": [{"hex": k, "count": v} for k, v in colors.items()],
        "topics_table": topics_table,
        "total_processing_time": round(total_processing_time, 2),
        "total_creatives_in_group": total_creatives,
        "color_class_distribution": color_class_dist,
        "topic_color_distribution": topic_color_distribution
    }

@app.get("/analytics/all", response_model=AnalyticsResponse)
def get_analytics_all(db: Session = Depends(get_db)):
    groups = db.query(database.Creative.group_id).distinct().all()
    if not groups:
        raise HTTPException(status_code=404, detail="Нет групп в БД")

    total_processing_time = 0.0
    total_creatives_all = 0

    for (group_id,) in groups:
        group_time, group_count = calculate_group_processing_time(db, group_id)
        total_processing_time += group_time
        total_creatives_all += group_count

    # Анализ всех креативов
    analyses = db.query(database.CreativeAnalysis).join(database.Creative).filter(
        database.CreativeAnalysis.overall_status == "SUCCESS"
    ).all()

    total_analyses = len(analyses)
    avg_ocr_conf = 0.0
    avg_obj_conf = 0.0
    topics = {}
    colors = {}
    topic_stats = {}

    for topic in TOPICS:
        topic_stats[topic] = {"count": 0, "ocr_conf": 0.0, "obj_conf": 0.0}

    for a in analyses:
        if a.ocr_blocks:
            confs = [b["confidence"] for b in a.ocr_blocks]
            avg_ocr_conf += sum(confs) / len(confs)
            if a.main_topic:
                topic_stats[a.main_topic]["ocr_conf"] += sum(confs) / len(confs)

        if a.detected_objects:
            confs = [o["confidence"] for o in a.detected_objects]
            avg_obj_conf += sum(confs) / len(confs)
            if a.main_topic:
                topic_stats[a.main_topic]["obj_conf"] += sum(confs) / len(confs)

        if a.main_topic:
            topic = a.main_topic
            topics[topic] = topics.get(topic, 0) + 1
            topic_stats[topic]["count"] += 1

        for c in a.dominant_colors or []:
            hex_color = c.get("hex")
            if hex_color:
                colors[hex_color] = colors.get(hex_color, 0) + 1

    avg_ocr_conf = avg_ocr_conf / total_analyses if total_analyses else 0
    avg_obj_conf = avg_obj_conf / total_analyses if total_analyses else 0

    topics_table = []
    for topic, stats in topic_stats.items():
        if stats["count"] == 0:
            continue
        topics_table.append({
            "Тематики": TOPIC_TRANSLATIONS.get(topic, topic),
            "Кол-во": stats["count"],
            "Ср. уверенность (OCR)": f"{stats['ocr_conf'] / stats['count']:.2f}" if stats["count"] else "—",
            "Ср. уверенность (объекты)": f"{stats['obj_conf'] / stats['count']:.2f}" if stats["count"] else "—"
        })

    # Среднее время на один креатив
    avg_time_per_creative = total_processing_time / total_creatives_all if total_creatives_all > 0 else 0

    color_class_dist = get_color_class_distribution(analyses)
    topic_color_distribution = get_topic_color_distribution(analyses, top_n=5)


    return {
        "summary": {
            "total_creatives": total_creatives_all,
            "avg_ocr_confidence": round(avg_ocr_conf, 2),
            "avg_object_confidence": round(avg_obj_conf, 2)
        },
        "topics": [{"topic": k, "count": v} for k, v in topics.items()],
        "dominant_colors": [{"hex": k, "count": v} for k, v in colors.items()],
        "topics_table": topics_table,
        "total_processing_time": round(total_processing_time, 2),
        "total_creatives_in_group": total_creatives_all,
        "avg_time_per_creative": round(avg_time_per_creative, 2),
        "color_class_distribution": color_class_dist,
        "topic_color_distribution": topic_color_distribution
    }