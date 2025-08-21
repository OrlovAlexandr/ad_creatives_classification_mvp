from contextlib import asynccontextmanager
from fastapi import FastAPI
from database import Base, engine
from minio_client import minio_client, settings
# from core.lifespan import lifespan
# from api import groups, status, analytics, creatives, upload
from api import router
import logging
import time
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Запуск lifespan: создание таблиц БД...")
    Base.metadata.create_all(bind=engine)
    logger.info("Таблицы БД созданы (если не существовали).")

    bucket = settings.MINIO_BUCKET
    if not minio_client.bucket_exists(bucket):
        logger.info(f"Создание бакета MinIO: {bucket}")
        minio_client.make_bucket(bucket)
    logger.info("Инициализация завершена.")
    yield
    logger.info("Приложение завершает работу.")

app = FastAPI(title="Creative Classification API", lifespan=lifespan)

logger.info("Подключение роутеров...")

app.include_router(router)

logger.info("Роутеры подключены. Список маршрутов:")
for route in app.routes:
    if hasattr(route, "path"):
        method = getattr(route, "methods", "UNKNOWN")
        logger.info(f"  {method} {route.path} → {route.name}")

# @app.get("/")
# def root():
#     return {"message": "Creative Classification Backend"}
