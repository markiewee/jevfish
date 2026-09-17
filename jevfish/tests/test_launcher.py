import re

from jevfish.config import PACKAGE_ROOT


def test_built_web_app_is_present():
    dist = PACKAGE_ROOT / "web" / "dist"
    html = (dist / "index.html").read_text()
    assets = re.findall(r'(?:src|href)="/(assets/[^"]+)"', html)
    assert assets and all((dist / a).is_file() for a in assets)
