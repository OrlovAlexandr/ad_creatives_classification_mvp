import datetime

from sqlalchemy import create_engine, Column, Integer, String, DateTime, JSON, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from config import DATABASE_URL

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Creative(Base):
    __tablename__ = "creatives"

    creative_id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, index=True)
    original_filename = Column(String)
    file_path = Column(String)
    upload_timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    file_size = Column(Integer)
    file_format = Column(String)
    image_width = Column(Integer)
    image_height = Column(Integer)


class CreativeAnalysis(Base):
    __tablename__ = "creative_analysis"

    analysis_id = Column(Integer, primary_key=True, index=True)
    creative_id = Column(Integer, ForeignKey("creatives.creative_id"))
    dominant_colors = Column(JSON)
    secondary_colors = Column(JSON)
    ocr_text = Column(Text)
    ocr_blocks = Column(JSON)
    text_topics = Column(JSON)
    detected_objects = Column(JSON)
    visual_topics = Column(JSON)
    main_topic = Column(String)
    analysis_timestamp = Column(DateTime)
    analysis_status = Column(String, default="PENDING")
    error_message = Column(Text)


# Создание таблиц
Base.metadata.create_all(bind=engine)
