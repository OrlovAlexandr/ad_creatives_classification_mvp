from datetime import datetime

from sqlalchemy import create_engine, Column, Integer, String, DateTime, JSON, Text, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from config import DATABASE_URL

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Creative(Base):
    __tablename__ = "creatives"

    creative_id = Column(String, primary_key=True, index=True)
    group_id = Column(String, index=True)
    original_filename = Column(String)
    file_path = Column(String)
    upload_timestamp = Column(DateTime, default=datetime.utcnow)
    file_size = Column(Integer)
    file_format = Column(String)
    image_width = Column(Integer)
    image_height = Column(Integer)


class CreativeAnalysis(Base):
    __tablename__ = "creative_analysis"

    analysis_id = Column(Integer, primary_key=True, index=True)
    creative_id = Column(String, ForeignKey("creatives.creative_id"), nullable=False)
    # OCR результаты
    ocr_text = Column(Text)
    ocr_blocks = Column(JSON)
    # YOLO результаты
    detected_objects = Column(JSON)
    # Предсказание таргета
    main_topic = Column(String)
    topic_confidence = Column(Float)
    # Определени доминантного цвета
    dominant_colors = Column(JSON)
    secondary_colors = Column(JSON)
    palette_colors = Column(JSON)

    # Статусы этапов
    ocr_status = Column(String, default="PENDING")
    detection_status = Column(String, default="PENDING")
    classification_status = Column(String, default="PENDING")
    color_analysis_status = Column(String, default="PENDING")
    overall_status = Column(String, default="PENDING")  # PENDING, PROCESSING, SUCCESS, ERROR

    # Временные метки этапов
    ocr_started_at = Column(DateTime)
    ocr_completed_at = Column(DateTime)
    detection_started_at = Column(DateTime)
    detection_completed_at = Column(DateTime)
    classification_started_at = Column(DateTime)
    classification_completed_at = Column(DateTime)
    color_analysis_started_at = Column(DateTime)
    color_analysis_completed_at = Column(DateTime)
    analysis_timestamp = Column(DateTime)

    # Время выполнения
    ocr_duration = Column(Float)
    detection_duration = Column(Float)
    classification_duration = Column(Float)
    color_analysis_duration = Column(Float)
    total_duration = Column(Float)

    error_message = Column(Text)
