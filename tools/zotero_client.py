#!/usr/bin/env python3
"""Local HTTP client for the Zotero Wiki Organizer plugin.

All collection writes go through the plugin's endpoints on Zotero's
loopback-only connector server; this tool never opens or modifies
zotero.sqlite.

The plugin (zotero_plugin/) must be installed in Zotero first. Token and
endpoint come from flags, environment variables, or a token file:

    export ZOTERO_WIKI_ORGANIZER_TOKEN=...            # from <dataDir>/wiki-organizer-token.txt
    export ZOTERO_WIKI_ORGANIZER_URL=http://127.0.0.1:23119   # default

Usage:

    uv run python -X utf8 tools/zotero_client.py health
    uv run python -X utf8 tools/zotero_client.py list [--json]
    uv run python -X utf8 tools/zotero_client.py create --name "Wiki Documents"
    uv run python -X utf8 tools/zotero_client.py create \\
        --name "Relativistic Atomic Structure" --parent "Wiki Documents"
    uv run python -X utf8 tools/zotero_client.py inspect [--keys KEY1,KEY2]
    uv run python -X utf8 tools/zotero_client.py find-doi 10.xxxx/xxxxx
"""

from __future__ import annotations

import _env  # noqa: F401  side-effect import: loads ~/.config/llm-wiki/.env first

import argparse
import json
import os
import platform
import re
import sys
from pathlib import Path
from urllib.parse import quote, urlsplit

import requests

PLUGIN_PREFIX = "/wiki-organizer/v1"
DEFAULT_BASE_URL = "http://127.0.0.1:23119"
BASE_URL_ENV = "ZOTERO_WIKI_ORGANIZER_URL"
TOKEN_ENV = "ZOTERO_WIKI_ORGANIZER_TOKEN"
TOKEN_FILE_ENV = "ZOTERO_WIKI_ORGANIZER_TOKEN_FILE"
LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}

EXIT_OK = 0
EXIT_CLIENT = 1
EXIT_SERVER = 2


class ClientError(Exception):
    """Configuration or connection problem, with a user-facing message."""


class ServerError(Exception):
    """Server returned an error status, with a user-facing message."""


def _stdout_utf8() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass


def _read_token_file(path: str) -> str:
    try:
        lines = [line.strip() for line in Path(path).read_text(encoding="utf-8").splitlines()]
    except OSError as exc:
        raise ClientError(f"无法读取 token 文件 {path}: {exc}") from exc
    for line in lines:
        if line.lower().startswith("token:"):
            value = line.split(":", 1)[1].strip()
            if value:
                return value
    for line in lines:
        if line and not line.startswith("#"):
            return line
    raise ClientError(f"token 文件 {path} 中没有找到 token")


TOKEN_PREF_PATTERN = re.compile(
    r'user_pref\("extensions\.zotero\.wikiOrganizer\.token",\s*"([^"]+)"\)'
)


def _token_from_zotero_prefs(profile_root: Path | None = None) -> str | None:
    """Read the token straight from the Zotero profile's prefs.js.

    The preference is the authoritative token storage, so this fallback lets
    the client work with zero configuration when the convenience token file
    has not been written yet.
    """
    roots = [profile_root] if profile_root is not None else _zotero_profile_roots()
    for root in roots:
        token = _token_from_profile_root(root)
        if token:
            return token
    return None


def _zotero_profile_roots() -> list[Path]:
    system = platform.system()
    if system == "Darwin":
        return [Path.home() / "Library" / "Application Support" / "Zotero" / "Profiles"]
    if system == "Windows":
        appdata = os.environ.get("APPDATA")
        return [Path(appdata) / "Zotero" / "Zotero" / "Profiles"] if appdata else []
    return [Path.home() / ".zotero" / "zotero"]


def _token_from_profile_root(root: Path) -> str | None:
    try:
        candidates = sorted(root.glob("*/prefs.js"))
    except OSError:
        return None
    for prefs in candidates:
        try:
            match = TOKEN_PREF_PATTERN.search(
                prefs.read_text(encoding="utf-8", errors="replace")
            )
        except OSError:
            continue
        if match:
            return match.group(1)
    return None


def _load_token(args: argparse.Namespace) -> str:
    token = (getattr(args, "token", None) or os.environ.get(TOKEN_ENV, "")).strip()
    if token:
        return token
    token_file = (
        getattr(args, "token_file", None) or os.environ.get(TOKEN_FILE_ENV, "")
    ).strip()
    if token_file:
        return _read_token_file(token_file)
    token = _token_from_zotero_prefs()
    if token:
        return token
    raise ClientError(
        "缺少 token。请任选一种方式提供：\n"
        f"  1. export {TOKEN_ENV}=<token>（token 位于 Zotero 数据目录的 wiki-organizer-token.txt）\n"
        f"  2. export {TOKEN_FILE_ENV}=/path/to/wiki-organizer-token.txt\n"
        "  3. 命令行参数 --token 或 --token-file\n"
        "  4. 什么都不做：已自动尝试读取 ~/.zotero/zotero/*/prefs.js 中的"
        " extensions.zotero.wikiOrganizer.token（读取失败，请确认 Zotero 已启动过插件）"
    )


def _resolve_base_url(args: argparse.Namespace) -> str:
    base = (
        getattr(args, "url", None) or os.environ.get(BASE_URL_ENV, "") or DEFAULT_BASE_URL
    ).strip()
    parts = urlsplit(base)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise ClientError(f"endpoint 地址格式无效：{base}")
    host = parts.hostname.lower()
    if host not in LOOPBACK_HOSTS:
        raise ClientError(
            f"已拒绝非 loopback 地址 {host}：插件端点只应通过本机访问。\n"
            "请使用 127.0.0.1、localhost 或 ::1。"
        )
    return base.rstrip("/")


def _request(
    method: str,
    path: str,
    token: str,
    base_url: str,
    *,
    json_body: dict | None = None,
    timeout: tuple[float, float] = (5.0, 60.0),
) -> tuple[int, object]:
    url = base_url + path
    headers = {
        "Authorization": f"Bearer {token}",
        # Zotero silently drops requests that look like a browser unless
        # this marker header is present (verified against server.js).
        "Zotero-Allowed-Request": "1",
        "User-Agent": "llm-wiki-zotero-client/0.1",
    }
    try:
        response = requests.request(
            method, url, headers=headers, json=json_body, timeout=timeout
        )
    except requests.exceptions.ConnectionError as exc:
        raise ClientError(
            f"无法连接 Zotero 本地服务器 {base_url}：请确认 Zotero 正在运行且插件已安装"
            f"（{exc.__class__.__name__}）"
        ) from exc
    except requests.exceptions.Timeout as exc:
        raise ClientError(f"请求 {url} 超时：Zotero 可能仍在启动中或已无响应。") from exc
    try:
        payload = response.json()
    except ValueError:
        payload = {"raw": response.text}
    return response.status_code, payload


def _raise_server_error(status: int, payload: object) -> None:
    message = ""
    if isinstance(payload, dict):
        message = str(payload.get("message") or payload.get("error") or "")
    suffix = f"：{message}" if message else ""
    hints = {
        400: f"请求参数错误{suffix}",
        401: "token 缺失或错误：请核对 Zotero 数据目录 wiki-organizer-token.txt 中的 token"
        "与环境变量设置。",
        404: "端点不存在（404）：插件未安装或版本过旧，请先安装 zotero_plugin/dist 下的 xpi。",
        409: f"同名冲突{suffix}",
        500: f"Zotero 内部事务失败{suffix}。不要自动重试写入，请先用 list 确认当前状态。",
        503: "Zotero 尚未完成启动或对象服务不可用，请稍后重试。",
    }
    raise ServerError(f"HTTP {status}：{hints.get(status, f'服务端错误{suffix}')}")


def _object_payload(payload: object, operation: str) -> dict:
    if not isinstance(payload, dict):
        raise ServerError(f"{operation}：Zotero 插件返回了非 JSON 对象响应。")
    return payload


def normalize_doi(value: str) -> str:
    """Normalize DOI variants for exact comparison, not fuzzy search."""
    doi = str(value or "").strip().lower()
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi)
    doi = re.sub(r"^doi:\s*", "", doi)
    return doi.rstrip(" .")


def find_items_by_doi(doi: str, *, base_url: str | None = None) -> list[dict]:
    """Find all top-level Zotero items whose data.DOI exactly matches DOI.

    Zotero's q search is intentionally not trusted for DOI de-duplication:
    it may omit records depending on indexing state. This scans paginated item
    data and compares normalized DOI values exactly before any import.
    """
    wanted = normalize_doi(doi)
    if not wanted:
        raise ClientError("DOI 不能为空")
    base = _resolve_base_url(argparse.Namespace(url=base_url or DEFAULT_BASE_URL))
    matches: list[dict] = []
    start = 0
    while True:
        url = f"{base}/api/users/0/items/top?include=data&limit=100&start={start}"
        try:
            response = requests.get(
                url,
                headers={"Zotero-Allowed-Request": "1", "User-Agent": "llm-wiki-zotero-client/0.1"},
                timeout=(5.0, 30.0),
            )
        except requests.exceptions.RequestException as exc:
            raise ClientError(f"无法查询 Zotero 条目：{exc}") from exc
        if response.status_code != 200:
            raise ServerError(f"Zotero 条目查询失败（HTTP {response.status_code}）")
        rows = response.json()
        if not isinstance(rows, list):
            raise ServerError("Zotero 条目查询返回了非数组响应")
        for row in rows:
            data = row.get("data", {}) if isinstance(row, dict) else {}
            if normalize_doi(data.get("DOI", "")) == wanted:
                matches.append(data)
        if len(rows) < 100:
            break
        start += len(rows)
    return matches


def cmd_find_doi(args: argparse.Namespace) -> int:
    matches = find_items_by_doi(args.doi, base_url=args.url)
    if args.json:
        print(json.dumps(matches, ensure_ascii=False, indent=2))
    elif matches:
        for item in matches:
            print(f"{item.get('key')}: {item.get('title')} (DOI={item.get('DOI')})")
    else:
        print("未找到该 DOI 的 Zotero 条目。")
    return EXIT_OK


def cmd_health(args: argparse.Namespace) -> int:
    token = _load_token(args)
    base = _resolve_base_url(args)
    status, payload = _request(
        "GET", f"{PLUGIN_PREFIX}/health", token, base, timeout=(3.0, 15.0)
    )
    if status != 200:
        _raise_server_error(status, payload)
    payload = _object_payload(payload, "健康检查失败")
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return EXIT_OK
    print(f"状态: {payload.get('status')}")
    print(f"插件版本: {payload.get('pluginVersion')}")
    print(f"Zotero 版本: {payload.get('zoteroVersion')}")
    print(f"个人库 libraryID: {payload.get('libraryID')}")
    print(f"collection 数量: {payload.get('collectionCount')}")
    return EXIT_OK


def _print_tree(collections: list[dict]) -> None:
    by_key = {record["key"]: record for record in collections}
    children: dict[str | None, list[dict]] = {}
    for record in collections:
        parent_key = record.get("parentKey")
        # A dangling parent key (e.g. legacy direct-SQLite rows) displays at
        # the top level instead of disappearing.
        if parent_key and parent_key not in by_key:
            parent_key = None
        children.setdefault(parent_key, []).append(record)

    def emit(parent_key: str | None, depth: int) -> None:
        for record in sorted(
            children.get(parent_key, []),
            key=lambda r: ((r.get("name") or ""), r.get("key") or ""),
        ):
            orphan = (
                "  [orphan: parent key not found]"
                if record.get("parentKey") and record["parentKey"] not in by_key
                else ""
            )
            print(
                f"{'  ' * depth}- {record.get('name')}  key={record.get('key')}"
                f" id={record.get('collectionID')} items={record.get('itemCount')}"
                f" version={record.get('version')}{orphan}"
            )
            emit(record["key"], depth + 1)

    emit(None, 0)


def cmd_list(args: argparse.Namespace) -> int:
    token = _load_token(args)
    base = _resolve_base_url(args)
    status, payload = _request("GET", f"{PLUGIN_PREFIX}/collections", token, base)
    if status != 200:
        _raise_server_error(status, payload)
    payload = _object_payload(payload, "collection 查询失败")
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return EXIT_OK
    print(f"个人库 libraryID={payload.get('libraryID')}，共 {payload.get('count')} 个 collection：")
    _print_tree(payload.get("collections") or [])
    return EXIT_OK


def cmd_create(args: argparse.Namespace) -> int:
    name = (args.name or "").strip()
    if not name:
        raise ClientError("--name 不能为空")
    parent = (args.parent or "").strip() or None
    if args.parent_key and parent:
        raise ClientError("--parent 与 --parent-key 只能二选一")

    body: dict = {"name": name, "mode": "create-if-missing"}
    if args.parent_key:
        body["parentKey"] = args.parent_key.strip()
    else:
        body["parent"] = parent

    token = _load_token(args)
    base = _resolve_base_url(args)
    status, payload = _request(
        "POST", f"{PLUGIN_PREFIX}/collections", token, base, json_body=body
    )
    if status != 200:
        _raise_server_error(status, payload)
    payload = _object_payload(payload, "collection 创建失败")

    if args.json:
        # Verify before emitting the machine-readable success response.
        status2, payload2 = _request("GET", f"{PLUGIN_PREFIX}/collections", token, base)
        if status2 != 200:
            print(f"写后验证查询失败（HTTP {status2}）。", file=sys.stderr)
            return EXIT_SERVER
        payload2 = _object_payload(payload2, "写后验证失败")
        keys = {c.get("key") for c in (payload2.get("collections") or [])}
        if payload.get("key") not in keys:
            print("写后验证失败：创建响应中的 key 未出现在查询结果中。", file=sys.stderr)
            return EXIT_SERVER
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return EXIT_OK
    outcome = "已创建" if payload.get("created") else "已存在（幂等复用，未新建）"
    print(f"{outcome}: {payload.get('name')}")
    print(
        f"  key={payload.get('key')}  collectionID={payload.get('collectionID')}"
        f"  version={payload.get('version')}"
    )
    parent_line = f"  parent={payload.get('parent') or '(顶层)'}"
    if payload.get("parentKey"):
        parent_line += f"  parentKey={payload.get('parentKey')}"
    print(parent_line)
    if payload.get("note"):
        print(f"  注意: {payload['note']}")

    # Plan §8: after a write, verify with a read before reporting success.
    status2, payload2 = _request("GET", f"{PLUGIN_PREFIX}/collections", token, base)
    if status2 != 200:
        print(f"警告: 写后验证查询失败（HTTP {status2}），写入结果未经二次确认。", file=sys.stderr)
        return EXIT_SERVER
    payload2 = _object_payload(payload2, "写后验证失败")
    keys = {c.get("key") for c in (payload2.get("collections") or [])}
    if payload.get("key") in keys:
        print("验证: 写后查询已确认该 key 存在。")
        return EXIT_OK
    raise ServerError(
        f"验证失败：创建响应中的 key={payload.get('key')} 在写后查询中不存在。"
        "请先用 list 检查实际状态，不要直接重试创建。"
    )


def cmd_inspect(args: argparse.Namespace) -> int:
    token = _load_token(args)
    base = _resolve_base_url(args)
    path = f"{PLUGIN_PREFIX}/migration/inspect"
    if args.keys:
        path += "?keys=" + quote(args.keys)
    status, payload = _request("GET", path, token, base)
    if status != 200:
        _raise_server_error(status, payload)
    payload = _object_payload(payload, "迁移审计失败")
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return EXIT_OK
    requested = payload.get("requestedKeys") or []
    print(f"迁移审计（只读）。请求 {len(requested)} 个 key：")
    for record in payload.get("found") or []:
        print(
            f"  找到 {record['key']}: name={record['name']!r}"
            f" library={record.get('libraryName')}"
            f" id={record.get('collectionID')} version={record.get('version')}"
            f" items={record.get('itemCount')}"
            f" parent={record.get('parentName') or '-'}"
        )
    for key in payload.get("missing") or []:
        print(f"  缺失 {key}（本地库中不存在）")
    print("说明: 本端点只读；任何删除/重建都必须按 plan §9 单独确认后执行。")
    return EXIT_OK


def assign_items(assignments: list[dict], *, token: str | None = None,
                 base_url: str | None = None) -> dict:
    """Add item memberships through the plugin and return its verified result."""
    if not assignments:
        raise ClientError("assignments 不能为空")
    token = token or _load_token(argparse.Namespace(token=None, token_file=None))
    # Keep the public helper subject to the same loopback policy as CLI paths.
    base_url = _resolve_base_url(
        argparse.Namespace(url=base_url or DEFAULT_BASE_URL)
    )
    status, payload = _request(
        "POST", f"{PLUGIN_PREFIX}/items/assign", token, base_url,
        json_body={"mode": "add", "assignments": assignments},
    )
    if status != 200:
        _raise_server_error(status, payload)
    return _object_payload(payload, "条目分类追加失败")


def cmd_assign(args: argparse.Namespace) -> int:
    try:
        assignments = json.loads(Path(args.file).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ClientError(f"无法读取 assignments JSON：{exc}") from exc
    if isinstance(assignments, dict):
        assignments = assignments.get("assignments")
    if not isinstance(assignments, list):
        raise ClientError("JSON 必须是 assignments 数组，或包含 assignments 数组的对象")
    token = _load_token(args)
    base = _resolve_base_url(args)
    payload = assign_items(assignments, token=token, base_url=base)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        changed = sum(1 for r in payload.get("results", []) if r.get("changed"))
        print(f"已处理 {payload.get('count', 0)} 个条目，新增分类归属 {changed} 个。")
        for r in payload.get("results", []):
            added = ", ".join(r.get("addedCollectionKeys", [])) or "（无新增）"
            print(f"  {r.get('itemKey')}: {added}")
    return EXIT_OK


def cmd_erase_legacy(args: argparse.Namespace) -> int:
    """Erase only the allow-listed, empty legacy collections."""
    token = _load_token(args)
    base = _resolve_base_url(args)
    keys = [key.strip() for key in (args.keys or "").split(",") if key.strip()]
    body = {"confirmation": args.confirm}
    if keys:
        body["keys"] = keys
    status, payload = _request(
        "POST", f"{PLUGIN_PREFIX}/migration/erase", token, base, json_body=body
    )
    if status != 200:
        _raise_server_error(status, payload)
    payload = _object_payload(payload, "历史 collection 清理失败")
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return EXIT_OK
    removed = payload.get("removed") or []
    missing = payload.get("missing") or []
    print(f"已通过 Zotero eraseTx() 移除 {len(removed)} 个历史空 collection。")
    for record in removed:
        print(f"  移除 {record.get('key')}: {record.get('name')} (id={record.get('collectionID')})")
    for key in missing:
        print(f"  已不存在：{key}")
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--url",
        help=f"插件 endpoint 基地址（默认 {DEFAULT_BASE_URL}，或环境变量 {BASE_URL_ENV}）",
    )
    common.add_argument("--token", help=f"认证 token（默认取环境变量 {TOKEN_ENV}）")
    common.add_argument(
        "--token-file", help=f"token 文件路径（默认取环境变量 {TOKEN_FILE_ENV}）"
    )

    parser = argparse.ArgumentParser(
        prog="zotero_client",
        description="Zotero Wiki Organizer 插件的本地客户端（详见 zotero_plugin/README.md）",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    health = subparsers.add_parser(
        "health", parents=[common], help="健康检查（确认插件与 Zotero 就绪）"
    )
    health.add_argument("--json", action="store_true", help="输出原始 JSON")
    health.set_defaults(func=cmd_health)

    list_cmd = subparsers.add_parser(
        "list", parents=[common], help="列出个人库 collection 树"
    )
    list_cmd.add_argument("--json", action="store_true", help="输出原始 JSON")
    list_cmd.set_defaults(func=cmd_list)

    create = subparsers.add_parser(
        "create", parents=[common], help="幂等创建 collection（create-if-missing）"
    )
    create.add_argument("--name", required=True, help="collection 名称（必填）")
    create.add_argument(
        "--parent", help="父 collection 名称或 '/' 分隔路径（省略则创建顶层）"
    )
    create.add_argument("--parent-key", help="父 collection 的 8 位 key（与 --parent 互斥）")
    create.add_argument("--json", action="store_true", help="输出原始 JSON")
    create.set_defaults(func=cmd_create)

    inspect = subparsers.add_parser(
        "inspect", parents=[common], help="只读审计历史问题 collection key（plan §9）"
    )
    inspect.add_argument("--keys", help="逗号分隔的 key 列表（默认 plan §2.2 的 7 个 key）")
    inspect.add_argument("--json", action="store_true", help="输出原始 JSON")
    inspect.set_defaults(func=cmd_inspect)

    find_doi = subparsers.add_parser(
        "find-doi", parents=[common], help="按 DOI 精确查找已有 Zotero 条目（导入前预检）"
    )
    find_doi.add_argument("doi", help="DOI（支持 doi: 和 https://doi.org/ 前缀）")
    find_doi.add_argument("--json", action="store_true", help="输出原始 JSON")
    find_doi.set_defaults(func=cmd_find_doi)

    assign = subparsers.add_parser(
        "assign", parents=[common], help="以追加方式将条目加入 collection（不移除已有归属）"
    )
    assign.add_argument("--file", required=True, help="assignments JSON 文件路径")
    assign.add_argument("--json", action="store_true", help="输出原始 JSON")
    assign.set_defaults(func=cmd_assign)

    erase = subparsers.add_parser(
        "erase-legacy",
        parents=[common],
        help="删除已核实为空的历史 collection（必须显式确认）",
    )
    erase.add_argument(
        "--confirm",
        required=True,
        help="必须为 ERASE_LEGACY_COLLECTIONS；仅允许删除内置的 7 个历史 key",
    )
    erase.add_argument("--keys", help="可选的逗号分隔 key 子集；省略则处理全部 7 个")
    erase.add_argument("--json", action="store_true", help="输出原始 JSON")
    erase.set_defaults(func=cmd_erase_legacy)

    return parser


def main(argv: list[str] | None = None) -> int:
    _stdout_utf8()
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (ClientError, ServerError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return EXIT_CLIENT if isinstance(exc, ClientError) else EXIT_SERVER
    except requests.exceptions.RequestException as exc:
        print(f"错误: 网络请求异常: {exc}", file=sys.stderr)
        return EXIT_CLIENT


if __name__ == "__main__":
    raise SystemExit(main())
