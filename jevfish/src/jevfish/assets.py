"""Where JevFish's files live, in development and once installed.

This module exists because of a measured bug. `config.py` used to compute

    PACKAGE_ROOT = Path(__file__).resolve().parents[2]

which is the repository root from a git checkout and a nonsense path inside
site-packages once the wheel is installed. Three things broke as a result, and all three
were verified: `web/dist` was not in the wheel at all so the app served `/` as a 404, the
bundled example seed was missing so the "Fill in the example" button failed, and the key
file and data directory resolved somewhere unwritable.

So: read-only assets ship inside the package and resolve through `importlib.resources`,
and anything written goes to a per-user directory that exists and is writable.
"""

from __future__ import annotations

import os
import sys
from importlib import resources
from pathlib import Path

APP = "jevfish"


def _packaged(name: str) -> Path:
    return Path(str(resources.files(APP) / name))


def web_dist() -> Path:
    """The built Vue app, served at /."""
    return _packaged("web_dist")


def examples_dir() -> Path:
    return _packaged("examples")


def example_seed() -> Path:
    """The seed document behind the "Fill in the example" button."""
    return examples_dir() / "lazybee-cleaning.md"


def _user_data_home() -> Path:
    """The platform's place for application data. No dependency needed for three cases."""
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support"
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    return Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")


def data_dir() -> Path:
    """Writable. Projects, runs, caches and recorded outcomes.

    Override with JEVFISH_DATA_DIR. Note this must never sit inside the package: site
    packages is not writable, and on macOS an app bundle cannot read Desktop, Documents
    or Downloads without a permission prompt the launcher cannot answer.
    """
    override = os.environ.get("JEVFISH_DATA_DIR", "").strip()
    if override:
        return Path(override).expanduser()
    return _user_data_home() / APP


def env_file() -> Path:
    """Where API keys are saved. Override with JEVFISH_ENV_FILE."""
    override = os.environ.get("JEVFISH_ENV_FILE", "").strip()
    return Path(override).expanduser() if override else data_dir() / ".env"
