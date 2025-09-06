import unittest

import numpy as np
from utils.color_utils import HEX_TO_CLASS
from utils.color_utils import classify_colors_by_palette
from utils.color_utils import rgb_to_hex
from utils.color_utils import rgb_to_hsv_array
from utils.color_utils import rgb_to_hsv_single


MIN_HSV_VALUE = 0.0
MAX_HSV_VALUE = 100.0
TEST_COLOR_PERCENT = 50.0

class TestColorUtils(unittest.TestCase):
    def test_rgb_to_hex(self):
        assert rgb_to_hex([255, 0, 0]) == "#ff0000"
        assert rgb_to_hex([0, 255, 0]) == "#00ff00"
        assert rgb_to_hex([0, 0, 255]) == "#0000ff"
        assert rgb_to_hex([255, 255, 255]) == "#ffffff"

    def test_rgb_to_hsv_single(self):
        # Тест для красного
        h, s, v = rgb_to_hsv_single(255, 0, 0)
        assert h == MIN_HSV_VALUE
        assert s == MAX_HSV_VALUE
        assert v == MAX_HSV_VALUE

        # Тест для черного
        h, s, v = rgb_to_hsv_single(0, 0, 0)
        assert v == MIN_HSV_VALUE
        assert s == MIN_HSV_VALUE

        # Тест для белого
        h, s, v = rgb_to_hsv_single(255, 255, 255)
        assert v == MAX_HSV_VALUE
        assert s == MIN_HSV_VALUE

    def test_rgb_to_hsv_array(self):
        rgb_array = np.array([[255, 0, 0], [0, 255, 0], [0, 0, 255]])
        hsv_array = rgb_to_hsv_array(rgb_array)
        assert hsv_array.shape == (3, 3)
        # Тест диапазона (0-1 для HSV)
        assert np.all(hsv_array >= 0)
        assert np.all(hsv_array <= 1)

    def test_classify_colors_by_palette_simple(self):
        # Тест с одним цветом, который соответствует палитре
        colors_result = {
            "dominant_colors": [
                {"hex": "#000000", "rgb": [0, 0, 0], "percent": TEST_COLOR_PERCENT},
                ],
            "secondary_colors": [],
        }
        result = classify_colors_by_palette(colors_result)
        exp_class = HEX_TO_CLASS.get("000000", "Неизвестно")
        assert exp_class in result
        assert result[exp_class]["percent"] == TEST_COLOR_PERCENT


if __name__ == "__main__":
    unittest.main()
