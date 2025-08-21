from minio.error import S3Error
from minio_client import minio_client
from config import settings
import logging
import os

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
    
def download_file_from_minio(creative, analysis, db, temp_local_path: str):
    """Скачивает файл креатива из MinIO."""
    try:
        object_name = f"{creative.creative_id}.{creative.file_format}"
        # Убедитесь, что папка /tmp существует
        os.makedirs(os.path.dirname(temp_local_path), exist_ok=True)
        response = minio_client.get_object(settings.MINIO_BUCKET, object_name)
        with open(temp_local_path, "wb") as f:
            f.write(response.read())
        if not os.path.exists(temp_local_path):
            raise Exception("Файл не был сохранён локально")
        logger.info(f"Изображение {creative.creative_id} успешно загружено из MinIO")
        return True
    except S3Error as e:
        logger.error(f"Ошибка MinIO при загрузке {creative.creative_id}: {e}")
        analysis.overall_status = "ERROR"
        analysis.error_message = "Не удалось загрузить изображение из MinIO"
        db.commit()
    except Exception as e:
        logger.error(f"Ошибка загрузки изображения из MinIO для {creative.creative_id}: {e}")
        analysis.overall_status = "ERROR"
        analysis.error_message = "Не удалось загрузить изображение из MinIO"
        db.commit()
    
    if os.path.exists(temp_local_path):
        try:
            os.remove(temp_local_path)
            logger.info(f"Удален повреждённый временный файл {temp_local_path}")
        except Exception as e:
            logger.error(f"Ошибка при удалении временного файла {temp_local_path}: {e}")
            raise

    return False
