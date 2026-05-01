import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import os.path as osp
import time
import io
import tempfile
from dataclasses import dataclass
from typing import List, Optional

import cv2
import torch

from loguru import logger
from dotenv import load_dotenv

from external.ByteTrack.yolox.data.data_augment import preproc
from external.ByteTrack.yolox.exp import get_exp
from external.ByteTrack.yolox.utils import fuse_model, get_model_info, postprocess
from external.ByteTrack.yolox.utils.visualize import plot_tracking
from external.ByteTrack.yolox.tracker.byte_tracker import BYTETracker
from external.ByteTrack.yolox.tracking_utils.timer import Timer
from utils.minio_utils import MinioUtils

# Load .env
load_dotenv("../.env")

IMAGE_EXT = [".jpg", ".jpeg", ".webp", ".bmp", ".png"]


@dataclass
class TrackingConfig:
    demo: str = "image"
    experiment_name: Optional[str] = None
    name: Optional[str] = None
    path: str = "./videos/palace.mp4"
    camid: int = 0
    save_result: bool = False
    exp_file: Optional[str] = None
    ckpt: Optional[str] = None
    device: str = "gpu"
    conf: Optional[float] = None
    nms: Optional[float] = None
    tsize: Optional[int] = None
    fps: int = 30
    fp16: bool = False
    fuse: bool = False
    trt: bool = False
    track_thresh: float = 0.5
    track_buffer: int = 30
    match_thresh: float = 0.8
    aspect_ratio_thresh: float = 1.6
    min_box_area: float = 10
    mot20: bool = False

class Predictor(object):
    def __init__(
        self,
        model,
        exp,
        trt_file=None,
        decoder=None,
        device=torch.device("cpu"),
        fp16=False
    ):
        self.model = model
        self.decoder = decoder
        self.num_classes = exp.num_classes
        self.confthre = exp.test_conf
        self.nmsthre = exp.nmsthre
        self.test_size = exp.test_size
        self.device = device
        self.fp16 = fp16
        if trt_file is not None:
            from torch2trt import TRTModule

            model_trt = TRTModule()
            model_trt.load_state_dict(torch.load(trt_file))

            x = torch.ones((1, 3, exp.test_size[0], exp.test_size[1]), device=device)
            self.model(x)
            self.model = model_trt
        self.rgb_means = (0.485, 0.456, 0.406)
        self.std = (0.229, 0.224, 0.225)

    def inference(self, img, timer):
        img_info = {"id": 0}
        if isinstance(img, str):
            img_info["file_name"] = osp.basename(img)
            img = cv2.imread(img)
        else:
            img_info["file_name"] = None

        height, width = img.shape[:2]
        img_info["height"] = height
        img_info["width"] = width
        img_info["raw_img"] = img

        img, ratio = preproc(img, self.test_size, self.rgb_means, self.std)
        img_info["ratio"] = ratio
        img = torch.from_numpy(img).unsqueeze(0).float().to(self.device)
        if self.fp16:
            img = img.half()  # to FP16

        with torch.no_grad():
            timer.tic()
            outputs = self.model(img)
            if self.decoder is not None:
                outputs = self.decoder(outputs, dtype=outputs.type())
            outputs = postprocess(
                outputs, self.num_classes, self.confthre, self.nmsthre
            )
            #logger.info("Infer time: {:.4f}s".format(time.time() - t0))
        return outputs, img_info

class ByteTrackService:
    def __init__(self, config: Optional[TrackingConfig] = None):
        self.config = config or TrackingConfig()
        self.exp = get_exp(self.config.exp_file, self.config.name)
        
        # Load MinIO configuration and initialize MinioUtils
        self.minio_utils = MinioUtils(
            bucket_name=os.getenv("MINIO_BUCKET", "videos"),
            endpoint=os.getenv("MINIO_ENDPOINT"),
            access_key=os.getenv("MINIO_ACCESS_KEY"),
            secret_key=os.getenv("MINIO_SECRET_KEY"),
        )

    def run(self):
        predictor = self._prepare_predictor_and_output()
        current_time = time.localtime()

        if self.config.demo == "video":
            output_path = self._imageflow_demo(predictor, current_time)
            return output_path
        elif self.config.demo == "webcam":
            pass
        else:
            raise ValueError(f"Unsupported demo type: {self.config.demo}")

    def _prepare_predictor_and_output(self):
        if not self.config.experiment_name:
            self.config.experiment_name = self.exp.exp_name

        output_dir = osp.join(self.exp.output_dir, self.config.experiment_name)
        os.makedirs(output_dir, exist_ok=True)

        if self.config.trt:
            self.config.device = "gpu"
        device = torch.device("cuda" if self.config.device == "gpu" else "cpu")

        logger.info("Config: {}".format(self.config))

        if self.config.conf is not None:
            self.exp.test_conf = self.config.conf
        if self.config.nms is not None:
            self.exp.nmsthre = self.config.nms
        if self.config.tsize is not None:
            self.exp.test_size = (self.config.tsize, self.config.tsize)

        model = self.exp.get_model().to(device)
        logger.info("Model Summary: {}".format(get_model_info(model, self.exp.test_size)))
        model.eval()

        if not self.config.trt:
            if self.config.ckpt is None:
                ckpt_file = osp.join(output_dir, "best_ckpt.pth.tar")
            else:
                ckpt_file = self.config.ckpt
            logger.info("loading checkpoint")
            ckpt = torch.load(ckpt_file, map_location="cpu")
            model.load_state_dict(ckpt["model"])
            logger.info("loaded checkpoint done.")

        if self.config.fuse:
            logger.info("\tFusing model...")
            model = fuse_model(model)

        if self.config.fp16:
            model = model.half()

        if self.config.trt:
            assert not self.config.fuse, "TensorRT model is not support model fusing!"
            trt_file = osp.join(output_dir, "model_trt.pth")
            assert osp.exists(
                trt_file
            ), "TensorRT model is not found!\n Run python3 tools/trt.py first!"
            model.head.decode_in_inference = False
            decoder = model.head.decode_outputs
            logger.info("Using TensorRT to inference")
        else:
            trt_file = None
            decoder = None

        predictor = Predictor(model, self.exp, trt_file, decoder, device, self.config.fp16)
        return predictor

    def _imageflow_demo(self, predictor, current_time):
        cap = cv2.VideoCapture(self.config.path if self.config.demo == "video" else self.config.camid)
        width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        fps = cap.get(cv2.CAP_PROP_FPS)

        tracker = BYTETracker(self.config, frame_rate=self.config.fps)
        timer = Timer()
        frame_id = 0
        results: List[str] = []

        timestamp = None
        vid_writer = None
        save_path = None
        if self.config.save_result:
            timestamp = time.strftime("%Y_%m_%d_%H_%M_%S", current_time)
            # write to a temporary local file then upload to MinIO if available
            if self.config.demo == "video":
                base_name = osp.basename(self.config.path)
            else:
                base_name = "camera.mp4"
            
            # Create tempfile for upload to Minio
            tmp_vid = tempfile.NamedTemporaryFile(delete=False, suffix=osp.splitext(base_name)[1])
            tmp_vid.close()
            save_path = tmp_vid.name
            logger.info(f"temporary video path is {save_path}")
            vid_writer = cv2.VideoWriter(
                save_path,
                cv2.VideoWriter_fourcc(*"mp4v"),
                fps,
                (int(width), int(height)),
            )

        while True:
            if frame_id % 20 == 0:
                logger.info(
                    "Processing frame {} ({:.2f} fps)".format(
                        frame_id, 1.0 / max(1e-5, timer.average_time)
                    )
                )
            ret_val, frame = cap.read()
            if not ret_val:
                break
            
            outputs, img_info = predictor.inference(frame, timer)
            if outputs[0] is not None:
                online_targets = tracker.update(
                    outputs[0], [img_info["height"], img_info["width"]], self.exp.test_size
                )
                online_tlwhs = []
                online_ids = []
                for t in online_targets:
                    tlwh = t.tlwh
                    tid = t.track_id
                    vertical = tlwh[2] / tlwh[3] > self.config.aspect_ratio_thresh
                    if tlwh[2] * tlwh[3] > self.config.min_box_area and not vertical:
                        online_tlwhs.append(tlwh)
                        online_ids.append(tid)
                        results.append(
                            f"{frame_id},{tid},{tlwh[0]:.2f},{tlwh[1]:.2f},{tlwh[2]:.2f},{tlwh[3]:.2f},{t.score:.2f},-1,-1,-1\n"
                        )
                timer.toc()
                online_im = plot_tracking(
                    img_info["raw_img"],
                    online_tlwhs,
                    online_ids,
                    frame_id=frame_id + 1,
                    fps=1.0 / timer.average_time,
                )
            else:
                timer.toc()
                online_im = img_info["raw_img"]

            if self.config.save_result:
                vid_writer.write(online_im)

            ch = cv2.waitKey(1)
            if ch == 27 or ch == ord("q") or ch == ord("Q"):
                break

            frame_id += 1

        cap.release()
        if vid_writer is not None:
            vid_writer.release()

        uploaded_video_url = None
        uploaded_results_url = None
        if self.config.save_result:
            # upload video file to MinIO if MinioUtils is initialized
            if self.minio_utils is not None:
                try:
                    object_name = f"tracked/{timestamp}/{base_name}"
                    uploaded_video_url = self.minio_utils.upload_file(
                        file_path=save_path,
                        object_name=object_name,
                        content_type="video/mp4",
                    )
                    logger.info(f"uploaded video to minio: {uploaded_video_url}")
                except Exception as e:
                    logger.error(f"failed upload video to minio: {e}")

                # write results to bytes and upload
                try:
                    results_txt = "".join(results)
                    object_name_txt = f"tracked/{timestamp}/{osp.splitext(base_name)[0]}_results.txt"
                    self.minio_utils.upload_bytes(
                        file_data=results_txt.encode("utf-8"),
                        object_name=object_name_txt,
                        content_type="text/plain",
                    )
                    uploaded_results_url = self.minio_utils.presigned_get_object(object_name_txt)
                    logger.info(f"uploaded results to minio: {uploaded_results_url}")
                except Exception as e:
                    logger.error(f"failed upload results to minio: {e}")

            # cleanup temp files
            try:
                if osp.exists(save_path):
                    os.remove(save_path)
            except Exception:
                pass

        return uploaded_video_url