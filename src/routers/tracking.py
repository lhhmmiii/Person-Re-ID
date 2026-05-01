import os
import tempfile
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Body
from fastapi import UploadFile, File, Form, HTTPException
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
        
        tracking_config = convert_schema_to_config(config)
        service = ByteTrackService(config=tracking_config)
        output_path = service.run()
        
        logger.info(f"Video tracking completed: {path}")
        
        return TrackingResponseSchema(
            status="success",
            message=f"Video tracking completed for {path}",
            output_path=output_path,
        )
    
    except FileNotFoundError as e:
        logger.error(f"Video file not found: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    
    except Exception as e:
        logger.error(f"Video tracking failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Video tracking failed: {str(e)}")

@router.post("/video-upload", response_model=TrackingResponseSchema)
async def track_video_upload(
    file: UploadFile = File(...),
    save_result: bool = Form(False),
    device: str = Form("gpu"),
    conf: Optional[float] = Form(None),
    exp_file: str = Form(...),
    ckpt: str = Form(...),
):
    try:
        video_id = str(uuid.uuid4())

        # 1. Save temp input
        tmp_input = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        tmp_input_path = tmp_input.name
        tmp_input.close()

        with open(tmp_input_path, "wb") as f:
            f.write(await file.read())

        config = TrackingConfigSchema(
            demo="video",
            path=tmp_input_path,
            save_result=save_result,
            device=device,
            conf=conf,
            exp_file=exp_file,
            ckpt=ckpt
        )

        tracking_config = convert_schema_to_config(config)
        service = ByteTrackService(config=tracking_config)
        output_path = service.run()

        # 4. Cleanup
        os.remove(tmp_input_path)

        return TrackingResponseSchema(
            status="success",
            message="Tracking completed",
            output_path=output_path
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
