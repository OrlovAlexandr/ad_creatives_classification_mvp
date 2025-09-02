import unittest

import numpy as np
from utils.color_utils import (
    HEX_TO_CLASS,
    classify_colors_by_palette,
    rgb_to_hex,
    rgb_to_hsv_array,
    rgb_to_hsv_single,
)


class TestColorUtils(unittest.TestCase):
    def test_rgb_to_hex(self):
        self.assertEqual(rgb_to_hex([255, 0, 0]), "#ff0000")
        self.assertEqual(rgb_to_hex([0, 255, 0]), "#00ff00")
        self.assertEqual(rgb_to_hex([0, 0, 255]), "#0000ff")
        self.assertEqual(rgb_to_hex([255, 255, 255]), "#ffffff")

    def test_rgb_to_hsv_single(self):
        # Тест для красного
        h, s, v = rgb_to_hsv_single(255, 0, 0)
        self.assertAlmostEqual(h, 0.0, delta=1.0)
        self.assertAlmostEqual(s, 100.0, delta=1.0)
        self.assertAlmostEqual(v, 100.0, delta=1.0)

        # Тест для черного
        h, s, v = rgb_to_hsv_single(0, 0, 0)
        self.assertAlmostEqual(v, 0.0, delta=1.0)
        self.assertAlmostEqual(s, 0.0, delta=1.0)

        # Тест для белого
        h, s, v = rgb_to_hsv_single(255, 255, 255)
        self.assertAlmostEqual(v, 100.0, delta=1.0)
        self.assertAlmostEqual(s, 0.0, delta=1.0)  # или близко к 0

    def test_rgb_to_hsv_array(self):
        rgb_array = np.array([[255, 0, 0], [0, 255, 0], [0, 0, 255]])
        hsv_array = rgb_to_hsv_array(rgb_array)
        self.assertEqual(hsv_array.shape, (3, 3))
        # Тест диапазона (0-1 для HSV)
        self.assertTrue(np.all(hsv_array >= 0))
        self.assertTrue(np.all(hsv_array <= 1))

    def test_classify_colors_by_palette_simple(self):
        # Тест с одним цветом, который соответствует палитре
        colors_result = {
            "dominant_colors": [
                {"hex": "#000000", "rgb": [0, 0, 0], "percent": 50.0}
                ],
            "secondary_colors": [],
        }
        result = classify_colors_by_palette(colors_result)
        exp_class = HEX_TO_CLASS.get("000000", "Неизвестно")
        self.assertIn(exp_class, result)
        self.assertEqual(result[exp_class]["percent"], 50.0)


if __name__ == "__main__":
    unittest.main()
