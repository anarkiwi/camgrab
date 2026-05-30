import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from camgrab.config import Config
from camgrab.grabber import annotate_frame, capture_frame, grab, probe_fps


def _config(tmp_path: Path) -> Config:
    return Config(
        rtsp_base="rtsp://127.0.0.1:8554/",
        rsync_dest="",
        out_dir=tmp_path,
        interval=300,
        label="finf",
        tz="Pacific/Auckland",
        workers=1,
        cameras=["driveway"],
        probe_timeout=90,
        capture_timeout=90,
    )


# --- probe_fps ---


def test_probe_fps_parses_fps_from_stderr():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="", stderr="Stream #0:0, 25 fps, 25 tbr")
        assert probe_fps("rtsp://localhost/cam", 90) == 25


def test_probe_fps_parses_fps_from_stdout():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="Video: h264, 30 fps", stderr="")
        assert probe_fps("rtsp://localhost/cam", 90) == 30


def test_probe_fps_returns_none_when_no_fps_in_output():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="", stderr="no video info here")
        assert probe_fps("rtsp://localhost/cam", 90) is None


def test_probe_fps_returns_none_on_timeout():
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("ffprobe", 90)):
        assert probe_fps("rtsp://localhost/cam", 90) is None


def test_probe_fps_returns_none_on_oserror():
    with patch("subprocess.run", side_effect=OSError("not found")):
        assert probe_fps("rtsp://localhost/cam", 90) is None


# --- capture_frame ---


def test_capture_frame_returns_true_when_ffmpeg_creates_nonempty_file(tmp_path):
    raw = tmp_path / "cam-raw.jpg"

    def fake_ffmpeg(*_args, **_kwargs):
        raw.write_bytes(b"\xff\xd8\xff" * 100)
        return MagicMock(returncode=0)

    with patch("subprocess.run", side_effect=fake_ffmpeg):
        assert capture_frame("rtsp://localhost/cam", 30, raw, 90) is True


def test_capture_frame_returns_false_when_ffmpeg_creates_empty_file(tmp_path):
    raw = tmp_path / "cam-raw.jpg"

    def fake_ffmpeg(*_args, **_kwargs):
        raw.write_bytes(b"")
        return MagicMock(returncode=0)

    with patch("subprocess.run", side_effect=fake_ffmpeg):
        assert capture_frame("rtsp://localhost/cam", 30, raw, 90) is False


def test_capture_frame_returns_false_when_ffmpeg_creates_no_file(tmp_path):
    raw = tmp_path / "cam-raw.jpg"
    with patch("subprocess.run"):
        assert capture_frame("rtsp://localhost/cam", 30, raw, 90) is False


def test_capture_frame_returns_false_on_timeout(tmp_path):
    raw = tmp_path / "cam-raw.jpg"
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("ffmpeg", 90)):
        assert capture_frame("rtsp://localhost/cam", 30, raw, 90) is False


def test_capture_frame_deletes_stale_raw_before_capture(tmp_path):
    raw = tmp_path / "cam-raw.jpg"
    raw.write_bytes(b"stale")
    captured_args = []

    def fake_ffmpeg(*_args, **_kwargs):
        captured_args.append(raw.exists())
        return MagicMock(returncode=0)

    with patch("subprocess.run", side_effect=fake_ffmpeg):
        capture_frame("rtsp://localhost/cam", 30, raw, 90)

    assert captured_args[0] is False


# --- annotate_frame ---


def test_annotate_frame_builds_correct_convert_command(tmp_path):
    raw = tmp_path / "cam-raw.jpg"
    raw.write_bytes(b"data")
    out = tmp_path / "cam.jpg"

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        result = annotate_frame(raw, out, "finf", "driveway", "Pacific/Auckland")

    assert result is True
    cmd = mock_run.call_args[0][0]
    assert cmd[0] == "convert"
    assert str(raw) == cmd[1]
    assert str(out) == cmd[-1]
    assert "-font" in cmd
    assert cmd[cmd.index("-font") + 1] == "FreeMono"
    annotation = cmd[-2]
    assert annotation.startswith("finf driveway ")


def test_annotate_frame_deletes_raw_on_success(tmp_path):
    raw = tmp_path / "cam-raw.jpg"
    raw.write_bytes(b"data")
    out = tmp_path / "cam.jpg"

    with patch("subprocess.run"):
        annotate_frame(raw, out, "finf", "driveway", "Pacific/Auckland")

    assert not raw.exists()


def test_annotate_frame_deletes_raw_on_failure(tmp_path):
    raw = tmp_path / "cam-raw.jpg"
    raw.write_bytes(b"data")
    out = tmp_path / "cam.jpg"

    with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "convert")):
        result = annotate_frame(raw, out, "finf", "driveway", "Pacific/Auckland")

    assert result is False
    assert not raw.exists()


# --- grab (integration) ---


def test_grab_returns_none_when_no_fps(tmp_path):
    config = _config(tmp_path)
    with patch("camgrab.grabber.probe_fps", return_value=None):
        assert grab("driveway", config) is None


def test_grab_returns_none_when_capture_fails(tmp_path):
    config = _config(tmp_path)
    with (
        patch("camgrab.grabber.probe_fps", return_value=30),
        patch("camgrab.grabber.capture_frame", return_value=False),
    ):
        assert grab("driveway", config) is None


def test_grab_returns_none_when_annotate_fails(tmp_path):
    config = _config(tmp_path)
    with (
        patch("camgrab.grabber.probe_fps", return_value=30),
        patch("camgrab.grabber.capture_frame", return_value=True),
        patch("camgrab.grabber.annotate_frame", return_value=False),
    ):
        assert grab("driveway", config) is None


def test_grab_returns_output_path_on_success(tmp_path):
    config = _config(tmp_path)
    with (
        patch("camgrab.grabber.probe_fps", return_value=30),
        patch("camgrab.grabber.capture_frame", return_value=True),
        patch("camgrab.grabber.annotate_frame", return_value=True),
    ):
        result = grab("driveway", config)

    assert result == tmp_path / "driveway.jpg"


def test_grab_constructs_rtsp_url_correctly(tmp_path):
    config = _config(tmp_path)
    probed_urls = []

    def fake_probe(url: str, _timeout: int) -> None:
        probed_urls.append(url)
        return None

    with patch("camgrab.grabber.probe_fps", side_effect=fake_probe):
        grab("driveway", config)

    assert probed_urls == ["rtsp://127.0.0.1:8554/driveway"]
