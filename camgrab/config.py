import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Config:
    rtsp_base: str
    rsync_dest: str
    out_dir: Path
    interval: int
    label: str
    tz: str
    workers: int
    cameras: list[str]
    probe_timeout: int
    capture_timeout: int


def cameras_from_dir(cam_dir: Path) -> list[str]:
    return sorted(p.name for p in cam_dir.iterdir())


def load_config() -> Config:
    cameras_env = os.environ.get("CAMGRAB_CAMERAS")
    cam_dir_env = os.environ.get("CAMGRAB_CAM_DIR")

    if cameras_env:
        cameras = [c.strip() for c in cameras_env.split(",") if c.strip()]
    elif cam_dir_env:
        cameras = cameras_from_dir(Path(cam_dir_env))
    else:
        cameras = []

    workers_str = os.environ.get("CAMGRAB_WORKERS")
    workers = int(workers_str) if workers_str else max(1, len(cameras))

    return Config(
        rtsp_base=os.environ.get("CAMGRAB_RTSP_BASE", "rtsp://127.0.0.1:8554/"),
        rsync_dest=os.environ.get("CAMGRAB_RSYNC_DEST", ""),
        out_dir=Path(os.environ.get("CAMGRAB_OUT_DIR", "/dev/shm")),
        interval=int(os.environ.get("CAMGRAB_INTERVAL", "300")),
        label=os.environ.get("CAMGRAB_LABEL", "vandervecken"),
        tz=os.environ.get("CAMGRAB_TZ", "Pacific/Auckland"),
        workers=workers,
        cameras=cameras,
        probe_timeout=int(os.environ.get("CAMGRAB_PROBE_TIMEOUT", "90")),
        capture_timeout=int(os.environ.get("CAMGRAB_CAPTURE_TIMEOUT", "90")),
    )
