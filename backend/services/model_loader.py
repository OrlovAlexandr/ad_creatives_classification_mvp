import os
import logging
from minio_client import minio_client
from config import settings
from icecream import ic

logger = logging.getLogger(__name__)


def ensure_model_exists_locally(model_name: str, minio_path: str, local_path: str):
    if os.path.exists(local_path):
        logger.info(f"Модель {model_name} уже существует локально: {local_path}")
        return True

    logger.info(f"Модель {model_name} не найдена локально. Загрузка из MinIO...")
    try:
        os.makedirs(os.path.dirname(local_path), exist_ok=True)

        response = minio_client.get_object(settings.MODEL_MINIO_BUCKET, minio_path)
        with open(local_path, 'wb') as f:
            f.write(response.read())
        logger.info(f"Модель {model_name} успешно загружена в {local_path}")
        ic(f"Модель {model_name} успешно загружена в {local_path}")
        return True
    except Exception as e:
        logger.error(f"Ошибка загрузки модели {model_name} из MinIO: {e}")
        return False

def ensure_easyocr_weights_exists_locally(local_weights_dir: str, minio_weights_dir: str):
    if os.path.exists(local_weights_dir):
        logger.info(f"Веса EasyOCR уже существуют локально: {local_weights_dir}")
        return True

    logger.info(f"Веса EasyOCR не найдены локально. Загрузка из MinIO...")
    try:
        os.makedirs(local_weights_dir, exist_ok=True)
        easyocr_files = [
            "model/craft_mlt_25k.pth",
            "model/cyrillic_g2.pth",
            "model/english_g2.pth",
            # "user_network/"
        ]

        for file_path in easyocr_files:
            minio_file_path = f"{minio_weights_dir}/{file_path}"
            local_file_path = os.path.join(local_weights_dir, file_path)
            os.makedirs(os.path.dirname(local_file_path), exist_ok=True)

            response = minio_client.get_object(settings.MODEL_MINIO_BUCKET, minio_file_path)
            with open(local_file_path, 'wb') as f:
                f.write(response.read())
            logger.info(f"Загружен файл EasyOCR: {file_path}")

        logger.info(f"Веса EasyOCR успешно загружены в {local_weights_dir}")
        ic("Веса EasyOCR успешно загружены в {local_weights_dir}")
        return True
    except Exception as e:
        logger.error(f"Ошибка загрузки весов EasyOCR из MinIO: {e}")
        return False
    
def load_models():
    success = True

    yolo_local_path = os.path.join(settings.MODEL_CACHE_DIR, settings.YOLO_MODEL_PATH)
    if not ensure_model_exists_locally("YOLOv8", settings.YOLO_MODEL_PATH, yolo_local_path):
        logger.error("Не удалось загрузить модель YOLOv8.")
        success = False

    easyocr_local_weights_dir = os.path.join(settings.MODEL_CACHE_DIR, settings.EASYOCR_WEIGHTS_DIR)
    if not ensure_easyocr_weights_exists_locally(easyocr_local_weights_dir, settings.EASYOCR_WEIGHTS_DIR):
        logger.error("Не удалось загрузить веса EasyOCR.")
        success = False

    bert_local_path = os.path.join(settings.MODEL_CACHE_DIR, settings.BERT_MODEL_PATH)
    if not ensure_model_exists_locally("Multimodal BERT", settings.BERT_MODEL_PATH, bert_local_path):
        logger.error("Не удалось загрузить модель Multimodal BERT.")
        success = False

    if success:
        logger.info("Все модели успешно загружены или уже существуют.")
    else:
        logger.error("Не удалось загрузить одну или несколько моделей.")
    return success
