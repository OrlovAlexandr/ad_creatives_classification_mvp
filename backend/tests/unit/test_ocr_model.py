import unittest
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from ml_models.ocr_model import extract_text_and_blocks


TEST_NUM_BLOCKS = 2
CONF_SMALL_THRESHOLD = 0.6
CONF_BIG_THRESHOLD = 0.9

class TestOcrModel(unittest.TestCase):
    @patch("ml_models.ocr_model.get_ocr_reader")
    def test_extract_text_and_blocks_success(self, mock_get_reader):
        mock_creative = MagicMock()
        mock_creative.image_width = 400
        mock_creative.image_height = 300

        mock_reader = MagicMock()
        mock_get_reader.return_value = mock_reader

        # Имитация результата readtext (bbox, text, conf)
        mock_result = [
            ([[10, 10], [50, 10], [50, 30], [10, 30]], "Papa", CONF_BIG_THRESHOLD),
            ([[60, 60], [100, 60], [100, 80], [60, 80]], "Mozhet", CONF_SMALL_THRESHOLD),
        ]
        mock_reader.readtext.return_value = mock_result

        # Файл-заглушка
        temp_path = "temp_path.jpg"
        text, blocks = extract_text_and_blocks(temp_path, creative=mock_creative)

        assert text == "Papa Mozhet"
        assert len(blocks) == TEST_NUM_BLOCKS
        assert blocks[0]["text"] == "Papa"
        assert blocks[0]["confidence"] == CONF_BIG_THRESHOLD

        exp_bbox_0_norm = [10 / 400, 10 / 300, 50 / 400, 30 / 300]
        assert blocks[0]["bbox"][0] == exp_bbox_0_norm[0]
        assert blocks[0]["bbox"][1] == exp_bbox_0_norm[1]
        assert blocks[0]["bbox"][2] == exp_bbox_0_norm[2]
        assert blocks[0]["bbox"][3] == exp_bbox_0_norm[3]

    @patch("ml_models.ocr_model.get_ocr_reader")
    def test_extract_text_and_blocks_empty_result(self, mock_get_reader):
        mock_creative = MagicMock()
        mock_creative.image_width = 400
        mock_creative.image_height = 300

        mock_reader = MagicMock()
        mock_get_reader.return_value = mock_reader
        mock_reader.readtext.return_value = []

        temp_path = "temp_path.jpg"
        text, blocks = extract_text_and_blocks(temp_path, creative=mock_creative)

        assert text == ""
        assert blocks == []

    @patch("ml_models.ocr_model.get_ocr_reader")
    def test_extract_text_and_blocks_exception_handling(self, mock_get_reader):
        mock_creative = MagicMock()
        mock_creative.image_width = 400
        mock_creative.image_height = 300

        mock_reader = MagicMock()
        mock_get_reader.return_value = mock_reader
        # Имитация исключение
        mock_reader.readtext.side_effect = Exception("Mock OCR Error")

        temp_path = "temp_path.jpg"
        with pytest.raises(Exception, match="Mock OCR Error") as exc:
            extract_text_and_blocks(temp_path, creative=mock_creative)

        assert "Mock OCR Error" in str(exc.value)


if __name__ == "__main__":
    unittest.main()
