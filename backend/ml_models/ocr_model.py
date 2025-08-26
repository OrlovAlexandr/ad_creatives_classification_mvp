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

            x1_norm = bbox[0][0] / img_width
            y1_norm = bbox[0][1] / img_height
            x3_norm = bbox[2][0] / img_width
            y3_norm = bbox[2][1] / img_height
            
            normalized_bbox = [x1_norm, y1_norm, x3_norm, y3_norm]    

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
