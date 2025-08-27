from config import TOPIC_TRANSLATIONS
from config import TOPICS
from database import get_db
from database_models.creative import Creative
from database_models.creative import CreativeAnalysis
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from models import AnalyticsResponse
from services.analytics_service import calculate_group_processing_time
from services.analytics_service import get_color_class_distribution
from services.analytics_service import get_topic_color_distribution
from sqlalchemy.orm import Session


router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/group/{group_id}", response_model=AnalyticsResponse)
def get_analytics(group_id: str, db: Session = Depends(get_db)):
    creatives = db.query(Creative).filter(Creative.group_id == group_id).all()
    if not creatives:
        raise HTTPException(status_code=404, detail="Группа не найдена")

    analyses = db.query(CreativeAnalysis).join(Creative).filter(
        Creative.group_id == group_id,
        CreativeAnalysis.overall_status == "SUCCESS",
    ).all()

    total_analyses = len(analyses)
    avg_ocr_conf = 0.0
    avg_obj_conf = 0.0
    avg_topic_conf = 0.0
    topics = {}
    colors = {}
    topic_stats = {}

    for topic in TOPICS:
        topic_stats[topic] = {
            "count": 0,
            "ocr_conf": 0.0,
            "obj_conf": 0.0,
            "topic_conf": 0.0,
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

        if a.topic_confidence:
            topic_stats[a.main_topic]["topic_conf"] += a.topic_confidence
            avg_topic_conf += a.topic_confidence

        for c in a.dominant_colors or []:
            hex_color = c.get("hex")
            if hex_color:
                colors[hex_color] = colors.get(hex_color, 0) + 1

    avg_ocr_conf = avg_ocr_conf / total_analyses if total_analyses else 0
    avg_obj_conf = avg_obj_conf / total_analyses if total_analyses else 0
    avg_topic_conf = avg_topic_conf / total_analyses if total_analyses else 0

    # таблица по тематикам
    topics_table = []
    for topic, stats in topic_stats.items():
        if stats["count"] == 0:
            continue
        topics_table.append({
            "Тематики": TOPIC_TRANSLATIONS.get(topic, topic),
            "Кол-во": stats["count"],
            "Ср. уверенность (OCR)": f"{stats['ocr_conf'] / stats['count']:.2f}" if stats["count"] else "—",
            "Ср. уверенность (объекты)": f"{stats['obj_conf'] / stats['count']:.2f}" if stats["count"] else "—",
            "Cр. уверенность (топики)": f"{stats['topic_conf'] / stats['count']:.2f}" if stats["count"] else "—",
        })

    # Общее время обработки группы
    total_processing_time, total_creatives = calculate_group_processing_time(db, group_id)

    color_class_dist = get_color_class_distribution(analyses)
    topic_color_distribution = get_topic_color_distribution(analyses, top_n=5)


    return {
        "summary": {
            "total_creatives": total_analyses,
            "avg_ocr_confidence": round(avg_ocr_conf, 2),
            "avg_object_confidence": round(avg_obj_conf, 2),
            "avg_topic_confidence": round(avg_topic_conf, 2),
        },
        "topics": [{"topic": k, "count": v} for k, v in topics.items()],
        "dominant_colors": [{"hex": k, "count": v} for k, v in colors.items()],
        "topics_table": topics_table,
        "total_processing_time": round(total_processing_time, 2),
        "total_creatives_in_group": total_creatives,
        "color_class_distribution": color_class_dist,
        "topic_color_distribution": topic_color_distribution,
    }

@router.get("/all", response_model=AnalyticsResponse)
def get_analytics_all(db: Session = Depends(get_db)):
    groups = db.query(Creative.group_id).distinct().all()
    if not groups:
        raise HTTPException(status_code=404, detail="Нет групп в БД")

    total_processing_time = 0.0
    total_creatives_all = 0

    for (group_id,) in groups:
        group_time, group_count = calculate_group_processing_time(db, group_id)
        total_processing_time += group_time
        total_creatives_all += group_count

    # Анализ всех креативов
    analyses = db.query(CreativeAnalysis).join(Creative).filter(
        CreativeAnalysis.overall_status == "SUCCESS",
    ).all()

    total_analyses = len(analyses)
    avg_ocr_conf = 0.0
    avg_obj_conf = 0.0
    avg_topic_conf = 0.0
    topics = {}
    colors = {}
    topic_stats = {}

    for topic in TOPICS:
        topic_stats[topic] = {
            "count": 0,
            "ocr_conf": 0.0,
            "obj_conf": 0.0,
            "topic_conf": 0.0,
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

        if a.topic_confidence:
            topic_stats[a.main_topic]["topic_conf"] += a.topic_confidence
            avg_topic_conf += a.topic_confidence

        for c in a.dominant_colors or []:
            hex_color = c.get("hex")
            if hex_color:
                colors[hex_color] = colors.get(hex_color, 0) + 1

    avg_ocr_conf = avg_ocr_conf / total_analyses if total_analyses else 0
    avg_obj_conf = avg_obj_conf / total_analyses if total_analyses else 0
    avg_topic_conf = avg_topic_conf / total_analyses if total_analyses else 0

    topics_table = []
    for topic, stats in topic_stats.items():
        if stats["count"] == 0:
            continue
        topics_table.append(
            {
                "Тематики": TOPIC_TRANSLATIONS.get(topic, topic),
                "Кол-во": stats["count"],
                "Ср. уверенность (OCR)": f"{stats['ocr_conf'] / stats['count']:.2f}" if stats["count"] else "—",
                "Ср. уверенность (объекты)": f"{stats['obj_conf'] / stats['count']:.2f}" if stats["count"] else "—",
                "Cр. уверенность (топики)": f"{stats['topic_conf'] / stats['count']:.2f}" if stats["count"] else "—",
            },
        )

    # Среднее время на один креатив
    avg_time_per_creative = total_processing_time / total_creatives_all if total_creatives_all > 0 else 0

    color_class_dist = get_color_class_distribution(analyses)
    topic_color_distribution = get_topic_color_distribution(analyses, top_n=5)


    return {
        "summary": {
            "total_creatives": total_creatives_all,
            "avg_ocr_confidence": round(avg_ocr_conf, 2),
            "avg_object_confidence": round(avg_obj_conf, 2),
            "avg_topic_confidence": round(avg_topic_conf, 2),
        },
        "topics": [{"topic": k, "count": v} for k, v in topics.items()],
        "dominant_colors": [{"hex": k, "count": v} for k, v in colors.items()],
        "topics_table": topics_table,
        "total_processing_time": round(total_processing_time, 2),
        "total_creatives_in_group": total_creatives_all,
        "avg_time_per_creative": round(avg_time_per_creative, 2),
        "color_class_distribution": color_class_dist,
        "topic_color_distribution": topic_color_distribution,
    }
