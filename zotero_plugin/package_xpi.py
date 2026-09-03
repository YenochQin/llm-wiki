#!/usr/bin/env python3
"""Package the Zotero Wiki Organizer plugin into an installable .xpi.

An .xpi is a zip archive with manifest.json at its root. This script only
uses the standard library so it runs with plain python3:

    uv run python -X utf8 zotero_plugin/package_xpi.py
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
def main() -> int:
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    version = manifest["version"]
    DIST.mkdir(parents=True, exist_ok=True)
    output = DIST / f"zotero-wiki-organizer-{version}.xpi"

    files = sorted([ROOT / "manifest.json", ROOT / "bootstrap.js", ROOT / "prefs.js", ROOT / "README.md"])
    files.extend(sorted((ROOT / "src").glob("*.js")))
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(ROOT).as_posix())

    print(f"packaged {len(files)} files -> {output}")
    for path in files:
        print(f"  {path.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
