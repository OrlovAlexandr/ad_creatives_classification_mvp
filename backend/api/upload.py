from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from services.upload_service import create_creative
from models import UploadResponse
import logging
import os
import shutil
from PIL import Image
from utils.minio_utils import upload_to_minio
from typing import List
from tasks import process_creative


logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/upload", response_model=UploadResponse)
async def upload_files(
    files: List[UploadFile] = File(...),
    group_id: str = Form(...),
    creative_ids: List[str] = Form(...),
    original_filenames: List[str] = Form(...),
    db: Session = Depends(get_db)
):
    logger.info(f"Получено: group_id={group_id}, creative_ids={creative_ids}")

    # Валидация
    if len(files) != len(creative_ids) or len(files) != len(original_filenames):
        raise HTTPException(
            status_code=400,
            detail="Количество файлов, creative_ids и original_filenames не совпадает"
        )

    uploaded = 0
    errors = []
    temp_dir = "uploads"
    os.makedirs(temp_dir, exist_ok=True)

    for file, creative_id, orig_filename in zip(files, creative_ids, original_filenames):
        temp_file_path = None
        try:
            # Проверка формата
            ext = file.filename.split(".")[-1].lower()
            if ext not in ["jpg", "jpeg", "png", "webp"]:
                errors.append(f"{orig_filename}: неподдерживаемый формат")
                continue

            # Сохранение временного файла
            temp_file_path = os.path.join(temp_dir, f"{creative_id}.{ext}")
            with open(temp_file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            # Получение метаданных
            with Image.open(temp_file_path) as img:
                width, height = img.size

            file_size = os.path.getsize(temp_file_path)

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
                image_height=height
            )

            process_creative.delay(creative_id)

            uploaded += 1

        except Exception as e:
            logger.error(f"Ошибка при обработке {orig_filename}: {e}")
            errors.append(f"{orig_filename}: {str(e)}")
        finally:
            # Удаление временного файла
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except Exception as cleanup_error:
                    logger.warning(f"Не удалось удалить временный файл {temp_file_path}: {cleanup_error}")

    return UploadResponse(uploaded=uploaded, group_id=group_id, errors=errors)
