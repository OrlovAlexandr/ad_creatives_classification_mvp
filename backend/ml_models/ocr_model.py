from config import TOPICS, TOPIC_TEXTS
from datetime import datetime
import random
import time
from PIL import Image
import easyocr
import os
from config import settings
from icecream import ic
import logging

logger = logging.getLogger(__name__)


_ocr_reader = None

def get_ocr_reader():
    global _ocr_reader
    if _ocr_reader is None:
        try:
            weights_dir = os.path.join(settings.MODEL_CACHE_DIR, settings.EASYOCR_WEIGHTS_DIR)
            model_dir = os.path.join(weights_dir, "model")
            user_network_dir = os.path.join(weights_dir, "user_network")

            if not os.path.exists(model_dir):
                logger.error(f"Директория с весами EasyOCR model не найдена: {model_dir}")
                raise FileNotFoundError(f"EasyOCR model weights dir not found: {model_dir}")

            logger.info(f"Инициализация EasyOCR Reader с локальными весами из {weights_dir}")
            use_gpu = settings.DEVICE.startswith('gpu')
            logger.info(f"Устройство для EasyOCR: {'GPU' if use_gpu else 'CPU'}")

            _ocr_reader = easyocr.Reader(
                ['en', 'ru'], 
                gpu=use_gpu,
                model_storage_directory=model_dir,
                user_network_directory=user_network_dir,
                download_enabled=False 
            )
            logger.info("EasyOCR Reader успешно инициализирован.")
        except Exception as e:
            logger.error(f"Ошибка при инициализации EasyOCR Reader: {e}")
            raise
    return _ocr_reader

def extract_text_and_blocks(image_path: str, creative) -> tuple[str, list]:
    reader = get_ocr_reader()
    try:
        results = reader.readtext(image_path)

        full_text_parts = []
        ocr_blocks = []
        img_width, img_height = creative.image_width, creative.image_height

        for (bbox, text, conf) in results:
            full_text_parts.append(text)

            print("bbox", bbox, type(bbox))
            bbox.pop(3)
            print("bbox pop", bbox)
            bbox.pop(1)
            print("bbox pop", bbox)

            normalized_bbox = [
                [point[0] / img_width, point[1] / img_height] for point in bbox
            ]
            print("normalized_bbox", normalized_bbox)        

            ocr_blocks.append({
                "text": text,
                "bbox": normalized_bbox,
                "confidence": conf
            })
            
        full_text = " ".join(full_text_parts)
        ic("Текст из EasyOCR:", full_text)
        return full_text, ocr_blocks

    except Exception as e:
        logger.error(f"Ошибка при выполнении OCR для {image_path}: {e}")
        raise


# def perform_ocr(
#         creative_id: str, 
#         creative,
#         analysis, 
#         db, 
#         temp_local_path: str
#         ):
#     """Выполняет OCR."""
#     logger.info(f"[{creative_id}] Начало OCR...")
#     analysis.ocr_status = "PROCESSING"
#     analysis.ocr_started_at = datetime.utcnow()
#     db.commit() # Коммитим статус PROCESSING

#     try:
#         # Имитация OCR
#         time.sleep(random.uniform(0.5, 3.0))
#         topic = random.choice(TOPICS)
#         full_text = TOPIC_TEXTS.get(topic, "Текст не найден")
#         words = full_text.split(". ")
#         blocks = []

#         h, w = creative.image_height, creative.image_width
#         for word in words:
#             confidence = round(random.uniform(0.7, 0.99), 2)
#             x1 = random.uniform(0.02, 0.1) * w
#             y1 = random.uniform(0.02, 0.8) * h
#             x2 = x1 + random.uniform(0.3, 0.7) * w
#             y2 = y1 + random.uniform(0.05, 0.15) * h
#             blocks.append({
#                 "text": word,
#                 "bbox": [x1/w, y1/h, x2/w, y2/h],
#                 "confidence": confidence
#             })

#         analysis.ocr_text = full_text
#         analysis.ocr_blocks = blocks
#         analysis.ocr_status = "SUCCESS"
#         analysis.ocr_completed_at = datetime.utcnow()
#         analysis.ocr_duration = (
#             analysis.ocr_completed_at - analysis.ocr_started_at
#             ).total_seconds()
#         db.commit()
#         logger.info(f"[{creative_id}] OCR завершен успешно.")
#     except Exception as e:
#         logger.error(f"[{creative_id}] Ошибка OCR: {e}")
#         analysis.ocr_status = "ERROR"
#         analysis.ocr_completed_at = datetime.utcnow()
#         analysis.ocr_duration = (
#             analysis.ocr_completed_at - analysis.ocr_started_at
#             ).total_seconds()
#         db.commit()
#         raise