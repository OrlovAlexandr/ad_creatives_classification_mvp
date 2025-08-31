import logging
import shutil
from pathlib import Path

from database import get_db
from fastapi import APIRouter
from fastapi import Depends
from fastapi import File
from fastapi import Form
from fastapi import HTTPException
from fastapi import UploadFile
from models import UploadResponse
from PIL import Image
from services.upload_service import create_creative
from sqlalchemy.orm import Session
from tasks import process_creative
from utils.minio_utils import upload_to_minio


logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_files(
        files: list[UploadFile] = File(...),
        group_id: str = Form(...),
        creative_ids: list[str] = Form(...),
        original_filenames: list[str] = Form(...),
        db: Session = Depends(get_db),
):
    logger.info(f"Получено: group_id={group_id}, creative_ids={creative_ids}")

    # Валидация
    if len(files) != len(creative_ids) or len(files) != len(original_filenames):
        raise HTTPException(
            status_code=400,
            detail="Количество файлов, creative_ids и original_filenames не совпадает",
        )

    uploaded = 0
    errors = []
    temp_dir = Path("uploads")
    temp_dir.mkdir(parents=True, exist_ok=True)

    for file, creative_id, orig_filename in zip(files, creative_ids, original_filenames, strict=False):
        temp_file_path = None
        try:
            # Проверка формата
            ext = file.filename.split(".")[-1].lower()
            if ext not in ["jpg", "jpeg", "png", "webp"]:
                errors.append(f"{orig_filename}: неподдерживаемый формат")
                continue

            # Сохранение временного файла
            temp_file_path = temp_dir / f"{creative_id}.{ext}"
            with temp_file_path.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            # Получение метаданных
            with Image.open(temp_file_path) as img:
                width, height = img.size

            file_size = temp_file_path.stat().st_size

            # Загрузка в MinIO
            object_name = f"{creative_id}.{ext}"
            minio_path = upload_to_minio(temp_file_path, object_name)

            # Сохранение в БД
            create_creative(
                db=db,
                creative_id=creative_id,
                group_id=group_id,
                original_filename=orig_filename,
                minio_path=minio_path,
                file_size=file_size,
                file_format=ext,
                image_width=width,
                image_height=height,
            )

            process_creative.delay(creative_id)

            uploaded += 1

        except Exception as e:
            logger.exception(f"Ошибка при обработке {orig_filename}")
            errors.append(f"{orig_filename}: {e!s}")
        finally:
            # Удаление временного файла
            if temp_file_path and temp_file_path.exists():
                try:
                    temp_file_path.unlink()
                except OSError as e:
                    logger.exception(f"Не удалось удалить временный файл {orig_filename}")
                    errors.append(f"{orig_filename}: {e!s}")

    return UploadResponse(uploaded=uploaded, group_id=group_id, errors=errors)
