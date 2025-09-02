import unittest
from unittest.mock import MagicMock, patch

from ml_models.ocr_model import extract_text_and_blocks


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
            ([[10, 10], [50, 10], [50, 30], [10, 30]], "Papa", 0.9),
            ([[60, 60], [100, 60], [100, 80], [60, 80]], "Mozhet", 0.8),
        ]
        mock_reader.readtext.return_value = mock_result

        # Файл-заглушка
        temp_path = "temp_path.jpg"
        text, blocks = extract_text_and_blocks(temp_path, creative=mock_creative)

        self.assertEqual(text, "Papa Mozhet")
        self.assertEqual(len(blocks), 2)
        self.assertEqual(blocks[0]["text"], "Papa")
        self.assertEqual(blocks[0]["confidence"], 0.9)

        exp_bbox_0_norm = [10 / 400, 10 / 300, 50 / 400, 30 / 300]
        self.assertAlmostEqual(blocks[0]["bbox"][0], exp_bbox_0_norm[0], places=4)
        self.assertAlmostEqual(blocks[0]["bbox"][1], exp_bbox_0_norm[1], places=4)
        self.assertAlmostEqual(blocks[0]["bbox"][2], exp_bbox_0_norm[2], places=4)
        self.assertAlmostEqual(blocks[0]["bbox"][3], exp_bbox_0_norm[3], places=4)

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

        self.assertEqual(text, "")
        self.assertEqual(blocks, [])

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
        with self.assertRaises(Exception) as context:
            extract_text_and_blocks(temp_path, creative=mock_creative)

        self.assertIn("Mock OCR Error", str(context.exception))


if __name__ == "__main__":
    unittest.main()
