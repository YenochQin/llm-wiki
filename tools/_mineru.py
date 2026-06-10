"""MinerU extraction backends used by `process_pdf.py`.

Two backends, both normalized to the same on-disk shape inside `cache_dir`:

    cache_dir/
        <stem>.md     # raw MinerU markdown
        <stem>.json   # MinerU content_list.json (renamed from <stem>_content_list.json)
        images/       # extracted figure/table crops referenced by the .md / .json

`extract(pdf, cache_dir, language, backend)` returns `(<stem>.md, <stem>.json)`
so the caller can hand the same paths it used to receive from the old
`mineru-open-api` CLI to `process_pdf.normalize_cache(...)` unchanged.

Backends:

- ``"api"``   — cloud client against ``mineru.net/api/v4`` using ``requests``.
                Token resolution is handled by ``tools/_env.py``:
                real environment variables first, then
                ``$XDG_CONFIG_HOME/llm-wiki/.env`` or
                ``~/.config/llm-wiki/.env``. Endpoint base overridable via
                ``MINERU_API_BASE`` in the same config file.
- ``"local"`` — calls ``mineru.cli.common.do_parse`` directly. Imports happen
                lazily so users on the api-only path don't need ``mineru[all]``.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
import tempfile
import time
import zipfile
from pathlib import Path

import _env  # noqa: F401 — load llm-wiki user config for MinerU keys

DEFAULT_API_BASE = "https://mineru.net/api/v4"
DEFAULT_MODEL_VERSION = "pipeline"
POLL_INTERVAL_SEC = 3
POLL_READ_TIMEOUT_SEC = 120
POLL_TIMEOUT_SEC = 30 * 60  # 30 minutes per PDF
DATA_ID_MAX_LENGTH = 128


def _config(name: str, default: str = "") -> str:
    """Resolve a setting after ``_env`` has loaded llm-wiki config."""
    return os.environ.get(name, "").strip() or default


def _is_mineru_content_json(path: Path) -> bool:
    name = path.name
    if name in {"api-task.json", "layout.json", "manifest.json"}:
        return False
    if name.endswith(("_middle.json", "_model.json")):
        return False
    return True


def _content_list_candidates(cache_dir: Path) -> list[Path]:
    names = ("content_list.json", "content_list_v2.json")
    candidates = [cache_dir / name for name in names if (cache_dir / name).exists()]
    candidates.extend(cache_dir.glob("*_content_list.json"))
    candidates.extend(cache_dir.glob("*_content_list_v2.json"))
    return sorted(set(candidates))


def _is_content_list_json(path: Path) -> bool:
    return path.name in {"content_list.json", "content_list_v2.json"} or path.name.endswith(
        ("_content_list.json", "_content_list_v2.json")
    )


def _existing_outputs(cache_dir: Path) -> tuple[Path, Path] | None:
    md_candidates = sorted(p for p in cache_dir.glob("*.md") if p.name != "full.md")
    json_candidates = sorted(
        (p for p in cache_dir.glob("*.json") if _is_mineru_content_json(p)),
        key=lambda p: (_is_content_list_json(p), p.name),
    )
    if md_candidates and json_candidates:
        return md_candidates[0], json_candidates[0]
    return None


def _safe_data_id(pdf: Path) -> str:
    """Return a MinerU API-safe data_id derived from the PDF filename.

    MinerU's cloud API documents data_id as limited to ASCII letters, digits,
    underscores, hyphens, and dots. Zotero filenames often contain spaces,
    Unicode punctuation, and non-Latin names, so using ``pdf.stem`` directly can
    make polling brittle even when upload succeeds.
    """
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", pdf.stem).strip("-.")
    if not safe:
        safe = "pdf"
    return safe[:DATA_ID_MAX_LENGTH].rstrip("-.") or "pdf"


def _write_api_task_state(cache_dir: Path, state: dict) -> None:
    (cache_dir / "api-task.json").write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _read_api_task_state(
    cache_dir: Path,
    *,
    api_base: str = "",
    model_version: str = "",
    language: str = "",
) -> dict | None:
    path = cache_dir / "api-task.json"
    if not path.exists():
        return None
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(state, dict):
        return None
    if not state.get("batch_id") or not state.get("data_id"):
        return None
    if api_base and state.get("api_base") and str(state.get("api_base")).rstrip("/") != api_base.rstrip("/"):
        return None
    if model_version and state.get("model_version") and state.get("model_version") != model_version:
        return None
    if language and state.get("language") and state.get("language") != language:
        return None
    return state


def extract(
    pdf: Path,
    cache_dir: Path,
    language: str,
    backend: str,
) -> tuple[Path, Path]:
    """Populate ``cache_dir`` with ``<stem>.md`` and ``<stem>.json`` (+ images/).

    Returns the two paths so the caller can run its existing manifest
    synthesis step. If both files are already present, returns them without
    calling either backend (cache hit).
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    cached = _existing_outputs(cache_dir)
    if cached is not None:
        print(f"cache hit: {cache_dir}", file=sys.stderr)
        return cached

    if backend == "api":
        _extract_via_api(pdf, cache_dir, language)
    elif backend == "local":
        _extract_via_local(pdf, cache_dir, language)
    else:
        raise ValueError(f"unknown backend: {backend!r} (expected 'api' or 'local')")

    found = _existing_outputs(cache_dir)
    if found is None:
        raise RuntimeError(
            f"backend={backend} produced no <stem>.md / <stem>.json in {cache_dir}"
        )
    return found


# ---------------------------------------------------------------------------
# api backend
# ---------------------------------------------------------------------------

def _extract_via_api(pdf: Path, cache_dir: Path, language: str) -> None:
    try:
        import requests
    except ImportError as exc:
        raise RuntimeError(
            "backend='api' requires `requests`. Install it with: "
            "uv pip install -e \".[api]\""
        ) from exc

    _extract_via_api_with_requests(requests, pdf, cache_dir, language)


def _extract_via_api_with_requests(requests_module, pdf: Path, cache_dir: Path, language: str) -> None:

    token = _config("MINERU_API_TOKEN")
    if not token:
        raise RuntimeError(
            "MINERU_API_TOKEN is not set. Put it in the environment or in "
            f"{_env.config_env_path()} (created from config/.env.example)."
        )
    api_base = _config("MINERU_API_BASE", DEFAULT_API_BASE).rstrip("/")
    model_version = _config("MINERU_MODEL_VERSION", DEFAULT_MODEL_VERSION)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    data_id = _safe_data_id(pdf)
    existing_task = _read_api_task_state(
        cache_dir,
        api_base=api_base,
        model_version=model_version,
        language=language,
    )
    if existing_task is not None:
        batch_id = str(existing_task["batch_id"])
        data_id = str(existing_task["data_id"])
        file_name = str(existing_task.get("file_name") or "")
        print(f"mineru api: resuming extraction (batch_id={batch_id})", file=sys.stderr)
        full_zip_url = _poll_batch_until_done(
            requests_module,
            api_base,
            headers,
            batch_id,
            data_id,
            file_name=file_name or None,
        )
        print(f"mineru api: downloading result zip", file=sys.stderr)
        _download_and_extract_zip(requests_module, full_zip_url, cache_dir, pdf.stem)
        return

    print(f"mineru api: requesting upload URL for {pdf.name}", file=sys.stderr)
    submit = requests_module.post(
        f"{api_base}/file-urls/batch",
        headers=headers,
        json={
            "files": [{"name": pdf.name, "data_id": data_id}],
            "model_version": model_version,
            "language": language,
        },
        timeout=60,
    )
    submit.raise_for_status()
    body = submit.json()
    if body.get("code") != 0:
        raise RuntimeError(f"mineru api submit failed: {body}")
    data = body["data"]
    batch_id = data["batch_id"]
    file_urls = data["file_urls"]
    if not file_urls:
        raise RuntimeError(f"mineru api returned no upload URLs: {body}")
    _write_api_task_state(
        cache_dir,
        {
            "batch_id": batch_id,
            "data_id": data_id,
            "file_name": pdf.name,
            "api_base": api_base,
            "model_version": model_version,
            "language": language,
            "submitted_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
    )

    print(f"mineru api: uploading PDF (batch_id={batch_id})", file=sys.stderr)
    with pdf.open("rb") as fh:
        put = requests_module.put(file_urls[0], data=fh, timeout=300)
    put.raise_for_status()

    print(f"mineru api: polling extraction (batch_id={batch_id})", file=sys.stderr)
    full_zip_url = _poll_batch_until_done(
        requests_module,
        api_base,
        headers,
        batch_id,
        data_id,
        file_name=pdf.name,
    )

    print(f"mineru api: downloading result zip", file=sys.stderr)
    _download_and_extract_zip(requests_module, full_zip_url, cache_dir, pdf.stem)


def _poll_batch_until_done(
    requests_module,
    api_base: str,
    headers: dict,
    batch_id: str,
    data_id: str,
    *,
    file_name: str | None = None,
) -> str:
    deadline = time.monotonic() + POLL_TIMEOUT_SEC
    last_progress = ""
    while time.monotonic() < deadline:
        try:
            resp = requests_module.get(
                f"{api_base}/extract-results/batch/{batch_id}",
                headers=headers,
                timeout=POLL_READ_TIMEOUT_SEC,
            )
        except _request_timeout_exceptions(requests_module):
            msg = f"  poll read timeout; retrying batch_id={batch_id}"
            if msg != last_progress:
                print(msg, file=sys.stderr)
                last_progress = msg
            time.sleep(POLL_INTERVAL_SEC)
            continue
        resp.raise_for_status()
        body = resp.json()
        if body.get("code") != 0:
            raise RuntimeError(f"mineru api poll failed: {body}")

        files = (body.get("data") or {}).get("extract_result") or []
        target = _extract_result_target(files, data_id, file_name)
        if target is None:
            time.sleep(POLL_INTERVAL_SEC)
            continue

        state = target.get("state")
        if state == "done":
            url = target.get("full_zip_url")
            if not url:
                raise RuntimeError(f"mineru api: state=done but no full_zip_url: {target}")
            return url
        if state in {"failed", "error"}:
            raise RuntimeError(f"mineru api extraction failed: {target}")

        progress = target.get("extract_progress") or {}
        msg = (
            f"  state={state} "
            f"pages={progress.get('extracted_pages', '?')}/{progress.get('total_pages', '?')}"
        )
        if msg != last_progress:
            print(msg, file=sys.stderr)
            last_progress = msg
        time.sleep(POLL_INTERVAL_SEC)

    raise RuntimeError(f"mineru api timed out after {POLL_TIMEOUT_SEC}s (batch_id={batch_id})")


def _extract_result_target(files: list[dict], data_id: str, file_name: str | None = None) -> dict | None:
    for item in files:
        if item.get("data_id") == data_id:
            return item
    if file_name:
        for item in files:
            if item.get("file_name") == file_name:
                return item
    if len(files) == 1:
        return files[0]
    return None


def _request_timeout_exceptions(requests_module) -> tuple[type[BaseException], ...]:
    exceptions = getattr(requests_module, "exceptions", None)
    timeout_types = [
        getattr(exceptions, "Timeout", None),
        getattr(exceptions, "ReadTimeout", None),
    ]
    return tuple(t for t in timeout_types if isinstance(t, type)) or (TimeoutError,)


def _download_and_extract_zip(
    requests_module,
    url: str,
    cache_dir: Path,
    stem: str,
) -> None:
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        with requests_module.get(url, stream=True, timeout=300) as resp:
            resp.raise_for_status()
            with tmp_path.open("wb") as fh:
                for chunk in resp.iter_content(chunk_size=1 << 20):
                    if chunk:
                        fh.write(chunk)
        with zipfile.ZipFile(tmp_path) as zf:
            zf.extractall(cache_dir)
    finally:
        tmp_path.unlink(missing_ok=True)

    _normalize_library_layout(cache_dir, stem)


# ---------------------------------------------------------------------------
# local backend
# ---------------------------------------------------------------------------

def _extract_via_local(pdf: Path, cache_dir: Path, language: str) -> None:
    try:
        from mineru.cli.common import do_parse, read_fn
    except ImportError as exc:
        raise RuntimeError(
            "backend='local' requires the mineru library. Install it with: "
            "uv pip install -e \".[local]\""
        ) from exc

    with tempfile.TemporaryDirectory(prefix="mineru-out-") as tmp_root:
        tmp_dir = Path(tmp_root)
        print(f"mineru local: parsing {pdf.name} (this may take a while)", file=sys.stderr)
        do_parse(
            output_dir=str(tmp_dir),
            pdf_file_names=[pdf.stem],
            pdf_bytes_list=[read_fn(pdf)],
            p_lang_list=[language],
            backend="pipeline",
            parse_method="auto",
        )
        produced = _find_library_output(tmp_dir, pdf.stem)
        for entry in produced.iterdir():
            dest = cache_dir / entry.name
            if dest.exists():
                if dest.is_dir():
                    shutil.rmtree(dest)
                else:
                    dest.unlink()
            shutil.move(str(entry), dest)

    _normalize_library_layout(cache_dir, pdf.stem)


def _find_library_output(tmp_dir: Path, stem: str) -> Path:
    """MinerU 2.x writes to <tmp>/<stem>/<method>/. Locate that subdir."""
    stem_dir = tmp_dir / stem
    if not stem_dir.is_dir():
        raise RuntimeError(f"mineru produced no output for stem={stem!r} in {tmp_dir}")
    for method in ("auto", "ocr", "txt"):
        candidate = stem_dir / method
        if candidate.is_dir():
            return candidate
    subdirs = [p for p in stem_dir.iterdir() if p.is_dir()]
    if len(subdirs) == 1:
        return subdirs[0]
    raise RuntimeError(f"could not locate mineru output method dir under {stem_dir}")


def _normalize_library_layout(cache_dir: Path, stem: str) -> None:
    """Coerce MinerU output (any backend) into the canonical cache shape.

    The downstream ``synthesize_manifest`` looks for exactly one ``<stem>.md``
    plus one non-manifest ``.json``. The various MinerU sources name those
    files differently:

    - ``mineru.cli.common.do_parse`` (local)  → ``<stem>.md`` + ``<stem>_content_list.json``
    - ``mineru.net`` cloud ZIP                → ``full.md`` + ``<task-uuid>_content_list.json``
    - MinerU 2.x pipeline output              → ``full.md`` + ``<task-uuid>_content_list_v2.json``

    Either way, after this function runs the cache contains exactly one
    ``<stem>.md`` and one ``<stem>.json`` that the manifest synthesizer can
    pick up. Debug artifacts (``<*>_middle.json``, ``<*>_model.json``,
    ``layout.json``, ``<*>_origin.pdf``, ``layout.pdf``, ``spans.pdf``) are
    removed so they don't confuse the cache-discovery glob.
    """
    canonical_md = cache_dir / f"{stem}.md"
    canonical_json = cache_dir / f"{stem}.json"

    if not canonical_md.exists():
        full_md = cache_dir / "full.md"
        if full_md.exists():
            shutil.copy2(full_md, canonical_md)
        else:
            stem_md = next(
                (p for p in cache_dir.glob("*.md") if p.name not in {"full.md", canonical_md.name}),
                None,
            )
            if stem_md is not None:
                stem_md.rename(canonical_md)

    if not canonical_json.exists():
        candidates = _content_list_candidates(cache_dir)
        if len(candidates) == 1:
            candidates[0].rename(canonical_json)
        elif len(candidates) > 1:
            stem_match = next(
                (
                    p
                    for p in (
                        cache_dir / f"{stem}_content_list.json",
                        cache_dir / f"{stem}_content_list_v2.json",
                    )
                    if p in candidates
                ),
                None,
            )
            if stem_match in candidates:
                stem_match.rename(canonical_json)
            else:
                # Stem-match failed (common with cloud UUIDs + non-ASCII stems).
                # Prefer v1 content_list; keep v2 as fallback when v1 is absent.
                v1_candidates = [p for p in candidates if not p.name.endswith("_content_list_v2.json")]
                if len(v1_candidates) == 1:
                    v1_candidates[0].rename(canonical_json)
                elif len(v1_candidates) == 0 and len(candidates) == 1:
                    candidates[0].rename(canonical_json)
                else:
                    names = ", ".join(p.name for p in candidates)
                    raise RuntimeError(
                        f"ambiguous content list JSON files in {cache_dir} ({names}); "
                        "delete the cache directory and re-run, or rename the correct one to "
                        f"{canonical_json.name}"
                    )

    debug_globs = [
        "*_middle.json",
        "*_model.json",
        "*_origin.pdf",
        "layout.json",
        "layout.pdf",
        "spans.pdf",
    ]
    for pattern in debug_globs:
        for path in cache_dir.glob(pattern):
            try:
                path.unlink()
            except OSError:
                pass
