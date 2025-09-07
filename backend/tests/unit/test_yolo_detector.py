import unittest
from unittest.mock import MagicMock
from unittest.mock import patch

import numpy as np
import pytest
import torch
from ml_models.yolo_detector import detect_objects


CLOCK_THRESHOLD = 0.85
PERSON_THRESHOLD = 0.75
TEST_NUM_DETECTIONS = 2

class TestYoloDetector(unittest.TestCase):
    @patch("ml_models.yolo_detector.get_yolo_model")
    @patch("PIL.Image.open")
    def test_detect_objects_success(self, mock_pil_open, mock_get_model):
        mock_img = MagicMock()
        mock_img.size = (400, 400)
        mock_pil_open.return_value.__enter__.return_value = mock_img

        mock_model = MagicMock()
        mock_get_model.return_value = mock_model
        mock_model.names = {0: "person", 74: "clock"}

        # Mock для clock
        mock_box1 = MagicMock()
        mock_box1.cls = torch.tensor([74])
        mock_box1.conf = torch.tensor([CLOCK_THRESHOLD])
        mock_box1.xyxy = torch.tensor([[50.0, 50.0, 150.0, 150.0]])

        # Mock для person
        mock_box2 = MagicMock()
        mock_box2.cls = torch.tensor([0])
        mock_box2.conf = torch.tensor([PERSON_THRESHOLD])
        mock_box2.xyxy = torch.tensor([[200.0, 200.0, 300.0, 300.0]])

        # Имитация results[0].boxes
        mock_boxes_iterator = iter([mock_box1, mock_box2])
        mock_boxes_obj = MagicMock()
        mock_boxes_obj.__iter__ = lambda _: mock_boxes_iterator

        mock_results_obj = MagicMock()
        mock_results_obj.boxes = mock_boxes_obj

        # mock_model.predict для возврата results
        mock_model.predict.return_value = [mock_results_obj]

        temp_path = "temp_path.jpg"
        detections = detect_objects(temp_path, conf_threshold=0.35)

        mock_pil_open.assert_called_once_with(temp_path)
        mock_model.predict.assert_called_once()
        assert len(detections) == TEST_NUM_DETECTIONS

        assert detections[0]["class"] == "clock"
        assert round(detections[0]["confidence"], 6) == CLOCK_THRESHOLD
        expected_bbox_0 = [50.0 / 400, 50.0 / 400, 150.0 / 400, 150.0 / 400]
        np.testing.assert_allclose(detections[0]["bbox"], expected_bbox_0, atol=1e-5)

        assert detections[1]["class"] == "person"
        assert round(detections[1]["confidence"], 6) == PERSON_THRESHOLD
        expected_bbox_1 = [200.0 / 400, 200.0 / 400, 300.0 / 400, 300.0 / 400]
        np.testing.assert_allclose(detections[1]["bbox"], expected_bbox_1, atol=1e-5)

    @patch("ml_models.yolo_detector.get_yolo_model")
    @patch("PIL.Image.open")
    def test_detect_objects_no_detections(self, mock_pil_open, mock_get_model):
        mock_img = MagicMock()
        mock_img.size = (400, 400)
        mock_pil_open.return_value.__enter__.return_value = mock_img

        mock_model = MagicMock()
        mock_get_model.return_value = mock_model
        mock_model.names = {0: "person"}

        # Имитация отсутствия боксов
        mock_results_obj = MagicMock()
        mock_results_obj.boxes = None
        mock_model.predict.return_value = [mock_results_obj]

        temp_path = "temp_path_no_box.jpg"
        detections = detect_objects(temp_path, conf_threshold=0.35)

        mock_pil_open.assert_called_once_with(temp_path)
        mock_model.predict.assert_called_once()
        assert detections == []

    @patch("ml_models.yolo_detector.get_yolo_model")
    @patch("PIL.Image.open")
    def test_detect_objects_model_exception(self, mock_pil_open, mock_get_model):
        mock_img = MagicMock()
        mock_img.size = (400, 400)
        mock_pil_open.return_value.__enter__.return_value = mock_img

        mock_model = MagicMock()
        mock_get_model.return_value = mock_model
        # Имитируем исключение при predict
        mock_model.predict.side_effect = Exception("Mock YOLO Error")

        temp_path = "temp_path_error.jpg"
        with pytest.raises(Exception, match="Mock YOLO Error") as exc:
            detect_objects(temp_path)

        mock_pil_open.assert_called_once_with(temp_path)
        mock_model.predict.assert_called_once()  # должно быть True
        assert "Mock YOLO Error" in str(exc.value)


if __name__ == "__main__":
    unittest.main()
