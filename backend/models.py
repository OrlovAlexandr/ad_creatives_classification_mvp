from datetime import datetime
from typing import List, Optional, Dict

from pydantic import BaseModel


class UploadResponse(BaseModel):
    uploaded: int
    group_id: str
    errors: List[str] = []


class CreativeBase(BaseModel):
    creative_id: str
    group_id: str
    original_filename: str
    file_path: str
    file_size: int
    file_format: str
    image_width: int
    image_height: int
    upload_timestamp: str

    class Config:
        from_attributes = True


class AnalysisBase(BaseModel):
    dominant_colors: List[Dict] = None
    ocr_text: str = None
    ocr_blocks: List[Dict] = None
    detected_objects: List[Dict] = None
    main_topic: str = None
    topic_confidence: float = None
    class Config:
        from_attributes = True


class CreativeDetail(CreativeBase):
    analysis: Optional[AnalysisBase] = None

    class Config:
        from_attributes = True


class GroupSummary(BaseModel):
    total_creatives: int
    first_upload: str
    avg_ocr_confidence: float
    avg_object_confidence: float


class AnalyticsResponse(BaseModel):
    summary: GroupSummary
    topics: List[Dict]
    dominant_colors: List[Dict]
    objects: List[Dict]

class UploadResponse(BaseModel):
    uploaded: int
    group_id: str
    errors: List[str]


class UploadRequest(BaseModel):
    creative_ids: list[str]
    original_filenames: list[str]
