import re
import numpy as np
from config import COCO_CLASS_TO_IDX, NUM_COCO, map_coco_to_topic
from icecream import ic

def clean_text_for_bert(s: str) -> str:
    s = str(s) if not (isinstance(s, float) and np.isnan(s)) else ""
    s = s.lower()
    s = re.sub(r'[^а-яёa-z0-9\s]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    ic("Текст после очистки:", s)
    return s

def yolo_to_vector_for_bert(classes: list, confs: list, num_classes: int = NUM_COCO) -> np.ndarray:
    vec = np.zeros(num_classes, dtype=np.float32)
    if not classes or not confs:
        return vec
    for cls, conf in zip(classes, confs):
        if cls in COCO_CLASS_TO_IDX:
            idx = COCO_CLASS_TO_IDX[cls]
            vec[idx] = max(vec[idx], float(conf))
    ic("Вектор YOLO (первые 10):", vec[:10])
    return vec

def yolo_top1_topic_for_bert(classes: list, confs: list) -> str:
    if not classes or not confs:
        return None
    max_conf_idx = int(np.argmax(confs))
    top_cls = classes[max_conf_idx]
    ic("Топ-1 тема YOLO:", top_cls)
    return map_coco_to_topic(top_cls)

# Пример использования
# if __name__ == "__main__":
#     test_text = "SMART WATCH 8 СЕРИИ. ДОПУСК УВЕДОМЛЕНИЙ. МОЩНАЯ БАТАРЕЯ"
#     cleaned = clean_text_for_bert(test_text)
#     print(f"Очищенный текст: {cleaned}")
#     
#     test_yolo_classes = ['clock', 'cell phone']
#     test_yolo_confs = [0.85, 0.45]
#     vec = yolo_to_vector_for_bert(test_yolo_classes, test_yolo_confs)
#     print(f"Вектор YOLO (первые 10): {vec[:10]}")
#     
#     top1_topic = yolo_top1_topic_for_bert(test_yolo_classes, test_yolo_confs)
#     print(f"Топ-1 тема: {top1_topic}")