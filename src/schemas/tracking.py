from typing import Optional
from pydantic import BaseModel, Field


class TrackingConfigSchema(BaseModel):
    """Tracking configuration schema for API requests"""
    demo: str = Field(default="image", description="Demo type: 'image', 'video', or 'webcam'")
    experiment_name: Optional[str] = Field(default=None, description="Experiment name")
    name: Optional[str] = Field(default=None, description="Model name")
    path: str = Field(default="./videos/palace.mp4", description="Path to image/video file or camera ID")
    camid: int = Field(default=0, description="Camera ID for webcam")
    save_result: bool = Field(default=False, description="Whether to save tracking results")
    exp_file: Optional[str] = Field(default=None, description="Experiment config file")
    ckpt: Optional[str] = Field(default=None, description="Checkpoint path")
    device: str = Field(default="gpu", description="Device: 'gpu' or 'cpu'")
    conf: Optional[float] = Field(default=None, description="Confidence threshold")
    nms: Optional[float] = Field(default=None, description="NMS threshold")
    tsize: Optional[int] = Field(default=None, description="Test image size")
    fps: int = Field(default=30, description="FPS for video")
    fp16: bool = Field(default=False, description="Use FP16 precision")
    fuse: bool = Field(default=False, description="Fuse model")
    trt: bool = Field(default=False, description="Use TensorRT")
    track_thresh: float = Field(default=0.5, description="Track threshold")
    track_buffer: int = Field(default=30, description="Track buffer size")
    match_thresh: float = Field(default=0.8, description="Match threshold")
    aspect_ratio_thresh: float = Field(default=1.6, description="Aspect ratio threshold")
    min_box_area: float = Field(default=10, description="Minimum bounding box area")
    mot20: bool = Field(default=False, description="MOT20 dataset mode")


class TrackingResultSchema(BaseModel):
    """Tracking result schema for API responses"""
    frame_id: int
    track_id: int
    x1: float
    y1: float
    w: float
    h: float
    score: float


class TrackingResponseSchema(BaseModel):
    """Response schema for tracking endpoint"""
    status: str = Field(description="Status of the tracking operation")
    message: str = Field(description="Status message")
    output_path: Optional[str] = Field(description="video output path")
