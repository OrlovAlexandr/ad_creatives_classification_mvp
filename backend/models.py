from typing import Any

from pydantic import BaseModel


class UploadRequest(BaseModel):
    creative_ids: list[str]
    original_filenames: list[str]


class UploadResponse(BaseModel):
    uploaded: int
    group_id: str
    errors: list[str] = []


class AnalyticsResponse(BaseModel):
    summary: dict[str, Any]
    topics: list[dict[str, Any]]
    dominant_colors: list[dict[str, Any]]
    durations: dict[str, float] | None = None
    topics_table: list[dict[str, Any]] | None = None
    total_processing_time: float | None = None
    total_creatives_in_group: int | None
    color_class_distribution: dict[str, float] | None = None
    topic_color_distribution: dict[str, list[dict[str, Any]]] | None = None


class AnalysisBase(BaseModel):
    dominant_colors: list[dict] | None = None
    secondary_colors: list[dict] | None = None
    palette_colors: dict | None = None

    ocr_status: str | None = None
    detection_status: str | None = None
    classification_status: str | None = None
    color_analysis_status: str | None = None
    ocr_duration: float | None = None
    detection_duration: float | None = None
    classification_duration: float | None = None
    color_analysis_duration: float | None = None

    ocr_text: str | None = None
    ocr_blocks: list[dict] | None = None
    detected_objects: list[dict] | None = None
    main_topic: str | None = None
    topic_confidence: float | None = None

    class Config:
        from_attributes = True


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


class CreativeDetail(CreativeBase):
    overall_status: str | None = None
    dominant_colors: list[dict] | None = None
    secondary_colors: list[dict] | None = None
    palette_colors: dict | None = None
    ocr_text: str | None = None
    ocr_blocks: list[dict] | None = None
    detected_objects: list[dict] | None = None
    main_topic: str | None = None
    topic_confidence: float | None = None

    class Config:
        from_attributes = True


class GroupSummary(BaseModel):
    total_creatives: int
    first_upload: str
    avg_ocr_confidence: float
    avg_object_confidence: float
