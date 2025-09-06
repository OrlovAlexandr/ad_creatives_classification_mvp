import logging
import os
import sys
from pathlib import Path

import pytest
from database import Base
from database import get_db
from database_models.creative import CreativeAnalysis
from fastapi.testclient import TestClient
from main import app
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker


logger = logging.getLogger(__name__)

TOPIC_CONF_THRESHOLD = 0.95

project_root = Path(__file__).parent.parent

if project_root not in sys.path:
    sys.path.insert(0, str(project_root))
    logger.info(f"Корневая директория '{project_root}' добавлена в sys.path для тестирования")

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
if not TEST_DATABASE_URL:
    logger.warning("TEST_DATABASE_URL не найден. Используется sqlite:///./test_integration.db")
    TEST_DATABASE_URL = "sqlite:///./test_integration.db"

test_engine = create_engine(TEST_DATABASE_URL, echo=True)

@pytest.fixture(scope="session", autouse=True)
def _setup_test_database():
    """Создает и удаляет таблицы в тестовой БД перед запуском всех тестов."""
    logger.info("Creating tables...")
    Base.metadata.create_all(bind=test_engine)
    yield
    logger.info("Dropping tables...")
    Base.metadata.drop_all(bind=test_engine)

@pytest.fixture()
def db_session():
    """Создает и возвращает сессию тестовой БД."""
    test_session_local = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    db = test_session_local()
    try:
        yield db
    finally:
        db.rollback()
        db.close()

@pytest.fixture()
def override_get_db(db_session: Session):
    """Оверрайд для get_db для тестовой БД."""
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass
    return _override_get_db

@pytest.fixture()
def client(override_get_db):
    """Создает TestClient с подменой зависимости get_db."""
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture()
def test_group_id():
    """Фиксированный ID тестовой группы."""
    return "test_group_20240101_000000"

@pytest.fixture()
def create_test_creative(db_session: Session, test_group_id: str):
    """Создает тестовый креатив в БД."""
    from database_models.creative import Creative  # noqa: I001
    import uuid
    creative_id = str(uuid.uuid4())
    creative = Creative(
        creative_id=creative_id,
        group_id=test_group_id,
        original_filename="test_image.jpg",
        file_path=f"creatives/{creative_id}.jpg",
        file_size=1024,
        file_format="jpg",
        image_width=800,
        image_height=600,
    )
    db_session.add(creative)
    db_session.commit()
    db_session.refresh(creative)
    return creative

@pytest.fixture()
def create_test_analysis(db_session: Session, create_test_creative):
    """Создает тестовый анализ для креатива со статусом SUCCESS."""
    creative_id = create_test_creative.creative_id

    analysis = CreativeAnalysis(
        creative_id=creative_id,
        overall_status="SUCCESS",
        ocr_text="Sample OCR text for testing",
        main_topic="clocks",
        topic_confidence=TOPIC_CONF_THRESHOLD,
    )
    db_session.add(analysis)
    db_session.commit()
    db_session.refresh(analysis)

    yield analysis

    try:
        db_session.delete(analysis)
        db_session.commit()
    except Exception:
        db_session.rollback()
        logger.exception("Ошибка при удалении анализа.")
