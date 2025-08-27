import re
from typing import Any

import numpy as np
from config import COCO_CLASS_TO_IDX, NUM_COCO, map_coco_to_topic
from icecream import ic

def clean_text_for_bert(s: str) -> str:
    s = str(s) if not (isinstance(s, float) and np.isnan(s)) else ""
    s = s.lower()
    s = re.sub(r'[^а-яёa-z0-9\s]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def yolo_to_vector_for_bert(classes: list, confs: list, num_classes: int = NUM_COCO) -> np.ndarray:
    vec = np.zeros(num_classes, dtype=np.float32)
    if not classes or not confs:
        return vec
    for cls, conf in zip(classes, confs):
        if cls in COCO_CLASS_TO_IDX:
            idx = COCO_CLASS_TO_IDX[cls]
            vec[idx] = max(vec[idx], float(conf))
    return vec

def yolo_top1_topic_for_bert(classes: list, confs: list) -> Any | None:
    if not classes or not confs:
        return None
    max_conf_idx = int(np.argmax(confs))
    top_cls = classes[max_conf_idx]
    return map_coco_to_topic(top_cls)
