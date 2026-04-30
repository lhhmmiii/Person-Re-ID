import os
from dotenv import load_dotenv
from fastapi import UploadFile, File
from utils.minio_utils import MinioUtils
from fastapi import APIRouter, HTTPException, Body
import uuid

# Load env params from .env
load_dotenv("../.env")

router = APIRouter(prefix="/videos", tags=["videos"])

minio_utils = MinioUtils(
    bucket_name="videos",
    endpoint=os.getenv("MINIO_ENDPOINT"),
    access_key=os.getenv("MINIO_ACCESS_KEY"),
    secret_key=os.getenv("MINIO_SECRET_KEY")
)

@router.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    video_id = str(uuid.uuid4())
    object_name = f"raw/{video_id}.mp4"

    data = await file.read()
    
    minio_utils.upload_bytes(
        file_data=data,
        object_name=object_name,
        content_type="video/mp4"
    )

    return {
        "video_id": video_id,
        "object_name": object_name
    }