import unittest

import numpy as np
from config import NUM_COCO
from config import map_coco_to_topic
from ml_models.preprocessing import COCO_CLASS_TO_IDX
from ml_models.preprocessing import clean_text_for_bert
from ml_models.preprocessing import yolo_to_vector_for_bert
from ml_models.preprocessing import yolo_top1_topic_for_bert


CLOCK_THRESHOLD = 0.8
CLOCK_THRESHOLD_BIGGER = 0.9
PERSON_THRESHOLD = 0.6

class TestPreprocessing(unittest.TestCase):
    def test_clean_text_for_bert(self):
        # Тест очистки
        input_text = "SMART WATCH 8 СЕРИИ. ДОПУСК УВЕДОМЛЕНИЙ."
        cleaned = clean_text_for_bert(input_text)
        assert isinstance(cleaned, str)
        assert cleaned == "smart watch 8 серии допуск уведомлений"

        # Тест с цифрами и пробелами
        input_text = "  Текст   с    лишними   пробелами 123!@#  "
        cleaned = clean_text_for_bert(input_text)
        assert cleaned == "текст с лишними пробелами 123"

    def test_clean_text_for_bert_edge_cases(self):
        assert clean_text_for_bert("") == ""
        assert clean_text_for_bert("   ") == ""
        # Тест с числами и спец символами
        assert clean_text_for_bert("123!@#$%^&*()_+") == "123"
        # Тест с кириллицей и латиницей
        assert clean_text_for_bert("Привет123Hello!") == "привет123hello"

    def test_yolo_to_vector_for_bert(self):
        # Тест с известными классами
        classes = ["clock", "person"]
        confs = [CLOCK_THRESHOLD, PERSON_THRESHOLD]
        vector = yolo_to_vector_for_bert(classes, confs)
        assert vector.shape[0] == len(COCO_CLASS_TO_IDX)  # размерность

        # Проверка, что значения правильные
        clock_idx = COCO_CLASS_TO_IDX["clock"]
        person_idx = COCO_CLASS_TO_IDX["person"]
        assert vector[clock_idx] == CLOCK_THRESHOLD
        assert vector[person_idx] == PERSON_THRESHOLD

        # Проверка что остальные значения 0
        vector_copy = vector.copy()
        vector_copy[clock_idx] = 0
        vector_copy[person_idx] = 0
        assert np.all(vector_copy == 0)

        # Тест с повторяющимся классом
        classes = ["clock", "clock"]
        confs = [CLOCK_THRESHOLD, CLOCK_THRESHOLD_BIGGER]
        vector = yolo_to_vector_for_bert(classes, confs)
        assert vector[clock_idx] == CLOCK_THRESHOLD_BIGGER  # должна быть макс уверенность

    def test_yolo_to_vector_for_bert_edge_cases(self):
        # Тест с пустыми списками
        vector = yolo_to_vector_for_bert([], [])
        assert isinstance(vector, np.ndarray)
        assert vector.shape == (NUM_COCO,)
        assert np.all(vector == 0)

        # Тест с неизвестным классом
        vector = yolo_to_vector_for_bert(["unknown_class"], [0.5])
        assert isinstance(vector, np.ndarray)
        assert vector.shape == (NUM_COCO,)
        assert np.all(vector == 0)  # Неизвестный класс будет 0

    def test_yolo_top1_topic_for_bert(self):
        # Тест с известными классами
        classes = ["clock", "person"]
        confs = [0.8, 0.6]
        topic = yolo_top1_topic_for_bert(classes, confs)
        exp_topic = map_coco_to_topic("clock")
        assert topic == exp_topic

        # Тест с пустыми списками
        topic = yolo_top1_topic_for_bert([], [])
        assert topic is None

        # Тест с неизвестным классом
        classes = ["unknown_class"]
        confs = [0.9]
        topic = yolo_top1_topic_for_bert(classes, confs)
        assert topic is None

        # Тест с известными и неизвестными классами
        topic = yolo_top1_topic_for_bert(["unknown_class", "clock"], [0.5, 0.9])
        exp_topic = map_coco_to_topic("clock")
        assert topic == exp_topic


if __name__ == "__main__":
    unittest.main()
