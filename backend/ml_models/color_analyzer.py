from datetime import datetime
from utils.color_utils import get_top_colors, classify_colors_by_palette
import logging

logger = logging.getLogger(__name__)

def perform_color_analysis(
        creative_id: str, 
        analysis, 
        db,
        temp_local_path: str, 
        n_dominant=3, 
        n_secondary=3, 
        n_coeff=1
        ): 
    logger.info(f"[{creative_id}] Начало анализа цветов...")
    analysis.color_analysis_status = "PROCESSING"
    analysis.color_analysis_started_at = datetime.utcnow()
    db.commit()

    try:
        colors_result = get_top_colors(temp_local_path, n_dominant=3, n_secondary=3, n_coeff=1)
        palette_result = classify_colors_by_palette(colors_result)

        analysis.dominant_colors = colors_result.get("dominant_colors", [])
        analysis.secondary_colors = colors_result.get("secondary_colors", [])
        analysis.palette_colors = palette_result

        analysis.color_analysis_status = "SUCCESS"
    except Exception as e:
        logger.error(f"Ошибка при анализе цветов для {creative_id}: {e}")
        analysis.color_analysis_status = "ERROR"
        raise
    finally:
        analysis.color_analysis_completed_at = datetime.utcnow()
        if analysis.color_analysis_started_at:
            analysis.color_analysis_duration = (
                analysis.color_analysis_completed_at - analysis.color_analysis_started_at
            ).total_seconds()
        db.commit()