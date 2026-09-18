"""Where files live must not depend on being run from a git checkout.

The old `PACKAGE_ROOT = Path(__file__).resolve().parents[2]` was the repo root from a
checkout and a nonsense path inside site-packages once installed. Measured consequences,
all three real: the wheel carried no web_dist so the app served / as a 404, the bundled
example seed was missing, and the key file resolved somewhere unwritable.
"""

from pathlib import Path

from jevfish import assets


def test_web_dist_exists_and_has_an_index():
    d = assets.web_dist()
    assert d.is_dir(), f"{d} is not a directory"
    assert (d / "index.html").is_file()


def test_the_built_app_has_its_javascript_bundle():
    js = list((assets.web_dist() / "assets").glob("*.js"))
    assert js, "the built Vue app is missing its bundle"
    assert js[0].stat().st_size > 10_000


def test_example_seed_is_readable():
    p = assets.example_seed()
    assert p.is_file()
    assert "Lazybee" in p.read_text()


def test_all_example_seeds_ship():
    names = {p.name for p in assets.examples_dir().glob("*.md")}
    assert "lazybee-cleaning.md" in names


def test_data_dir_respects_the_env_override(tmp_path, monkeypatch):
    monkeypatch.setenv("JEVFISH_DATA_DIR", str(tmp_path / "somewhere"))
    d = assets.data_dir()
    assert d == tmp_path / "somewhere"
    d.mkdir(parents=True, exist_ok=True)
    (d / "probe").write_text("ok")
    assert (d / "probe").read_text() == "ok"


def test_data_dir_defaults_outside_the_package(monkeypatch):
    """site-packages is not writable, so nothing we write may resolve inside it."""
    monkeypatch.delenv("JEVFISH_DATA_DIR", raising=False)
    d = assets.data_dir()
    pkg = Path(assets.__file__).resolve().parent
    assert pkg not in d.resolve().parents
    assert d.name == "jevfish"


def test_env_file_follows_the_data_dir_and_its_own_override(tmp_path, monkeypatch):
    monkeypatch.delenv("JEVFISH_ENV_FILE", raising=False)
    monkeypatch.setenv("JEVFISH_DATA_DIR", str(tmp_path / "d"))
    assert assets.env_file() == tmp_path / "d" / ".env"
    monkeypatch.setenv("JEVFISH_ENV_FILE", str(tmp_path / "keys.env"))
    assert assets.env_file() == tmp_path / "keys.env"
