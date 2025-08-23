import cv2
import numpy as np
from PIL import Image
import requests
from io import BytesIO
from icecream import ic
import os
from dotenv import load_dotenv

load_dotenv()

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
MINIO_SECURE = os.getenv("MINIO_SECURE").lower() == "true"
MINIO_BUCKET = os.getenv("MINIO_BUCKET")
if MINIO_SECURE:
    MINIO_BASE_URL = f"https://{MINIO_ENDPOINT}"
else:

    MINIO_BASE_URL = f"http://{MINIO_ENDPOINT}"
MINIO_PUBLIC_URL = os.getenv("MINIO_PUBLIC_URL")
if not MINIO_PUBLIC_URL:
    MINIO_PUBLIC_URL = MINIO_BASE_URL 

def draw_bounding_boxes(image_path_or_url=None, image_url=None, ocr_blocks=None, 
                        detected_objects=None,
                        ocr_color=(0, 255, 0), obj_color=(0, 255, 255)):
    if ocr_blocks is None: ocr_blocks = []
    if detected_objects is None: detected_objects = []

    img_source = image_url or image_path_or_url
    if not img_source:
        raise ValueError("Необходимо указать image_path_or_url или image_url")

    # Загружаем изображение
    try:
        ic(f"Загрузка изображения до отрисовки: {img_source}")

        if img_source.startswith(('http://', 'https://')):
            # Загрузка по URL            
            response = requests.get(img_source)
            response.raise_for_status()
            image = Image.open(BytesIO(response.content)).convert("RGB")
            ic(image)
        else:
            # Загрузка из локального файла
            image = Image.open(img_source).convert("RGB")

        img_array = np.array(image)
        ic(img_array.shape)
        h, w, _ = img_array.shape
        img_cv = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    except requests.RequestException as e:
        ic("Ошибка при загрузке изображения по URL", img_source)
        raise RuntimeError(f"Ошибка сети при загрузке {img_source}: {e}")
    except (FileNotFoundError, OSError) as e:
        ic("Ошибка при загрузке изображения из локального файла", img_source)
        raise RuntimeError(f"Не удалось открыть файл {img_source}: {e}")
    except Exception as e:
        ic("Неизвестная ошибка при загрузке изображения", img_source)
        raise RuntimeError(f"Неизвестная ошибка при загрузке {img_source}: {e}")

    # Рисуем OCR-рамки
    for block in ocr_blocks:
        bbox_raw = block.get("bbox")
        if not bbox_raw or len(bbox_raw) != 4:
            continue

        normalized_bbox = _normalize_bbox(bbox_raw, w, h)
        if normalized_bbox is None:
            continue
        x1, y1, x2, y2 = normalized_bbox
        cv2.rectangle(img_cv, (x1, y1), (x2, y2), ocr_color, 2)

        confidence = block.get("confidence", 0.0)
        label = f"OCR {confidence:.2f}"
        _draw_label(img_cv, label, (x1, y1), bg_color=ocr_color, text_color=(0, 0, 0))

    # Рисуем объекты
    for obj in detected_objects:
        bbox_raw = obj.get("bbox")
        normalized_bbox = _normalize_bbox(bbox_raw, w, h)
        if normalized_bbox is None:
            continue
        x1, y1, x2, y2 = normalized_bbox
        cv2.rectangle(img_cv, (x1, y1), (x2, y2), obj_color, 2)

        class_name = obj.get("class", "unknown")
        confidence = obj.get("confidence", 0.0)
        label = f"{class_name} {confidence:.2f}"
        _draw_label(img_cv, label, (x1, y1), bg_color=obj_color, text_color=(0, 0, 0))

    # Конвертируем обратно в RGB
    img_with_boxes = cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB)
    ic(img_with_boxes.shape)
    return Image.fromarray(img_with_boxes)


def _draw_label(image_cv, text, position, bg_color, text_color):
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.6
    font_thickness = 1
    padding = 2

    (text_width, text_height), baseline = cv2.getTextSize(text, font, font_scale, font_thickness)
    x, y = position

    text_x = x
    text_y = max(y - 10, text_height + padding)

    cv2.rectangle(
        image_cv,
        (text_x, text_y - text_height - padding),
        (text_x + text_width + 2 * padding, text_y + padding),
        bg_color,
        -1
    )

    cv2.putText(
        image_cv,
        text,
        (text_x + padding, text_y),
        font,
        font_scale,
        text_color,
        font_thickness,
        cv2.LINE_AA
    )

def _normalize_bbox(bbox, img_width, img_height):
    if not bbox or not isinstance(bbox, list):
        return None

    try:
        if len(bbox) == 4:
            if isinstance(bbox[0], (int, float)):
                x1_norm, y1_norm, x2_norm, y2_norm = bbox
                x1 = int(x1_norm * img_width)
                y1 = int(y1_norm * img_height)
                x2 = int(x2_norm * img_width)
                y2 = int(y2_norm * img_height)
                return (x1, y1, x2, y2)
            elif isinstance(bbox[0], list) and len(bbox[0]) == 2:
                points = np.array(bbox)
                x_coords = points[:, 0] * img_width
                y_coords = points[:, 1] * img_height
                x1 = int(np.min(x_coords))
                y1 = int(np.min(y_coords))
                x2 = int(np.max(x_coords))
                y2 = int(np.max(y_coords))
                return (x1, y1, x2, y2)
    except (ValueError, IndexError, TypeError) as e:
        ic(f"Ошибка нормализации bbox {bbox}: {e}")
        pass
        
    return None
