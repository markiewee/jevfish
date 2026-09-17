from jevfish.config import env_file_path
from tests.test_pipeline import settings


def test_env_file_path_follows_env(tmp_path, monkeypatch):
    monkeypatch.setenv("JEVFISH_ENV_FILE", str(tmp_path / "x.env"))
    assert env_file_path() == tmp_path / "x.env"


def test_health_reports_app_and_setup_needed(tmp_path):
    ready = settings(tmp_path).health()
    assert ready["app"] == "jevfish" and ready["setup_needed"] is False
    missing = settings(tmp_path, fake_judge=False, fake_llm=False).health()
    assert missing["setup_needed"] is True
