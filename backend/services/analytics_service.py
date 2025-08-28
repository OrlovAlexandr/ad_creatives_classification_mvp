from config import COLOR_CLASSES
from config import COLOR_VISUAL_CLASSES
from database_models.creative import Creative
from database_models.creative import CreativeAnalysis
from sqlalchemy.orm import Session


def calculate_group_processing_time(db: Session, group_id: str) -> tuple[float, int]:
    analyses = db.query(
        CreativeAnalysis.ocr_started_at,
        CreativeAnalysis.analysis_timestamp,
    ).join(
        Creative,
        Creative.creative_id == CreativeAnalysis.creative_id,
    ).filter(
        Creative.group_id == group_id,
        CreativeAnalysis.overall_status == "SUCCESS",
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
        for (class_name, data), norm_percent in zip(top_colors, normalized, strict=False):
            result[topic].append({
                "class": class_name,
                "hex": data["hex"],
                "percent": norm_percent,
            })

    return result
