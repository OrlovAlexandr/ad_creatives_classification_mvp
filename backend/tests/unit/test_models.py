import unittest

from database_models.creative import Base, Creative, CreativeAnalysis
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


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
            image_width=800,
            image_height=600,
        )
        self.db.add(creative)
        self.db.commit()
        self.db.refresh(creative)

        retrieved = (
            self.db.query(Creative)
            .filter(Creative.creative_id == "test_id_123")
            .first()
        )
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.original_filename, "test.jpg")
        self.assertEqual(retrieved.image_width, 800)

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
            topic_confidence=0.95,
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
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.main_topic, "Часы")
        self.assertEqual(retrieved.topic_confidence, 0.95)
        self.assertEqual(retrieved.overall_status, "SUCCESS")


if __name__ == "__main__":
    unittest.main()
