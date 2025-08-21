from minio.error import S3Error
from minio_client import minio_client
from config import settings
import logging

logger = logging.getLogger(__name__)

def upload_to_minio(file_path: str, object_name: str) -> str:
    try:
        # Проверяем существование бакета
        if not minio_client.bucket_exists(settings.MINIO_BUCKET):
            minio_client.make_bucket(settings.MINIO_BUCKET)
            
        minio_client.fput_object(settings.MINIO_BUCKET, object_name, file_path)
        return f"{settings.MINIO_BUCKET}/{object_name}"
    except S3Error as e:
        logger.error(f"Ошибка MinIO при загрузке: {e}")
        raise
    except Exception as e:
        logger.error(f"Неожиданная ошибка при загрузке в MinIO: {e}")
        raise