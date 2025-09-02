import unittest

import numpy as np
from config import NUM_COCO, map_coco_to_topic
from ml_models.preprocessing import (
    COCO_CLASS_TO_IDX,
    clean_text_for_bert,
    yolo_to_vector_for_bert,
    yolo_top1_topic_for_bert,
)


class TestPreprocessing(unittest.TestCase):
    def test_clean_text_for_bert(self):
        # Тест очистки
        input_text = "SMART WATCH 8 СЕРИИ. ДОПУСК УВЕДОМЛЕНИЙ."
        cleaned = clean_text_for_bert(input_text)
        self.assertIsInstance(cleaned, str)
        self.assertEqual(cleaned, "smart watch 8 серии допуск уведомлений")

        # Тест с цифрами и пробелами
        input_text = "  Текст   с    лишними   пробелами 123!@#  "
        cleaned = clean_text_for_bert(input_text)
        self.assertEqual(cleaned, "текст с лишними пробелами 123")

    def test_clean_text_for_bert_edge_cases(self):
        # Тест с пустой строкой
        self.assertEqual(clean_text_for_bert(""), "")
        # Тест со строкой из пробелов
        self.assertEqual(clean_text_for_bert("   "), "")
        # Тест с числами и спец символами
        self.assertEqual(clean_text_for_bert("123!@#$%^&*()_+"), "123")
        # Тест с кириллицей и латиницей
        self.assertEqual(clean_text_for_bert("Привет123Hello!"), "привет123hello")

    def test_yolo_to_vector_for_bert(self):
        # Тест с известными классами
        classes = ["clock", "person"]
        confs = [0.8, 0.6]
        vector = yolo_to_vector_for_bert(classes, confs)
        self.assertEqual(vector.shape[0], len(COCO_CLASS_TO_IDX))  # размерность

        # Проверка, что значения правильные
        clock_idx = COCO_CLASS_TO_IDX["clock"]
        person_idx = COCO_CLASS_TO_IDX["person"]
        self.assertEqual(vector[clock_idx], 0.8)
        self.assertEqual(vector[person_idx], 0.6)

        # Проверка что остальные значения 0
        vector_copy = vector.copy()
        vector_copy[clock_idx] = 0
        vector_copy[person_idx] = 0
        self.assertTrue(np.all(vector_copy == 0))

        # Тест с повторяющимся классом
        classes = ["clock", "clock"]
        confs = [0.5, 0.9]
        vector = yolo_to_vector_for_bert(classes, confs)
        self.assertEqual(vector[clock_idx], 0.9)  # должна быть макс уверенность

    def test_yolo_to_vector_for_bert_edge_cases(self):
        # Тест с пустыми списками
        vector = yolo_to_vector_for_bert([], [])
        self.assertIsInstance(vector, np.ndarray)
        self.assertEqual(vector.shape, (NUM_COCO,))
        self.assertTrue(np.all(vector == 0))

        # Тест с неизвестным классом
        vector = yolo_to_vector_for_bert(["unknown_class"], [0.5])
        self.assertIsInstance(vector, np.ndarray)
        self.assertEqual(vector.shape, (NUM_COCO,))
        self.assertTrue(np.all(vector == 0))  # Неизвестный класс будет 0

    def test_yolo_top1_topic_for_bert(self):
        # Тест с известными классами
        classes = ["clock", "person"]
        confs = [0.8, 0.6]
        topic = yolo_top1_topic_for_bert(classes, confs)
        exp_topic = map_coco_to_topic("clock")
        self.assertEqual(topic, exp_topic)

        # Тест с пустыми списками
        topic = yolo_top1_topic_for_bert([], [])
        self.assertIsNone(topic)

        # Тест с неизвестным классом
        classes = ["unknown_class"]
        confs = [0.9]
        topic = yolo_top1_topic_for_bert(classes, confs)
        exp_topic = map_coco_to_topic("unknown_class")  # Должно быть None
        self.assertIsNone(exp_topic)

        # Тест с известными и неизвестными классами
        topic = yolo_top1_topic_for_bert(["unknown_class", "clock"], [0.5, 0.9])
        exp_topic = map_coco_to_topic("clock")
        self.assertEqual(topic, exp_topic)


if __name__ == "__main__":
    unittest.main()
