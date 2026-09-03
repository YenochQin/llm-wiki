#!/usr/bin/env python3
"""Deprecated guard for the old direct-SQLite collection creator.

Collection writes must go through the Zotero Wiki Organizer plugin so Zotero
can maintain object caches, versions, and the sync queue. Use
``tools/zotero_client.py create`` instead.
"""

from __future__ import annotations

import sys


def main() -> int:
    print(
        "已停用：此脚本过去会直接修改 zotero.sqlite，可能破坏 Zotero 同步。\n"
        "请先安装 zotero_plugin/dist/zotero-wiki-organizer-*.xpi，"
        "再使用：\n"
        "  uv run python -X utf8 tools/zotero_client.py create --name \"分类名称\"",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
