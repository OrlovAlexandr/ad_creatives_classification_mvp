import logging
from contextlib import asynccontextmanager

from database import Base
from database import SessionLocal
from database import engine
from database_models.app_settings import AppSettings
from fastapi import FastAPI
from minio_client import minio_client
from minio_client import settings
from sqlalchemy.orm import Session


logger = logging.getLogger(__name__)
from config import DOMINANT_COLORS_COUNT
from config import SECONDARY_COLORS_COUNT


def initialize_default_settings(db: Session):
    default_settings = [
        {
            "key": "DOMINANT_COLORS_COUNT",
            "value": str(DOMINANT_COLORS_COUNT),
            "description": "Количество доминирующих цветов",
            },
        {
            "key": "SECONDARY_COLORS_COUNT",
            "value": str(SECONDARY_COLORS_COUNT),
            "description": "Количество второстепенных цветов",
            },
    ]

    for setting_data in default_settings:
        existing = db.query(AppSettings).filter(AppSettings.key == setting_data["key"]).first()
        if not existing:
            logger.info(f"Инициализация настройки: {setting_data['key']} = {setting_data['value']}")
            db.add(AppSettings(**setting_data))
    db.commit()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Запуск lifespan: создание таблиц БД и инициализация настроек...")
    Base.metadata.create_all(bind=engine)
    logger.info("Таблицы БД созданы (если не существовали).")

    db = SessionLocal()
    try:
        initialize_default_settings(db)
    finally:
        db.close()

    bucket = settings.MINIO_BUCKET
    if not minio_client.bucket_exists(bucket):
        logger.info(f"Создание бакета MinIO: {bucket}")
        minio_client.make_bucket(bucket)
    logger.info("Инициализация завершена.")
    yield
    logger.info("Приложение завершает работу.")
