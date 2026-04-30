import os
import sys
from typing import Optional

from fastapi import APIRouter, HTTPException, Body
from loguru import logger

from schemas.tracking import TrackingConfigSchema, TrackingResponseSchema
from services.tracking import ByteTrackService, TrackingConfig


router = APIRouter(prefix="/tracking", tags=["tracking"])


def convert_schema_to_config(schema: TrackingConfigSchema) -> TrackingConfig:
    """Convert Pydantic schema to TrackingConfig dataclass"""
    return TrackingConfig(
        demo=schema.demo,
        experiment_name=schema.experiment_name,
        name=schema.name,
        path=schema.path,
        camid=schema.camid,
        save_result=schema.save_result,
        exp_file=schema.exp_file,
        ckpt=schema.ckpt,
        device=schema.device,
        conf=schema.conf,
        nms=schema.nms,
        tsize=schema.tsize,
        fps=schema.fps,
        fp16=schema.fp16,
        fuse=schema.fuse,
        trt=schema.trt,
        track_thresh=schema.track_thresh,
        track_buffer=schema.track_buffer,
        match_thresh=schema.match_thresh,
        aspect_ratio_thresh=schema.aspect_ratio_thresh,
        min_box_area=schema.min_box_area,
        mot20=schema.mot20,
    )


@router.post("/run", response_model=TrackingResponseSchema)
async def run_tracking(config: TrackingConfigSchema = Body(..., description="Tracking configuration")):
    """
    Run object tracking on images or video

    - **demo**: Type of input - 'image', 'video', or 'webcam'
    - **path**: Path to image directory, video file, or video file for webcam
    - **save_result**: Whether to save tracking results and visualizations
    - **device**: 'gpu' or 'cpu' for model inference
    """
    try:
        logger.info(f"Starting tracking with config: demo={config.demo}, path={config.path}")
        
        # Convert schema to config
        tracking_config = convert_schema_to_config(config)
        
        # Initialize and run service
        service = ByteTrackService(config=tracking_config)
        service.run()
        
        logger.info("Tracking completed successfully")
        
        return TrackingResponseSchema(
            status="success",
            message="Tracking completed successfully",
            saved_folder=None,  # Could be enhanced to return actual folder path
        )
    
    except FileNotFoundError as e:
        logger.error(f"File not found: {str(e)}")
        raise HTTPException(status_code=404, detail=f"File not found: {str(e)}")
    
    except ValueError as e:
        logger.error(f"Invalid configuration: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Invalid configuration: {str(e)}")
    
    except Exception as e:
        logger.error(f"Tracking failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Tracking failed: {str(e)}")


@router.post("/image", response_model=TrackingResponseSchema)
async def track_images(
    path: str = Body(..., description="Path to image or directory containing images"),
    save_result: bool = Body(False, description="Save visualization results"),
    device: str = Body("gpu", description="Device: 'gpu' or 'cpu'"),
    conf: Optional[float] = Body(None, description="Confidence threshold"),
):
    """
    Track objects in images

    - **path**: Path to single image or directory with images
    - **save_result**: Save tracking visualizations
    - **device**: 'gpu' or 'cpu'
    - **conf**: Detection confidence threshold
    """
    try:
        config = TrackingConfigSchema(
            demo="image",
            path=path,
            save_result=save_result,
            device=device,
            conf=conf,
        )
        
        tracking_config = convert_schema_to_config(config)
        service = ByteTrackService(config=tracking_config)
        service.run()
        
        logger.info(f"Image tracking completed: {path}")
        
        return TrackingResponseSchema(
            status="success",
            message=f"Image tracking completed for {path}",
        )
    
    except Exception as e:
        logger.error(f"Image tracking failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Image tracking failed: {str(e)}")


@router.post("/video", response_model=TrackingResponseSchema)
async def track_video(
    path: str = Body(..., description="Path to video file"),
    save_result: bool = Body(False, description="Save tracking results and video"),
    device: str = Body("gpu", description="Device: 'gpu' or 'cpu'"),
    conf: Optional[float] = Body(None, description="Confidence threshold"),
    exp_file: str = Body(
        "/media/ctuav/corsair-ssd/hunglh/Person-Re-ID/external/ByteTrack/exps/example/mot/yolox_x_mix_det.py",
        description="Path to ByteTrack experiment file"
    ),
    ckpt: str = Body(
        "/media/ctuav/corsair-ssd/hunglh/Person-Re-ID/checkpoints/bytetrack_x_mot17.pth.tar",
        description="Path to model checkpoint"
    )
):
    """
    Track objects in video

    - **path**: Path to video file
    - **save_result**: Save tracked video and results
    - **device**: 'gpu' or 'cpu'
    - **conf**: Detection confidence threshold
    - **exp_file**: Path to experiment file
    - **ckpt**: Path to checkpoint file
    """
    try:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Video file not found: {path}")
        
        config = TrackingConfigSchema(
            demo="video",
            path=path,
            save_result=save_result,
            device=device,
            conf=conf,
            exp_file=exp_file,
            ckpt=ckpt
        )
        
        print(config)
        
        tracking_config = convert_schema_to_config(config)
        service = ByteTrackService(config=tracking_config)
        service.run()
        
        logger.info(f"Video tracking completed: {path}")
        
        return TrackingResponseSchema(
            status="success",
            message=f"Video tracking completed for {path}",
        )
    
    except FileNotFoundError as e:
        logger.error(f"Video file not found: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    
    except Exception as e:
        logger.error(f"Video tracking failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Video tracking failed: {str(e)}")


@router.post("/webcam", response_model=TrackingResponseSchema)
async def track_webcam(
    camid: int = Body(0, description="Camera ID"),
    save_result: bool = Body(False, description="Save tracking results"),
    device: str = Body("gpu", description="Device: 'gpu' or 'cpu'"),
    conf: Optional[float] = Body(None, description="Confidence threshold"),
    experiment_name: Optional[str] = Body(None, description="Experiment name"),
):
    """
    Track objects from webcam

    - **camid**: Camera device ID (default: 0)
    - **save_result**: Save tracking video
    - **device**: 'gpu' or 'cpu'
    - **conf**: Detection confidence threshold
    """
    try:
        config = TrackingConfigSchema(
            demo="webcam",
            camid=camid,
            path="",
            save_result=save_result,
            device=device,
            conf=conf,
            experiment_name=experiment_name,
        )
        
        tracking_config = convert_schema_to_config(config)
        service = ByteTrackService(config=tracking_config)
        service.run()
        
        logger.info(f"Webcam tracking completed: camera {camid}")
        
        return TrackingResponseSchema(
            status="success",
            message=f"Webcam tracking completed for camera {camid}",
        )
    
    except Exception as e:
        logger.error(f"Webcam tracking failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Webcam tracking failed: {str(e)}")


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "ByteTrack",
        "version": "1.0.0",
    }
