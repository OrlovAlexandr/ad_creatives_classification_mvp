import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_SECURE: bool = False
    MINIO_BUCKET: str = "creatives"
    BACKEND_CORS_ORIGINS: list = ["http://localhost:8501"]
    REDIS_URL: str

    class Config:
        env_file = ".env"

settings = Settings()

# Константы для тематик
TOPICS = ['tableware', 'ties', 'bags', 'cups', 'clocks']

TOPIC_TRANSLATIONS = {
    'tableware': 'Ст. приборы',
    'ties': 'Галстуки',
    'bags': 'Сумки',
    'cups': 'Чашки',
    'clocks': 'Часы'
}

TOPIC_TEXTS = {
    'tableware': 'НАБОР ИЗ НЕРЖАВЕЙКИ. ПОСУДА ДЛЯ КУХНИ. 10 ПРЕДМЕТОВ',
    'ties': 'ШЕЛКОВЫЙ ГАЛСТУК. КЛАССИКА. ПОДАРОК МУЖЧИНЕ',
    'bags': 'ЛЕДИ-СУМКА 2025. КОЖА, ЗАСТЕЖКА, ВМЕСТИТЕЛЬНО',
    'cups': 'ФИРМЕННАЯ КЕРАМИКА. ПОДАРОК К ПРАЗДНИКУ. НЕ ТЕРЯЕТ ЦВЕТ',
    'clocks': 'SMART WATCH 8 СЕРИИ. ДОПУСК УВЕДОМЛЕНИЙ. МОЩНАЯ БАТАРЕЯ'
}

COCO_CLASSES = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat",
    "traffic light", "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat",
    "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe", "backpack",
    "umbrella", "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard", "sports ball",
    "kite", "baseball bat", "baseball glove", "skateboard", "surfboard", "tennis racket",
    "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana", "apple",
    "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake",
    "chair", "couch", "potted plant", "bed", "dining table", "toilet", "tv", "laptop",
    "mouse", "remote", "keyboard", "cell phone", "microwave", "oven", "toaster", "sink",
    "refrigerator", "book", "clock", "vase", "scissors", "teddy bear", "hair drier", "toothbrush"
]

# Константы для цветового анализа
DOMINANT_COLORS_COUNT = 3
SECONDARY_COLORS_COUNT = 3

PALETTE_HEX = [
    "ff0000", "ff8080", "800000", "804040",
    "ff8000", "ffbf80", "804000", "806040",
    "ffff00", "ffff80", "808000", "808040",
    "80ff00", "bfff80", "408000", "608040",
    "00ff00", "80ff80", "008000", "408040",
    "00ff80", "80ffbf", "008040", "408060",
    "00ffff", "80ffff", "008080", "408080",
    "0080ff", "80bfff", "004080", "406080",
    "0000ff", "8080ff", "000080", "404080",
    "8000ff", "bf80ff", "400080", "604080",
    "ff00ff", "ff80ff", "800080", "804080",
    "ff0080", "ff80bf", "800040", "804060",
    "000000",
    "404040",
    "808080",
    "bfbfbf",
    "ffffff" 
]

MONOCHROME_HEX_SET = {"000000", "404040", "808080", "bfbfbf", "ffffff"}

COLOR_CLASSES = {
    "Красный": {"ff0000", "ff8080", "800000"},
    "Коричневый": {"804040", "804000", "806040"},
    "Розовый": {"ff80ff", "ff0080", "ff80bf"},
    "Оранжевый": {"ff8000", "ffbf80"},
    "Желтый": {"ffff00", "ffff80", "808040", "808000"},
    "Зеленый": {"80ff00", "bfff80", "408000", "608040", "00ff00", "80ff80", "008000", "408040", "00ff80", "80ffbf", "008040", "408060"},
    "Голубой": {"00ffff", "80ffff", "80bfff"},
    "Темно-голубой": {"008080", "408080"},
    "Синий": {"0080ff", "004080", "406080", "0000ff", "000080"},
    "Фиолетовый": {"8080ff", "404080", "8000ff", "bf80ff", "400080", "604080"},
    "Маджента": {"ff00ff"},
    "Сиреневый": {"800080", "804080", "800040", "804060"},
    "Черный": {"000000"},
    "Темно-серый": {"404040"},
    "Серый": {"808080"},
    "Светло-серый": {"bfbfbf"},
    "Белый": {"ffffff"}
}

COLOR_VISUAL_CLASSES = {
    "Красный": {"bc0e0e"},
    "Коричневый": {"663300"},
    "Розовый": {"ff0080"},
    "Оранжевый": {"f27900"},
    "Желтый": {"f2f20c"},
    "Зеленый": {"009900"},
    "Голубой": {"29cccc"},
    "Темно-голубой": {"008080"},
    "Синий": {"0a4bcc"},
    "Фиолетовый": {"7e17e5"},
    "Маджента": {"ff00ff"},
    "Сиреневый": {"b300b3"},
    "Черный": {"000000"},
    "Темно-серый": {"404040"},
    "Серый": {"808080"},
    "Светло-серый": {"bfbfbf"},
    "Белый": {"f7f7f7"}
}
