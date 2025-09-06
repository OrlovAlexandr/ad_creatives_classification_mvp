import logging
from pathlib import Path

import numpy as np
from config import CONF_THRESHOLD
from config import settings
from PIL import Image
from ultralytics import YOLO


logger = logging.getLogger(__name__)

_yolo_model = None

NUM_COLOR_CHANNELS = 4


class YOLOModelNotFoundError(FileNotFoundError):
    def __init__(self, model_path):
        message = f"Модель YOLO не найдена по пути {model_path}"
        super().__init__(message)


def get_yolo_model():
    global _yolo_model  # noqa: PLW0603
    if _yolo_model is None:
        model_path = Path(settings.MODEL_CACHE_DIR) / settings.YOLO_MODEL_PATH
        if not model_path.exists():
            logger.error(f"Модель YOLO не найдена по пути {model_path}")
            raise YOLOModelNotFoundError(model_path)
        try:
            device = settings.DEVICE
            logger.info(f"Загрузка модели YOLO на устройство: {device}")
            _yolo_model = YOLO(model_path).to(device)
            logger.info("Модель YOLO успешно инициализирована.")
        except Exception:
            logger.exception("Ошибка при инициализации модели YOLO")
            raise
    return _yolo_model


def detect_objects(image_path: str, conf_threshold: float = CONF_THRESHOLD) -> list[dict]:
    model = get_yolo_model()
    try:
        with Image.open(image_path) as image_pil:
            logger.debug("[YOLO] Изображение открыто успешно")
            img_width, img_height = image_pil.size
            image_array = np.array(image_pil)
            logger.debug(f"[YOLO] Массив NumPy создан. Форма: {image_array.shape}")

            if image_array.shape[-1] == NUM_COLOR_CHANNELS:
                logger.debug("[YOLO] Удаление альфа-канала")
                image_array = image_array[:, :, :3]

        device = settings.DEVICE
        logger.debug(f"[YOLO] Параметры predict, conf={conf_threshold}")

        results = model.predict(source=image_array, conf=conf_threshold, device=device)

        detections = []
        if results and hasattr(results[0], 'boxes') and results[0].boxes is not None:
            boxes = results[0].boxes
            box_index = 0
            for box in boxes:
                try:
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
                        "bbox": [x1_norm, y1_norm, x2_norm, y2_norm],
                    })
                    box_index += 1
                except Exception as box_e:
                    logger.error(f"[YOLO] Ошибка при обработке бокса #{box_index}: {box_e}", exc_info=True)
                    box_index += 1

            detections.sort(key=lambda x: x['confidence'], reverse=True)
            return detections[:3]

    except Exception:
        logger.exception(f"Ошибка при выполнении детекции YOLO для {image_path}")
        raise

    else:
        logger.info("[YOLO] Объекты не обнаружены или results пустой")
        return []
