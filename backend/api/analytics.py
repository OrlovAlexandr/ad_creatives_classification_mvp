from typing import Any

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


def _process_single_analysis(
        analysis: CreativeAnalysis,
        topic_stats: dict[str, dict[str, Any]],
        topics: dict[str, int],
        colors: dict[str, int],
):
    ocr_blocks = getattr(analysis, 'ocr_blocks', None) or []
    detected_objects = getattr(analysis, 'detected_objects', None) or []
    main_topic = getattr(analysis, 'main_topic', None)
    topic_confidence = getattr(analysis, 'topic_confidence', None)
    dominant_colors = getattr(analysis, 'dominant_colors', None) or []

    if ocr_blocks:
        try:
            confs = [b["confidence"] for b in ocr_blocks]
            if confs:
                avg_conf = sum(confs) / len(confs)
                if isinstance(avg_conf, int | float):
                    topic_stats.setdefault(main_topic, {}).setdefault("ocr_conf", 0.0)
                    topic_stats[main_topic]["ocr_conf"] += avg_conf
        except (KeyError, TypeError, ZeroDivisionError):
            pass

    if detected_objects:
        try:
            confs = [o["confidence"] for o in detected_objects]
            if confs:
                avg_conf = sum(confs) / len(confs)
                if isinstance(avg_conf, int | float):
                    topic_stats.setdefault(main_topic, {}).setdefault("obj_conf", 0.0)
                    topic_stats[main_topic]["obj_conf"] += avg_conf
        except (KeyError, TypeError, ZeroDivisionError):
            pass

    if main_topic:
        topics[main_topic] = topics.get(main_topic, 0) + 1
        topic_stats.setdefault(main_topic, {}).setdefault("count", 0)
        topic_stats[main_topic]["count"] += 1

    if topic_confidence is not None and isinstance(topic_confidence, int | float):
        topic_stats.setdefault(main_topic, {}).setdefault("topic_conf", 0.0)
        topic_stats[main_topic]["topic_conf"] += topic_confidence

    for c in dominant_colors:
        hex_color = c.get("hex")
        if hex_color:
            colors[hex_color] = colors.get(hex_color, 0) + 1


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

    topics: dict[str, int] = {}
    colors: dict[str, int] = {}
    topic_stats: dict[str, dict[str, Any]] = {
        topic: {"count": 0, "ocr_conf": 0.0, "obj_conf": 0.0, "topic_conf": 0.0}
        for topic in TOPICS
    }

    for analysis in analyses:
        _process_single_analysis(analysis, topic_stats, topics, colors)

    total_ocr_confs = sum(stats.get("ocr_conf", 0.0) for stats in topic_stats.values())
    total_obj_confs = sum(stats.get("obj_conf", 0.0) for stats in topic_stats.values())
    total_topic_confs = sum(stats.get("topic_conf", 0.0) for stats in topic_stats.values())

    avg_ocr_conf = total_ocr_confs / total_analyses if total_analyses else 0.0
    avg_obj_conf = total_obj_confs / total_analyses if total_analyses else 0.0
    avg_topic_conf = total_topic_confs / total_analyses if total_analyses else 0.0

    topics_table = []
    for topic, stats in topic_stats.items():
        count = stats["count"]
        if count == 0:
            continue
        ocr_total = stats.get("ocr_conf", 0.0)
        obj_total = stats.get("obj_conf", 0.0)
        topic_total = stats.get("topic_conf", 0.0)

        topics_table.append({
            "Тематики": TOPIC_TRANSLATIONS.get(topic, topic),
            "Кол-во": count,
            "Ср. уверенность (OCR)": f"{ocr_total / count:.2f}" if count else "—",
            "Ср. уверенность (объекты)": f"{obj_total / count:.2f}" if count else "—",
            "Cр. уверенность (топики)": f"{topic_total / count:.2f}" if count else "—",
        })

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

    analyses = db.query(CreativeAnalysis).join(Creative).filter(
        CreativeAnalysis.overall_status == "SUCCESS",
    ).all()

    total_analyses = len(analyses)

    topics: dict[str, int] = {}
    colors: dict[str, int] = {}
    topic_stats: dict[str, dict[str, Any]] = {
        topic: {"count": 0, "ocr_conf": 0.0, "obj_conf": 0.0, "topic_conf": 0.0}
        for topic in TOPICS
    }

    for analysis in analyses:
        _process_single_analysis(analysis, topic_stats, topics, colors)

    total_ocr_confs = sum(stats.get("ocr_conf", 0.0) for stats in topic_stats.values())
    total_obj_confs = sum(stats.get("obj_conf", 0.0) for stats in topic_stats.values())
    total_topic_confs = sum(stats.get("topic_conf", 0.0) for stats in topic_stats.values())

    avg_ocr_conf = total_ocr_confs / total_analyses if total_analyses else 0.0
    avg_obj_conf = total_obj_confs / total_analyses if total_analyses else 0.0
    avg_topic_conf = total_topic_confs / total_analyses if total_analyses else 0.0

    topics_table = []
    for topic, stats in topic_stats.items():
        count = stats["count"]
        if count == 0:
            continue
        ocr_total = stats.get("ocr_conf", 0.0)
        obj_total = stats.get("obj_conf", 0.0)
        topic_total = stats.get("topic_conf", 0.0)

        topics_table.append({
            "Тематики": TOPIC_TRANSLATIONS.get(topic, topic),
            "Кол-во": count,
            "Ср. уверенность (OCR)": f"{ocr_total / count:.2f}" if count else "—",
            "Ср. уверенность (объекты)": f"{obj_total / count:.2f}" if count else "—",
            "Cр. уверенность (топики)": f"{topic_total / count:.2f}" if count else "—",
        })

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
