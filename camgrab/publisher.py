import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def rsync_publish(src: Path, dest: str) -> bool:
    """rsync src to dest. Returns True on success."""
    try:
        subprocess.run(["rsync", "-a", str(src), dest], check=True, capture_output=True)
    except (subprocess.CalledProcessError, OSError):
        logger.warning("rsync failed: %s -> %s", src, dest)
        return False
    return True
