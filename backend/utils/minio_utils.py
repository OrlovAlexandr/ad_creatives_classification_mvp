import logging
from pathlib import Path

from config import settings
from minio.error import S3Error
from minio_client import minio_client


logger = logging.getLogger(__name__)


class FileNotSavedException(Exception):
    message = "Файл не был сохранён локально"


def _raise_file_not_saved_exception(temp_local_path: str) -> None:
    raise FileNotSavedException(temp_local_path)


def upload_to_minio(file_path: str, object_name: str) -> str:
    try:
        # Проверяем существование бакета
        if not minio_client.bucket_exists(settings.MINIO_BUCKET):
            minio_client.make_bucket(settings.MINIO_BUCKET)

        minio_client.fput_object(settings.MINIO_BUCKET, object_name, file_path)
    except S3Error:
        logger.exception("Ошибка MinIO при загрузке")
        raise
    except Exception:
        logger.exception("Неожиданная ошибка при загрузке в MinIO")
        raise
    else:
        return f"{settings.MINIO_BUCKET}/{object_name}"


def download_file_from_minio(creative, analysis, db, temp_local_path: str):
    """Скачивает файл креатива из MinIO."""
    try:
        temp_local_path = Path(temp_local_path)
        object_name = f"{creative.creative_id}.{creative.file_format}"

        temp_local_path.parent.mkdir(parents=True, exist_ok=True)
        response = minio_client.get_object(settings.MINIO_BUCKET, object_name)
        with temp_local_path.open("wb") as f:
            f.write(response.read())
        if not temp_local_path.exists():
            _raise_file_not_saved_exception(str(temp_local_path))
        logger.info(f"Изображение {creative.creative_id} успешно загружено из MinIO")
    except S3Error:
        logger.exception(f"Ошибка MinIO при загрузке {creative.creative_id}")
        analysis.overall_status = "ERROR"
        analysis.error_message = "Не удалось загрузить изображение из MinIO"
        db.commit()
    except Exception as e:
        logger.exception(
            f"Ошибка загрузки изображения из MinIO для {creative.creative_id}: {type(e).__name__}",
        )
        analysis.overall_status = "ERROR"
        analysis.error_message = "Не удалось загрузить изображение из MinIO"
        db.commit()
    else:
        return True

    if temp_local_path.exists():
        try:
            temp_local_path.unlink()
            logger.info(f"Удален повреждённый временный файл {temp_local_path}")
        except Exception:
            logger.exception(f"Ошибка при удалении временного файла {temp_local_path}")
            raise

    return False
