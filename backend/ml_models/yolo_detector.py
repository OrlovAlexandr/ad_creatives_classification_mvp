from datetime import datetime
import random
import time
import os
from PIL import Image
from ultralytics import YOLO
from config import settings
import numpy as np

from config import COCO_CLASSES, CONF_THRESHOLD
import logging

logger = logging.getLogger(__name__)


_yolo_model = None

def get_yolo_model():
    global _yolo_model
    if _yolo_model is None:
        model_path = os.path.join(settings.MODEL_CACHE_DIR, settings.YOLO_MODEL_PATH)
        if not os.path.exists(model_path):
            logger.error(f"Модель YOLO не найдена по пути {model_path}")
            raise FileNotFoundError(f"YOLO model not found at {model_path}")
        try:
            device = settings.DEVICE 
            logger.info(f"Загрузка модели YOLO на устройство: {device}")
            _yolo_model = YOLO(model_path).to(device)
            logger.info("Модель YOLO успешно загружена.")
        except Exception as e:
            logger.error(f"Ошибка при загрузке модели YOLO: {e}")
            raise
    return _yolo_model

def detect_objects(image_path: str, conf_threshold: float = CONF_THRESHOLD) -> list[dict]:
    model = get_yolo_model()
    try:
        image_pil = Image.open(image_path)
        img_width, img_height = image_pil.size
        image_array = np.array(image_pil)
        
        if image_array.shape[-1] == 4:
            image_array = image_array[:, :, :3]
        
        device = settings.DEVICE
        results = model.predict(source=image_array, conf=conf_threshold, device=device)
        
        detections = []
        if results and hasattr(results[0], 'boxes') and results[0].boxes is not None:
            boxes = results[0].boxes
            for box in boxes:
                class_id = int(box.cls)
                class_name = model.names[class_id]
                confidence = float(box.conf.item())
                bbox_xyxy = box.xyxy.squeeze().tolist()
                
                x1_norm = bbox_xyxy[0] / img_width
                y1_norm = bbox_xyxy[1] / img_height
                x2_norm = bbox_xyxy[2] / img_width
                y2_norm = bbox_xyxy[3] / img_height
                
                detections.append({
                    "class": class_name,
                    "confidence": confidence,
                    "bbox": [x1_norm, y1_norm, x2_norm, y2_norm]
                })
        
        detections.sort(key=lambda x: x['confidence'], reverse=True)
        return detections[:3] 

    except Exception as e:
        logger.error(f"Ошибка при выполнении детекции YOLO для {image_path}: {e}")
        raise
