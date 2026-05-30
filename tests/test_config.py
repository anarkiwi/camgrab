from camgrab.config import cameras_from_dir, load_config


def test_load_config_defaults(monkeypatch):
    for var in (
        "CAMGRAB_CAMERAS",
        "CAMGRAB_CAM_DIR",
        "CAMGRAB_RTSP_BASE",
        "CAMGRAB_RSYNC_DEST",
        "CAMGRAB_OUT_DIR",
        "CAMGRAB_INTERVAL",
        "CAMGRAB_LABEL",
        "CAMGRAB_TZ",
        "CAMGRAB_WORKERS",
        "CAMGRAB_PROBE_TIMEOUT",
        "CAMGRAB_CAPTURE_TIMEOUT",
    ):
        monkeypatch.delenv(var, raising=False)
    config = load_config()
    assert config.rtsp_base == "rtsp://127.0.0.1:8554/"
    assert config.label == "vandervecken"
    assert config.tz == "Pacific/Auckland"
    assert config.interval == 300
    assert config.probe_timeout == 90
    assert config.capture_timeout == 90
    assert config.cameras == []


def test_load_config_cameras_from_env(monkeypatch):
    monkeypatch.setenv("CAMGRAB_CAMERAS", "driveway, garage, front")
    monkeypatch.delenv("CAMGRAB_CAM_DIR", raising=False)
    config = load_config()
    assert config.cameras == ["driveway", "garage", "front"]


def test_load_config_cameras_from_dir(monkeypatch, tmp_path):
    (tmp_path / "garage").mkdir()
    (tmp_path / "driveway").mkdir()
    (tmp_path / "front").mkdir()
    monkeypatch.setenv("CAMGRAB_CAM_DIR", str(tmp_path))
    monkeypatch.delenv("CAMGRAB_CAMERAS", raising=False)
    config = load_config()
    assert config.cameras == ["driveway", "front", "garage"]


def test_load_config_cameras_env_takes_precedence_over_dir(monkeypatch, tmp_path):
    (tmp_path / "other").mkdir()
    monkeypatch.setenv("CAMGRAB_CAM_DIR", str(tmp_path))
    monkeypatch.setenv("CAMGRAB_CAMERAS", "explicit")
    config = load_config()
    assert config.cameras == ["explicit"]


def test_load_config_workers_defaults_to_camera_count(monkeypatch):
    monkeypatch.setenv("CAMGRAB_CAMERAS", "a,b,c")
    monkeypatch.delenv("CAMGRAB_WORKERS", raising=False)
    monkeypatch.delenv("CAMGRAB_CAM_DIR", raising=False)
    config = load_config()
    assert config.workers == 3


def test_load_config_workers_explicit(monkeypatch):
    monkeypatch.setenv("CAMGRAB_CAMERAS", "a,b,c")
    monkeypatch.setenv("CAMGRAB_WORKERS", "2")
    monkeypatch.delenv("CAMGRAB_CAM_DIR", raising=False)
    config = load_config()
    assert config.workers == 2


def test_cameras_from_dir_sorted(tmp_path):
    (tmp_path / "b").touch()
    (tmp_path / "a").touch()
    (tmp_path / "c").mkdir()
    assert cameras_from_dir(tmp_path) == ["a", "b", "c"]
