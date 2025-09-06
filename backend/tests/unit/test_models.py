import unittest

from database_models.creative import Base
from database_models.creative import Creative
from database_models.creative import CreativeAnalysis
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tests.conftest import TOPIC_CONF_THRESHOLD


TEST_IMAGE_WIDTH = 800
TEST_IMAGE_HEIGHT = 600

class TestDatabaseModels(unittest.TestCase):
    def setUp(self):
        # Создаем sqlite в памяти
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db = self.SessionLocal()

    def tearDown(self):
        self.db.close()

    def test_creative_creation(self):
        creative = Creative(
            creative_id="test_id_123",
            group_id="test_group_456",
            original_filename="test.jpg",
            file_path="creatives/test_id_123.jpg",
            file_size=1024,
            file_format="jpg",
            image_width=TEST_IMAGE_WIDTH,
            image_height=TEST_IMAGE_HEIGHT,
        )
        self.db.add(creative)
        self.db.commit()
        self.db.refresh(creative)

        retrieved = (
            self.db.query(Creative)
            .filter(Creative.creative_id == "test_id_123")
            .first()
        )
        assert retrieved is not None
        assert retrieved.original_filename == "test.jpg"
        assert retrieved.image_width == TEST_IMAGE_WIDTH
        assert retrieved.image_height == TEST_IMAGE_HEIGHT

    def test_creative_analysis_creation(self):
        # Сначала создаем Creative
        creative = Creative(
            creative_id="test_id_789",
            group_id="test_group_abc",
            original_filename="test2.png",
        )
        self.db.add(creative)
        self.db.commit()

        # Затем CreativeAnalysis
        analysis = CreativeAnalysis(
            creative_id="test_id_789",
            ocr_text="Sample OCR text",
            main_topic="Часы",
            topic_confidence=TOPIC_CONF_THRESHOLD,
            overall_status="SUCCESS",
        )
        self.db.add(analysis)
        self.db.commit()
        self.db.refresh(analysis)

        retrieved = (
            self.db.query(CreativeAnalysis)
            .filter(CreativeAnalysis.creative_id == "test_id_789")
            .first()
        )
        assert retrieved is not None
        assert retrieved.main_topic == "Часы"
        assert retrieved.topic_confidence == TOPIC_CONF_THRESHOLD
        assert retrieved.overall_status == "SUCCESS"


if __name__ == "__main__":
    unittest.main()
