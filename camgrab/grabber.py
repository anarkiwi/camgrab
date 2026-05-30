import datetime
import logging
import re
import subprocess
import zoneinfo
from pathlib import Path

from camgrab.config import Config

logger = logging.getLogger(__name__)

_FPS_RE = re.compile(r"(\d+)\s+fps")


def probe_fps(rtsp_url: str, timeout: int) -> int | None:
    """Run ffprobe and return stream FPS, or None if undetectable."""
    try:
        result = subprocess.run(
            ["ffprobe", "-loglevel", "32", "-i", rtsp_url],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    match = _FPS_RE.search(result.stdout + result.stderr)
    return int(match.group(1)) if match else None


def capture_frame(rtsp_url: str, fps: int, raw_path: Path, timeout: int) -> bool:
    """Capture a single frame from the RTSP stream to raw_path."""
    raw_path.unlink(missing_ok=True)
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-nostats",
                "-loglevel",
                "0",
                "-t",
                "5",
                "-i",
                rtsp_url,
                "-y",
                "-f",
                "image2",
                "-q:v",
                "0",
                "-r",
                "1",
                "-frames:v",
                str(fps * 2),
                "-update",
                "1",
                str(raw_path),
            ],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=timeout,
        )
    except (subprocess.TimeoutExpired, OSError):
        return False
    return raw_path.exists() and raw_path.stat().st_size > 0


def annotate_frame(raw_path: Path, out_path: Path, label: str, cam_name: str, tz_name: str) -> bool:
    """Annotate raw_path with a timestamp overlay and write to out_path."""
    tz = zoneinfo.ZoneInfo(tz_name)
    date_str = datetime.datetime.now(tz=tz).strftime("%a %d %b %Y %H:%M:%S %Z")
    annotation = f"{label} {cam_name} {date_str}"
    try:
        subprocess.run(
            [
                "convert",
                str(raw_path),
                "-strip",
                "-interlace",
                "Plane",
                "-gaussian-blur",
                "0.05",
                "-quality",
                "85%",
                "-undercolor",
                "black",
                "-fill",
                "white",
                "-gravity",
                "Southwest",
                "-pointsize",
                "30",
                "-font",
                "FreeMono",
                "-annotate",
                "+0+0",
                annotation,
                str(out_path),
            ],
            check=True,
            capture_output=True,
        )
    except (subprocess.CalledProcessError, OSError):
        return False
    finally:
        raw_path.unlink(missing_ok=True)
    return True


def grab(cam_name: str, config: Config) -> Path | None:
    """Grab and annotate a snapshot for one camera. Returns output path or None on failure."""
    rtsp_url = config.rtsp_base.rstrip("/") + "/" + cam_name
    raw_path = config.out_dir / f"{cam_name}-raw.jpg"
    out_path = config.out_dir / f"{cam_name}.jpg"

    fps = probe_fps(rtsp_url, config.probe_timeout)
    if fps is None:
        logger.debug("%s: no FPS detected, skipping", cam_name)
        return None

    if not capture_frame(rtsp_url, fps, raw_path, config.capture_timeout):
        logger.warning("%s: frame capture failed", cam_name)
        return None

    if not annotate_frame(raw_path, out_path, config.label, cam_name, config.tz):
        logger.warning("%s: annotation failed", cam_name)
        return None

    return out_path
