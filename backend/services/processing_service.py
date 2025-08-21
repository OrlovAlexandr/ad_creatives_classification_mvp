from PIL import Image
from database_models.creative import Creative, CreativeAnalysis
import logging
import os

logger = logging.getLogger(__name__)


def get_creative_and_analysis(
        db, creative_id: str
        ) -> tuple[Creative, CreativeAnalysis]:
    """Получает креатив и его анализ из БД."""
    creative = db.query(Creative).filter(Creative.creative_id == creative_id).first()
    if not creative:
        raise ValueError(f"Креатив с ID {creative_id} не найден")

    analysis = db.query(CreativeAnalysis).filter(
        CreativeAnalysis.creative_id == creative_id).first()
    if not analysis:
        analysis = CreativeAnalysis(creative_id=creative_id)
        db.add(analysis)
    return creative, analysis

def get_image_dimensions(temp_local_path: str) -> tuple[bool, tuple[int, int]]:
    """Получает размеры изображения."""
    try:
        with Image.open(temp_local_path) as img:
            return True, img.size # (width, height)
    except Exception as e:
        logger.error("Ошибка чтения изображения {temp_local_path}: {e}")
        
    if os.path.exists(temp_local_path):
        try:
            os.remove(temp_local_path)
            logger.info(f"Удален повреждённый временный файл {temp_local_path}")
        except Exception as e:
            logger.error(f"Ошибка при удалении временного файла {temp_local_path}: {e}")
    return False, (0, 0)
    

    