from datetime import datetime
from typing import List, Optional, Dict, Any

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
    dominant_colors: Optional[List[Dict]] = None
    secondary_colors: Optional[List[Dict]] = None
    palette_colors: Optional[Dict] = None

    ocr_status: Optional[str] = None
    detection_status: Optional[str] = None
    classification_status: Optional[str] = None
    color_analysis_status: Optional[str] = None
    ocr_duration: Optional[float] = None
    detection_duration: Optional[float] = None
    classification_duration: Optional[float] = None
    color_analysis_duration: Optional[float] = None
    
    ocr_text: Optional[str] = None
    ocr_blocks: Optional[List[Dict]] = None
    detected_objects: Optional[List[Dict]] = None
    main_topic: Optional[str] = None
    topic_confidence: Optional[float] = None
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
    summary: Dict[str, Any]
    topics: List[Dict[str, Any]]
    dominant_colors: List[Dict[str, Any]]
    durations: Optional[Dict[str, float]] = None
    topics_table: Optional[List[Dict[str, Any]]] = None
    total_processing_time: Optional[float] = None
    total_creatives_in_group: Optional[int]
    color_class_distribution: Optional[Dict[str, float]] = None
    topic_color_distribution: Optional[Dict[str, List[Dict[str, Any]]]] = None

class UploadResponse(BaseModel):
    uploaded: int
    group_id: str
    errors: List[str]


class UploadRequest(BaseModel):
    creative_ids: list[str]
    original_filenames: list[str]
