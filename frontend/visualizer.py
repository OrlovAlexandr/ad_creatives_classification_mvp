import cv2
from PIL import Image


def draw_bounding_boxes(image_path, ocr_blocks=None, detected_objects=None,
                        ocr_color=(0, 255, 0), obj_color=(0, 255, 255)):
    if ocr_blocks is None:
        ocr_blocks = []
    if detected_objects is None:
        detected_objects = []

    # Загружаем изображение
    try:
        image = Image.open(image_path).convert("RGB")
        img_array = np.array(image)
        h, w, _ = img_array.shape
        img_cv = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    except Exception as e:
        raise RuntimeError(f"Не удалось загрузить изображение {image_path}: {e}")

    # Рисуем OCR-рамки
    for block in ocr_blocks:
        bbox = block.get("bbox")
        if not bbox or len(bbox) != 4:
            continue
        x1, y1, x2, y2 = int(bbox[0] * w), int(bbox[1] * h), int(bbox[2] * w), int(bbox[3] * h)
        cv2.rectangle(img_cv, (x1, y1), (x2, y2), ocr_color, 2)

        confidence = block.get("confidence", 0.0)
        label = f"OCR {confidence:.2f}"
        _draw_label(img_cv, label, (x1, y1), bg_color=ocr_color, text_color=(0, 0, 0))

    # Рисуем объекты
    for obj in detected_objects:
        bbox = obj.get("bbox")
        if not bbox or len(bbox) != 4:
            continue
        x1, y1, x2, y2 = int(bbox[0] * w), int(bbox[1] * h), int(bbox[2] * w), int(bbox[3] * h)
        cv2.rectangle(img_cv, (x1, y1), (x2, y2), obj_color, 2)

        class_name = obj.get("class", "unknown")
        confidence = obj.get("confidence", 0.0)
        label = f"{class_name} {confidence:.2f}"
        _draw_label(img_cv, label, (x1, y1), bg_color=obj_color, text_color=(0, 0, 0))

    # Конвертируем обратно в RGB
    img_with_boxes = cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB)
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
