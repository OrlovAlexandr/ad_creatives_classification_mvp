from contextlib import asynccontextmanager
from fastapi import FastAPI
from database import Base, engine
from minio_client import minio_client, settings
from database_models.creative import Creative, CreativeAnalysis

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Создание таблиц
    Base.metadata.create_all(bind=engine)
    
    # Проверка/создание бакета MinIO
    # bucket = settings.MINIO_BUCKET
    # if not minio_client.bucket_exists(bucket):
    #     minio_client.make_bucket(bucket)
    
    yield