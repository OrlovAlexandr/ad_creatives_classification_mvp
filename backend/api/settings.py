from fastapi import APIRouter, Depends, HTTPException
from database import get_db
from sqlalchemy.orm import Session
from services.settings_service import get_setting, update_setting, get_all_settings
from pydantic import BaseModel
from typing import Dict, Any, Optional
import logging
from database_models.app_settings import AppSettings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/settings", tags=["settings"])

class SettingUpdate(BaseModel):
    key: str
    value: Any

class SettingResponse(BaseModel):
    key: str
    value: Any
    description: Optional[str] = None

@router.get("/", response_model=Dict[str, Any])
def read_all_settings(db: Session = Depends(get_db)):
    logger.info("Запрос всех настроек")
    return get_all_settings(db)

@router.get("/{key}", response_model=SettingResponse)
def read_setting(key: str, db: Session = Depends(get_db)):
    logger.info(f"Запрос настройки: {key}")
    setting = db.query(AppSettings).filter(AppSettings.key == key).first()
    if not setting:
         raise HTTPException(status_code=404, detail=f"Настройка '{key}' не найдена")
    return SettingResponse(key=setting.key, value=setting.get_value(), description=setting.description)

@router.put("/{key}", response_model=SettingResponse)
def update_setting_endpoint(key: str, value: Any, db: Session = Depends(get_db)):
    logger.info(f"Обновление настройки {key} на {value}")
    setting_obj = db.query(AppSettings).filter(AppSettings.key == key).first()
    if not setting_obj:
         raise HTTPException(status_code=404, detail=f"Настройка '{key}' не найдена")
    
    old_value = setting_obj.value
    setting_obj.set_value(value)
    try:
        db.commit()
        db.refresh(setting_obj)
        logger.info(f"Настройка {key} обновлена с {old_value} на {setting_obj.value}")
    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка при обновлении настройки {key}: {e}")
        raise HTTPException(status_code=500, detail="Ошибка обновления настройки")
        
    return SettingResponse(key=setting_obj.key, value=setting_obj.get_value(), description=setting_obj.description)

@router.put("/", response_model=Dict[str, Any])
def update_settings_bulk(updates: dict, db: Session = Depends(get_db)):
    logger.info(f"Пакетное обновление настроек: {updates}")
    updated = {}
    try:
        for key, value in updates.items():
            setting_obj = db.query(AppSettings).filter(AppSettings.key == key).first()
            if setting_obj:
                setting_obj.set_value(value)
                updated[key] = setting_obj.get_value()
        db.commit()
        
        for key in updated:
            setting_obj = db.query(AppSettings).filter(AppSettings.key == key).first()
            updated[key] = setting_obj.get_value() if setting_obj else updated[key]
        logger.info("Пакетное обновление настроек завершено.")
        return updated
    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка при пакетном обновлении настроек: {e}")
        raise HTTPException(status_code=500, detail="Ошибка пакетного обновления настроек")
