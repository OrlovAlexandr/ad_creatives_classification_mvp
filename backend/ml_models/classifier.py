from datetime import datetime
import random
import time
import os

from config import settings, TOPICS, NUM_COCO, NUM_LABELS
from ml_models.preprocessing import clean_text_for_bert, yolo_to_vector_for_bert
import logging

from transformers import AutoModel
from transformers import AutoTokenizer
import torch
from torch import nn

from icecream import ic

logger = logging.getLogger(__name__)


class MultiModalBertClassifier(nn.Module):
    def __init__(self, model_name, num_numeric_features, num_labels, dropout=0.3, hidden_dim=256):
        super().__init__()
        self.bert = AutoModel.from_pretrained(model_name)
        hid = self.bert.config.hidden_size
        self.dropout = nn.Dropout(dropout)
        self.fc1 = nn.Linear(hid + num_numeric_features, hidden_dim)
        self.act = nn.ReLU()
        self.fc2 = nn.Linear(hidden_dim, num_labels)

    def forward(self, input_ids, attention_mask, yolo_vec, labels=None):
        # Получаем эмбеддинг 
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        # лучше mean-pooling по токенам:
        last_hidden = outputs.last_hidden_state  
        mask = attention_mask.unsqueeze(-1)     
        summed = torch.sum(last_hidden * mask, dim=1)      
        counts = torch.clamp(mask.sum(dim=1), min=1e-9)      
        text_vec = summed / counts                           

        x = torch.cat([text_vec, yolo_vec], dim=1)
        x = self.dropout(self.act(self.fc1(x)))
        logits = self.fc2(x)
        loss = None
        if labels is not None:
            loss = nn.CrossEntropyLoss()(logits, labels)
        return {'loss': loss, 'logits': logits}


# --- Глобальные переменные для модели и токенизатора (кеширование) ---
_bert_model = None
_bert_tokenizer = None

def get_bert_model_and_tokenizer():
    global _bert_model, _bert_tokenizer
    if _bert_model is None or _bert_tokenizer is None:
        ic("Загрузка модели BERT и токенизатора")
        try:
            tokenizer_name = settings.BERT_TOKENIZER_NAME
            logger.info(f"Загрузка токенизатора: {tokenizer_name}")
            _bert_tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)
            ic("Токенизатор загружен:")
            
            model_path = os.path.join(settings.MODEL_CACHE_DIR, settings.BERT_MODEL_PATH)
            if not os.path.exists(model_path):
                logger.error(f"Модель BERT не найдена по пути {model_path}")
                raise FileNotFoundError(f"BERT model not found at {model_path}")

            device = torch.device(settings.DEVICE)
            logger.info(f"Загрузка весов модели BERT с устройства: {device}")
            
            vocab_size = _bert_tokenizer.vocab_size
            yolo_vec_size = NUM_COCO
            num_labels = NUM_LABELS
            
            _bert_model = MultiModalBertClassifier(
                model_name=tokenizer_name,
                num_numeric_features=yolo_vec_size,
                num_labels=num_labels,
                dropout=0.3,
                hidden_dim=256
            )
            ic("Модель BERT инициализирована:")
            
            checkpoint = torch.load(model_path, map_location=device)

            _bert_model.load_state_dict(checkpoint) 
            _bert_model.to(device)
            _bert_model.eval()
            logger.info("Модель BERT и токенизатор успешно загружены и находятся в режиме eval.")
            ic("Модель BERT и токенизатор успешно загружены.")
        except Exception as e:
            logger.error(f"Ошибка при инициализации или загрузке весов модели BERT: {e}")
            raise
    return _bert_model, _bert_tokenizer

def classify_creative(ocr_text: str, detected_objects: list) -> tuple[str, float]:
    ic("Классификация креатива...")
    try:
        logger.info("Начало классификации креатива.")
        model, tokenizer = get_bert_model_and_tokenizer()

        logger.debug("Шаг 1: Предобработка текста OCR.")
        cleaned_ocr_text = clean_text_for_bert(ocr_text)
        logger.debug(f"Очищенный текст OCR: {cleaned_ocr_text}")

        logger.debug("Шаг 2: Извлечение классов и уверенности из YOLO.")
        yolo_classes = [obj['class'] for obj in detected_objects]
        yolo_confs = [obj['confidence'] for obj in detected_objects]
        logger.debug(f"Классы YOLO: {yolo_classes}")
        logger.debug(f"Уверенности YOLO: {yolo_confs}")

        logger.debug("Шаг 3: Преобразование YOLO в вектор.")
        yolo_vector = yolo_to_vector_for_bert(yolo_classes, yolo_confs)
        logger.debug(f"Вектор YOLO (первые 10 элементов): {yolo_vector[:10]}")

        logger.debug("Шаг 4: Токенизация текста.")

        encoding = tokenizer(
            cleaned_ocr_text,
            return_tensors='pt',
            padding='max_length',
            truncation=True,
            max_length=160
        )
        input_ids = encoding['input_ids']
        attention_mask = encoding['attention_mask']

        yolo_vec = torch.tensor(yolo_vector, dtype=torch.float32).unsqueeze(0) 

        device = torch.device(settings.DEVICE)
        input_ids = input_ids.to(device)
        attention_mask = attention_mask.to(device)
        yolo_vec = yolo_vec.to(device)

        logger.debug("Шаг 5: Выполнение предсказания моделью.")
        with torch.no_grad():
            outputs = model(input_ids=input_ids, attention_mask=attention_mask, yolo_vec=yolo_vec)

            logits = outputs['logits']
            probabilities = torch.softmax(logits, dim=1)
            predicted_class_id = torch.argmax(probabilities, dim=1).item()
            confidence = probabilities[0][predicted_class_id].item()

        id_to_topic = {0: 'ties', 1: 'cups', 2: 'cutlery', 3: 'bags', 4: 'clocks'}
        main_topic_name = id_to_topic.get(predicted_class_id, "unknown")
        
        logger.info(f"Классификация завершена. Предсказанная тема: {main_topic_name}, Уверенность: {confidence:.4f}")
        return main_topic_name, confidence 

    except Exception as e:
        logger.error(f"Ошибка при классификации креатива: {e}", exc_info=True)
        return None, 0.0

# Пример использования (для тестирования модуля отдельно)
# if __name__ == "__main__":
#     # Пример данных
#     test_ocr_text = "SMART WATCH 8 СЕРИИ. ДОПУСК УВЕДОМЛЕНИЙ. МОЩНАЯ БАТАРЕЯ"
#     test_detected_objects = [
#         {"class": "clock", "confidence": 0.85},
#         {"class": "cell phone", "confidence": 0.45}
#     ]
#     
#     # Убедитесь, что MODEL_CACHE_DIR и BERT_MODEL_PATH установлены в settings
#     # и модель находится по этому пути
#     topic, conf = classify_creative(test_ocr_text, test_detected_objects)
#     print(f"Предсказанная тема: {topic}, Уверенность: {conf}")


# def perform_classification(
#         creative_id: str, 
#         analysis, 
#         db,
#         ):
#     """Выполняет классификацию."""
#     logger.info(f"[{creative_id}] Начало классификации...")
#     analysis.classification_status = "PROCESSING"
#     analysis.classification_started_at = datetime.utcnow()
#     db.commit() # Коммитим статус PROCESSING

#     try:
#         # Имитация классификации
#         time.sleep(random.uniform(0.5, 3.0))
#         topic = random.choice(TOPICS)
#         analysis.topic = topic

#         topic_confidence = round(random.uniform(0.6, 0.95), 2)
#         analysis.main_topic = topic
#         analysis.topic_confidence = topic_confidence
#         analysis.classification_status = "SUCCESS"

#         analysis.classification_сompleted_at = datetime.utcnow()
#         analysis.classification_duration = (
#             analysis.classification_сompleted_at - analysis.classification_started_at
#             ).total_seconds()
#         db.commit()
#     except Exception as e:
#         logger.error(f"[{creative_id}] Ошибка в классификации: {str(e)}")
#         analysis.classification_status = "ERROR"
#         analysis.classification_сompleted_at = datetime.utcnow()
#         analysis.classification_duration = (
#             analysis.classification_сompleted_at - analysis.classification_started_at
#             ).total_seconds()
#         db.commit()
#         raise