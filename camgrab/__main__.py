import concurrent.futures
import logging
import time

from camgrab.config import Config, load_config
from camgrab.grabber import grab
from camgrab.publisher import rsync_publish

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


def run_once(config: Config) -> None:
    def _grab_and_publish(cam_name: str) -> None:
        out = grab(cam_name, config)
        if out is not None and config.rsync_dest:
            rsync_publish(out, config.rsync_dest)

    with concurrent.futures.ThreadPoolExecutor(max_workers=config.workers) as executor:
        futures = {executor.submit(_grab_and_publish, c): c for c in config.cameras}
        for future in concurrent.futures.as_completed(futures):
            cam = futures[future]
            try:
                future.result()
            except Exception:
                logger.exception("%s: unexpected error", cam)


def main() -> None:
    config = load_config()
    if not config.cameras:
        logger.warning("No cameras configured — set CAMGRAB_CAMERAS or CAMGRAB_CAM_DIR")
    while True:
        run_once(config)
        time.sleep(config.interval)


if __name__ == "__main__":
    main()
