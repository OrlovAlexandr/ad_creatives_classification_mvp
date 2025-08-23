from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from database_models.creative import Creative

router = APIRouter()

@router.get("/groups")
def get_groups(db: Session = Depends(get_db)):
    """Список групп креативов"""
    groups = db.query(Creative.group_id).distinct().all()
    result = []
    for (group_id,) in groups:
        # Количество креативов в группе
        count = db.query(Creative).filter(
            Creative.group_id == group_id
            ).count()

        # Первый креатив в группе (дата создания)
        first = db.query(Creative.upload_timestamp).filter(
            Creative.group_id == group_id).order_by(
            Creative.upload_timestamp).first()
        result.append({
            "group_id": group_id,
            "count": count,
            "created_at": first[0].isoformat() if first else None
        })

    result.sort(key=lambda x: x["created_at"] or "", reverse=True)  # Сортировка
    return result