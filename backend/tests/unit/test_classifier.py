import unittest
from unittest.mock import MagicMock
from unittest.mock import patch

import numpy as np
import torch
from config import NUM_LABELS
from ml_models.classifier import classify_creative
from ml_models.classifier import get_bert_model_and_tokenizer
from ml_models.preprocessing import NUM_COCO


class TestClassifier(unittest.TestCase):
    @patch("ml_models.classifier.settings")
    @patch("ml_models.classifier.AutoTokenizer")
    @patch("ml_models.classifier.torch.load")
    @patch("ml_models.classifier.pathlib.Path.exists")
    @patch("ml_models.classifier.MultiModalBertClassifier")
    def test_get_bert_model_and_tokenizer_success(
        self,
        mock_model_class,
        mock_path_exists,
        mock_torch_load,
        mock_auto_tokenizer,
        mock_settings,
    ):
        # Настройка моков
        mock_settings.MODEL_CACHE_DIR = "/fake/cache/dir"
        mock_settings.BERT_MODEL_PATH = "fake_model.pt"
        mock_settings.BERT_TOKENIZER_NAME = "fake-tokenizer"
        mock_settings.DEVICE = "cpu"
        mock_settings.NUM_COCO = NUM_COCO
        mock_settings.NUM_LABELS = NUM_LABELS

        mock_path_exists.return_value = True

        mock_tokenizer = MagicMock()
        mock_auto_tokenizer.from_pretrained.return_value = mock_tokenizer

        # Имитация загрузки state_dict
        mock_state_dict = {"fake_key": "fake_value"}
        mock_torch_load.return_value = mock_state_dict

        # MultiModalBertClassifier имитация
        mock_model_instance = MagicMock()
        mock_model_class.return_value = mock_model_instance

        model, tokenizer = get_bert_model_and_tokenizer()

        # Проверяем вызовы
        mock_auto_tokenizer.from_pretrained.assert_called_once_with("fake-tokenizer")
        mock_path_exists.assert_called_once()
        mock_torch_load.assert_called_once()
        mock_model_class.assert_called_once_with(
            model_name="fake-tokenizer",
            num_numeric_features=NUM_COCO,
            num_labels=NUM_LABELS,
            dropout=0.3,
            hidden_dim=256,
        )
        mock_model_instance.load_state_dict.assert_called_once_with(mock_state_dict)
        mock_model_instance.to.assert_called()
        mock_model_instance.eval.assert_called_once()

        assert model == mock_model_instance
        assert tokenizer == mock_tokenizer

    @patch("ml_models.classifier.get_bert_model_and_tokenizer")  # Мокаем методы
    @patch("ml_models.classifier.clean_text_for_bert")
    @patch("ml_models.classifier.yolo_to_vector_for_bert")
    def test_classify_creative_success(
        self, mock_yolo_to_vec, mock_clean_text, mock_get_model_tokenizer,
    ):
        mock_model = MagicMock(name="MockModel")
        mock_tokenizer = MagicMock(name="MockTokenizer")

        mock_logits = torch.tensor([[0.1, 0.9, 0.2, 0.3, 0.4]])  # 5 классов
        mock_model_output = {"logits": mock_logits}

        # Настраиваем mock_model и forward
        mock_model.return_value = mock_model_output
        mock_model.forward.return_value = mock_model_output

        mock_get_model_tokenizer.return_value = (mock_model, mock_tokenizer)

        # clean_text имитация
        mock_clean_text.return_value = "cleaned ocr text"

        # yolo имитация
        fake_yolo_vector = np.array([0.1, 0.2, 0.3] + [0.0] * (NUM_COCO - 3))
        mock_yolo_to_vec.return_value = fake_yolo_vector

        # Имитируем tokenizer
        mock_encoding = {
            "input_ids": torch.tensor(
                [[101, 2023, 2003, 1037, 13997, 11510, 1012, 102]],
            ),
            "attention_mask": torch.tensor([[1, 1, 1, 1, 1, 1, 1, 1]]),
        }
        mock_tokenizer.return_value = mock_encoding

        ocr_text = "smart watch 8 series"
        detected_objects = [{"class": "clock", "confidence": 0.9}]

        main_topic, confidence = classify_creative(ocr_text, detected_objects)

        mock_get_model_tokenizer.assert_called_once()
        mock_clean_text.assert_called_once_with(ocr_text)
        mock_yolo_to_vec.assert_called_once_with(["clock"], [0.9])
        mock_model.forward.assert_called()

        exp_topic = "cups"
        assert main_topic == exp_topic
        assert isinstance(confidence, float)
        assert confidence >= 0.0
        assert confidence <= 1.0

    @patch("ml_models.classifier.get_bert_model_and_tokenizer")
    def test_classify_creative_model_exception(self, mock_get_model_tokenizer):
        mock_get_model_tokenizer.side_effect = Exception("Model Load Error")

        ocr_text = "test"
        detected_objects = []

        main_topic, confidence = classify_creative(ocr_text, detected_objects)

        assert main_topic is None
        assert confidence == 0.0
        mock_get_model_tokenizer.assert_called_once()


if __name__ == "__main__":
    unittest.main()
