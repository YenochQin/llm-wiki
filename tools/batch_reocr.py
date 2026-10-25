#!/usr/bin/env python3
"""Rank already-ingested PDFs and reparse them locally with MinerU 4.

plan writes priority.md and queue.json; run writes resumable progress and staged
OCR outputs. Existing PDFs, canonical sources and knowledge pages are read-only.
The default parser is the tested MinerU 4 basic/auto mode, not forced page OCR.
"""

from __future__ import annotations

import argparse
import codecs
import contextlib
import hashlib
import importlib.metadata
import json
import os
import re
import selectors
import signal
import shutil
import subprocess
import sys
import time
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from _page_scan import markdown_pages
from urllib.parse import unquote

import frontmatter
import yaml
from _cli_io import configure_utf8_stdio
from _paths import DEFAULT_CONFIG_PATH, load_paths, resolve_runtime_path
from source_quality_lint import scan_text


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def atomic_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def metadata(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    try:
        return dict(frontmatter.loads(text).metadata), ""
    except (yaml.YAMLError, ValueError, TypeError) as exc:
        # Some source metadata includes broken symbols in its sections array.
        # Recover only independently valid scalar fields; never alter the file.
        fields = {}
        head = re.match(r"\A---\s*\n(.*?)\n---", text, re.DOTALL)
        if head:
            for match in re.finditer(r"^(source|title|sourceSlug|paperSlug|citationKey):\s*(.+)$", head[1], re.MULTILINE):
                try:
                    value = yaml.safe_load(match[2])
                    if isinstance(value, str):
                        fields[match[1]] = value
                except yaml.YAMLError:
                    pass
        return fields, f"metadata parse error: {type(exc).__name__}; scalar provenance only"


def normalized(value) -> str:
    return re.sub(r"[^\w]", "", str(value).casefold())


def source_paths(page: Path, meta: dict, wiki: Path) -> tuple[list[Path], list[str]]:
    source_root = (wiki / "sources/papers").resolve()
    text = page.read_text(encoding="utf-8")
    resolved, notes = set(), []
    for target in re.findall(r"\[prepared markdown\]\(([^)]+)\)", text):
        candidate = (page.parent / unquote(target.split("#")[0].strip().strip("<>"))).resolve()
        if not candidate.is_relative_to(source_root):
            notes.append(f"source link outside sources/papers: {target}")
        elif not candidate.is_file():
            notes.append(f"broken source link: {target}")
        else:
            resolved.add(candidate)
    if not resolved:
        explicit = meta.get("sourceSlug") or meta.get("source_slug")
        candidate = (source_root / f"{explicit or page.stem}.md").resolve()
        if candidate.is_relative_to(source_root) and candidate.is_file():
            m, _ = metadata(candidate)
            if explicit or normalized(m.get("title")) == normalized(meta.get("title")):
                resolved.add(candidate)
                notes.append("source recovered from explicit metadata" if explicit else "same-name source identity verified by title")
    return sorted(resolved), notes


def locate_pdf(value: str, zotero_roots: list[Path], raw: Path, project: Path) -> list[Path]:
    """Resolve exact provenance, including portable and migrated storage paths."""
    if not value:
        return []
    value = unquote(value).replace("\\", "/")
    value = re.sub(r"/+", "/", value)
    candidates = set()
    direct = Path(value).expanduser()
    if direct.is_absolute() and direct.is_file():
        candidates.add(direct.resolve())
    storage = re.search(r"(?:^|/)storage/([A-Z0-9]{8})/(.+)$", value)
    if storage:
        for root in zotero_roots:
            p = (root / "storage" / storage[1] / storage[2]).resolve()
            if p.is_relative_to((root / "storage").resolve()) and p.is_file():
                candidates.add(p)
    elif value.startswith("raw/"):
        p = (raw / value[4:]).resolve()
        if p.is_relative_to(raw.resolve()) and p.is_file():
            candidates.add(p)
    elif not direct.is_absolute() and not re.match(r"^[A-Za-z]:/", value):
        for base in (raw, project):
            p = (base / value).resolve()
            if p.is_relative_to(base.resolve()) and p.is_file():
                candidates.add(p)
    return sorted(p for p in candidates if p.suffix.lower() == ".pdf")


def build_plan(wiki: Path, raw: Path, project: Path, zotero_roots: list[Path], lookup=None) -> tuple[list[dict], list[dict]]:
    """Return a paper inventory and unique PDF jobs in importance order."""
    rows, jobs_by_hash = [], {}
    hash_cache = {}
    for page in sorted(markdown_pages((wiki / "papers"))):
        meta, warning = metadata(page)
        importance = meta.get("importance")
        valid = isinstance(importance, int) and not isinstance(importance, bool) and 1 <= importance <= 5
        row = {"paper": str(page.resolve()), "slug": page.stem,
               "title": meta.get("title") or page.stem, "importance": importance if valid else None,
               "notes": [warning] if warning else [], "job_ids": [], "sources": [], "status": "unresolved"}
        if not valid:
            row["notes"].append("importance missing/invalid; original value not changed")
        sources, notes = source_paths(page, meta, wiki)
        row["notes"].extend(notes)
        row["sources"] = [str(p) for p in sources]
        pdfs = set()
        unresolved = []
        for source in sources:
            source_meta, error = metadata(source)
            if error:
                row["notes"].append(f"{source.name}: {error}")
            candidates = locate_pdf(str(source_meta.get("source") or ""), zotero_roots, raw, project)
            if len(candidates) == 1:
                pdfs.add(candidates[0])
            elif len(candidates) > 1:
                row["notes"].append(f"ambiguous PDF provenance for {source.name}")
                unresolved.append(source)
            else:
                unresolved.append(source)
        if (not sources or unresolved) and lookup:
            # A unique exact bibliographic match may recover stale/missing paths.
            candidates = lookup(meta)
            if len(candidates) == 1 and len(sources) <= 1:
                pdfs.add(candidates[0])
                unresolved = []
                row["notes"].append("PDF recovered by exact Zotero DOI/title match")
        if unresolved:
            row["notes"].append("unresolved source PDFs: " + ", ".join(p.name for p in unresolved))
        if not pdfs:
            row["notes"].append("no uniquely resolved existing PDF")
        for pdf in sorted(pdfs):
            try:
                if pdf not in hash_cache:
                    hash_cache[pdf] = digest(pdf)
                sha = hash_cache[pdf]
                if sha not in jobs_by_hash:
                    import pypdfium2
                    doc = pypdfium2.PdfDocument(pdf)
                    try:
                        pages = len(doc)
                    finally:
                        doc.close()
                    jobs_by_hash[sha] = {"id": sha[:20], "pdf": str(pdf), "pdf_sha256": sha,
                                         "pages": pages, "importance": row["importance"], "papers": [], "sources": [],
                                         "label": page.stem, "title": row["title"]}
                job = jobs_by_hash[sha]
                job["importance"] = max(job["importance"] or 0, row["importance"] or 0) or None
                job["papers"].append(str(page.resolve()))
                job["sources"] = sorted(set(job["sources"]) | set(row["sources"]))
                row["job_ids"].append(job["id"])
            except (OSError, ValueError, RuntimeError) as exc:
                row["notes"].append(f"PDF cannot be read: {pdf}: {type(exc).__name__}")
        if row["job_ids"]:
            row["status"] = "partial" if unresolved else "ready"
        rows.append(row)
    rows.sort(key=lambda r: (-(r["importance"] or 0), r["slug"]))
    jobs = sorted(jobs_by_hash.values(), key=lambda j: (-(j["importance"] or 0), j["label"], j["id"]))
    for rank, row in enumerate(rows, 1):
        row["rank"] = rank
    for rank, job in enumerate(jobs, 1):
        job["rank"] = rank
    return rows, jobs


def exact_zotero_lookup(config_path: Path):
    import find_zotero_pdf

    def lookup(meta):
        external = meta.get("external_ids") or {}
        doi = str(external.get("DOI") or external.get("doi") or "").strip().lower() if isinstance(external, dict) else ""
        result = find_zotero_pdf.find(None, query=str(meta.get("title") or ""), doi=doi,
                                     item_key="", limit=5, config_path=config_path)
        candidates = set()
        for item in result.get("candidates", []):
            item_doi = str(item.get("doi") or "").strip().lower()
            exact = item_doi == doi if doi else normalized(item.get("title")) == normalized(meta.get("title"))
            if exact:
                candidates.update(Path(p).resolve() for p in item.get("pdf_paths", []) if Path(p).is_file())
        return sorted(candidates)
    return lookup


def priority_markdown(plan: dict) -> str:
    rows, jobs = plan["papers"], plan["jobs"]
    def cell(value):
        return str(value).replace("|", "\\|").replace("\n", " ").replace("\r", " ")
    by_id = {j["id"]: j for j in jobs}
    out = ["# 已 ingest 文献本地重新解析优先级", "",
           f"创建时间（UTC）：{plan['created_utc']}。按论文页现有 importance 从高到低，同分按文件名排序。", "",
           f"论文页：{len(rows)}；唯一 PDF：{len(jobs)}；PDF 总页数：{sum(j['pages'] for j in jobs)}。", "",
           "同一 PDF 内容只解析一次，执行重要性取对应页面的最高值。无效 importance 保留为空并排最后。",
           "使用 MinerU 4 basic/auto。只重新准备来源，不改写论文页、概念、claims，也不替换 canonical source。", "",
           f"结果目录：`{plan['output_root']}`。进度见 [progress.md](progress.md)。", "",
           "## PDF 执行顺序", "", "| 顺序 | Importance | 页数 | 文献 | PDF | 引用论文页数 |",
           "| ---: | ---: | ---: | --- | --- | ---: |"]
    for j in jobs:
        out.append(f"| {j['rank']} | {j['importance'] or '未设置'} | {j['pages']} | {cell(j['title'])} | [PDF](<{j['pdf']}>) | {len(j['papers'])} |")
    out += ["", "## 全部论文页与定位状态", "", "| 排名 | Importance | 论文页 | 状态 | PDF 执行序号 | 说明 |",
            "| ---: | ---: | --- | --- | --- | --- |"]
    for r in rows:
        ranks = ", ".join(str(by_id[i]["rank"]) for i in r["job_ids"])
        out.append(f"| {r['rank']} | {r['importance'] or '未设置'} | [{cell(r['slug'])}](<{r['paper']}>) | {r['status']} | {ranks or '—'} | {cell('; '.join(r['notes']))} |")
    return "\n".join(out) + "\n"


def save_progress(queue: Path, plan: dict, state: dict) -> None:
    state["updated_utc"] = now()
    atomic_json(queue / "progress.json", state)
    counts = Counter(v["status"] for v in state["jobs"].values())
    out = ["# 批量重新解析进度", "", f"更新时间（UTC）：{state['updated_utc']}", "",
           f"Worker PID：{state.get('pid', '—')}；状态：{state.get('status', 'pending')}。", "",
           f"统计：`{dict(counts)}`。原始 PDF、canonical sources 和知识页面保持只读。", "",
           "| 优先序号 | 文献 | 状态 | 结果／错误 |", "| ---: | --- | --- | --- |"]
    for j in plan["jobs"]:
        s = state["jobs"].get(j["id"], {"status": "pending"})
        detail = s.get("error", "")
        if s.get("result"):
            detail = f"[结果](<{s['result']}>)；质量疑点 {s.get('quality_issues', 0)}"
        out.append(f"| {j['rank']} | {j['label']} | {s['status']} | {str(detail).replace('|', '/').replace(chr(10), ' ')[:450]} |")
    tmp = queue / "progress.md.tmp"
    tmp.write_text("\n".join(out) + "\n", encoding="utf-8")
    tmp.replace(queue / "progress.md")


@contextlib.contextmanager
def worker_lock(queue: Path):
    # Advisory OS lock releases automatically even when the worker is killed.
    import fcntl
    with (queue / "worker.lock").open("a+") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("A worker is already running for this queue") from exc
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def extract_result(archive: Path, target: Path) -> tuple[Path, int]:
    with zipfile.ZipFile(archive) as z:
        for item in z.infolist():
            if not (target / item.filename).resolve().is_relative_to(target.resolve()):
                raise ValueError("Unsafe path in result archive")
        z.extractall(target)
    markdown = target / "markdown.md"
    middle = target / "middle_json.json"
    if not markdown.is_file() or not markdown.read_text(encoding="utf-8").strip():
        raise ValueError("MinerU returned no readable nonempty Markdown")
    data = json.loads(middle.read_text(encoding="utf-8"))
    if not isinstance(data.get("pages"), list):
        raise TypeError("MinerU middle JSON lacks page coverage")
    return markdown, len(data["pages"])


def completed_result(job: dict, root: Path, engine: dict) -> dict | None:
    path = root / job["id"] / "result.json"
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
        if result["pdf_sha256"] != job["pdf_sha256"] or result["engine"] != engine:
            return None
        if digest(Path(job["pdf"])) != job["pdf_sha256"]:
            return None
        if digest(Path(result["markdown"])) != result["markdown_sha256"]:
            return None
        return result
    except (OSError, ValueError, KeyError):
        return None


def validate_staging_root(output: Path, wiki: Path, raw: Path | None = None) -> Path:
    """Parser artifacts are disposable caches, never vault-visible sources."""
    output, wiki = output.resolve(), wiki.resolve()
    boundary = next((p for p in (wiki, *wiki.parents) if (p / ".obsidian").is_dir()), wiki)
    protected = [boundary] + ([raw.resolve()] if raw is not None else [])
    if any(output.is_relative_to(p) or p.is_relative_to(output) for p in protected):
        raise ValueError("OCR staging must be outside the wiki/Obsidian vault and raw inputs; use .checkpoints/reocr/<run>")
    return output


def relocate_queue(queue: Path, output: Path) -> dict:
    """Move an idle cache and repair receipt paths without changing OCR bytes."""
    queue = queue.resolve()
    with worker_lock(queue):
        plan = json.loads((queue / "queue.json").read_text(encoding="utf-8"))
        runtime = load_paths(config_path=Path(plan["paths_config"]) if plan.get("paths_config") else None)
        wiki = resolve_runtime_path("@configured", runtime, role="wiki", require_external=True)
        raw = resolve_runtime_path("@raw-root", runtime, role="raw", require_external=True)
        if wiki.resolve() != Path(plan["wiki_root"]).resolve():
            raise ValueError("Queue wiki no longer matches configuration")
        output = validate_staging_root(resolve_runtime_path(str(output), runtime, role="output"), wiki, raw)
        old = Path(plan["output_root"]).resolve()
        if output == old:
            return {"status": "unchanged", "output_root": str(output)}
        if output.is_relative_to(old) or old.is_relative_to(output) or queue.is_relative_to(old):
            raise ValueError("Cache relocation paths must not overlap")
        journal = queue / "relocation.json"
        recovering = False
        if output.exists():
            record = json.loads(journal.read_text()) if journal.exists() else {}
            recovering = (not old.exists() and record.get("from") == str(old) and record.get("to") == str(output))
            if not recovering:
                raise ValueError("Relocation destination already exists")
        if not recovering:
            expected = {j["id"] for j in plan["jobs"]}
            if not old.is_dir() or any(p.is_symlink() or not p.is_dir() or p.name not in expected for p in old.iterdir()):
                raise ValueError("Cache root contains unexpected entries; refusing to move it")
            atomic_json(journal, {"from": str(old), "to": str(output), "started_utc": now(), "original_plan": plan,
                                  "original_progress": json.loads((queue / "progress.json").read_text())})
            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(old), str(output))
        def moved(value):
            if not isinstance(value, str) or not Path(value).is_absolute():
                return value
            # Receipts may use an alias such as macOS /var -> /private/var.
            # Resolve non-strictly: the old cache has already been moved, or
            # may be absent while recovering an interrupted relocation.
            try:
                relative = Path(value).resolve().relative_to(old)
            except ValueError:
                return value
            return str(output / relative)
        receipts = 0
        for job in plan["jobs"]:
            receipt = output / job["id"] / "result.json"
            if not receipt.is_file():
                continue
            result = json.loads(receipt.read_text())
            for key in ("markdown", "quality_report"):
                if key in result:
                    result[key] = moved(result[key])
            if digest(Path(result["markdown"])) != result["markdown_sha256"]:
                raise ValueError(f"Relocated Markdown hash mismatch: {job['id']}")
            atomic_json(receipt, result)
            quality_path = Path(result.get("quality_report", ""))
            if quality_path.is_file():
                quality = json.loads(quality_path.read_text())
                quality["path"] = moved(quality.get("path"))
                atomic_json(quality_path, quality)
            receipts += 1
        state = json.loads((queue / "progress.json").read_text())
        for item in state["jobs"].values():
            if "result" in item:
                item["result"] = moved(item["result"])
        plan["output_root"] = str(output)
        atomic_json(queue / "queue.json", plan)
        (queue / "priority.md").write_text(priority_markdown(plan), encoding="utf-8")
        save_progress(queue, plan, state)
        record = json.loads(journal.read_text())
        record.update(status="completed", completed_utc=now(), receipts_verified=receipts)
        atomic_json(journal, record)
        return {"status": "relocated", "output_root": str(output), "receipts_verified": receipts}


def wait_with_output(proc, log, timeout: float) -> int:
    """Tee native progress to the terminal and log, retaining CR/UTF-8 output."""
    deadline = time.monotonic() + timeout if timeout else None
    decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
    with selectors.DefaultSelector() as selector:
        selector.register(proc.stdout, selectors.EVENT_READ)
        while True:
            remaining = deadline - time.monotonic() if deadline else None
            if remaining is not None and remaining <= 0:
                raise subprocess.TimeoutExpired(proc.args, timeout)
            if not selector.select(min(0.2, remaining) if remaining is not None else 0.2):
                continue
            chunk = os.read(proc.stdout.fileno(), 65536)
            if not chunk:
                break
            text = decoder.decode(chunk)
            log.write(text)
            log.flush()
            sys.stdout.write(text)
            sys.stdout.flush()
    tail = decoder.decode(b"", final=True)
    log.write(tail)
    sys.stdout.write(tail)
    sys.stdout.flush()
    remaining = max(0, deadline - time.monotonic()) if deadline else None
    return proc.wait(timeout=remaining)


def execute_job(job: dict, output: Path, engine: dict, executable: Path, mineru_home: Path, timeout: int,
                verbose: bool = False) -> dict:
    pdf = Path(job["pdf"])
    if digest(pdf) != job["pdf_sha256"]:
        raise ValueError("PDF has changed since planning; re-plan before parsing")
    job_dir = output / job["id"]
    job_dir.mkdir(parents=True, exist_ok=True)
    # Separate attempts preserve incomplete/failed diagnostics without mixing files.
    attempt = job_dir / ("attempt-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    attempt.mkdir()
    archive = attempt / "native.zip"
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", MINERU_HOME=str(mineru_home),
               MINERU_MODEL_SOURCE="local", MINERU_MODEL_SMALL_BACKEND="onnx",
               HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
    # Keep the dependency installation untouched. Successful old receipts remain
    # reusable; the guard changes only zero-area boxes that previously crashed.
    compat = executable.name == "mineru-kit" and engine["mineru_version"] == "4.0.12"
    launcher = [sys.executable, str(Path(__file__).with_name("mineru_compat_cli.py"))] if compat else [str(executable)]
    command = [*launcher, "parse", str(pdf), "--output", str(archive), "--format", "zip",
               "--tier", engine["tier"], "--ocr-mode", engine["ocr_mode"]]
    with (attempt / "mineru.log").open("w", encoding="utf-8") as log:
        proc = subprocess.Popen(command, stdout=subprocess.PIPE if verbose else log, stderr=subprocess.STDOUT, env=env)
        try:
            code = wait_with_output(proc, log, timeout) if verbose else proc.wait(timeout=timeout or None)
        except BaseException:
            proc.terminate()
            try:
                proc.wait(timeout=20)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
            raise
        finally:
            if proc.stdout is not None:
                proc.stdout.close()
    if code:
        tail = (attempt / "mineru.log").read_text(encoding="utf-8", errors="replace")[-1500:]
        raise RuntimeError(f"MinerU exit {code}; log: {attempt / 'mineru.log'}; {tail}")
    markdown, pages = extract_result(archive, attempt / "native")
    if pages != job["pages"]:
        raise ValueError(f"Incomplete page coverage: {pages}/{job['pages']}")
    if digest(pdf) != job["pdf_sha256"]:
        raise ValueError("PDF changed during parsing")
    quality = scan_text(markdown.read_text(encoding="utf-8"), path=markdown)
    atomic_json(attempt / "quality.json", quality)
    result = {"job_id": job["id"], "pdf": str(pdf), "pdf_sha256": job["pdf_sha256"],
              "engine": engine, "pages": pages, "papers": job["papers"], "previous_sources": job["sources"],
              "completed_utc": now(), "markdown": str(markdown), "markdown_sha256": digest(markdown),
              "quality_report": str(attempt / "quality.json"), "quality_issues": len(quality["issues"]),
              "quality_counts": dict(Counter(i["severity"] for i in quality["issues"])),
              "pdf_fidelity_verified": False}
    atomic_json(job_dir / "result.json", result)
    return result


def run_queue(args) -> dict:
    queue = args.queue_dir.resolve()
    plan = json.loads((queue / "queue.json").read_text(encoding="utf-8"))
    output = Path(plan["output_root"]).resolve()
    runtime = load_paths(config_path=Path(plan["paths_config"]) if plan.get("paths_config") else None)
    wiki = resolve_runtime_path("@configured", runtime, role="wiki", require_external=True)
    if wiki.resolve() != Path(plan["wiki_root"]).resolve():
        raise ValueError("Queue wiki no longer matches configuration")
    raw = resolve_runtime_path("@raw-root", runtime, role="raw", require_external=True)
    validate_staging_root(output, wiki, raw)
    executable = Path(sys.executable).parent / "mineru-kit"
    version = importlib.metadata.version("mineru")
    if version.split(".")[0] != "4" or not executable.is_file():
        raise RuntimeError("This runner requires MinerU 4 and mineru-kit in the current Python environment")
    engine = {"mineru_version": version, "tier": "basic", "ocr_mode": "auto", "small_backend": "onnx"}
    with worker_lock(queue):
        if json.loads((queue / "queue.json").read_text(encoding="utf-8")) != plan:
            raise RuntimeError("Queue changed before the worker lock was acquired; rerun the command")
        state_path = queue / "progress.json"
        state = json.loads(state_path.read_text()) if state_path.exists() else {"jobs": {}}
        for job in plan["jobs"]:
            state["jobs"].setdefault(job["id"], {"status": "pending"})
        state.update(pid=os.getpid(), status="running", engine=engine)
        (queue / "STOP").unlink(missing_ok=True)
        save_progress(queue, plan, state)
        attempts = 0
        try:
            for job in plan["jobs"]:
                if (queue / "STOP").exists():
                    state["status"] = "stopped"
                    break
                previous = state["jobs"][job["id"]]
                done = completed_result(job, output, engine)
                if done:
                    previous.update(status="completed", result=str(output / job["id"] / "result.json"), quality_issues=done["quality_issues"])
                    continue
                if previous["status"] == "failed" and not args.retry_failed:
                    continue
                if args.max_items and attempts >= args.max_items:
                    state["status"] = "paused_at_limit"
                    break
                attempts += 1
                previous.clear()
                previous.update(status="running", started_utc=now())
                save_progress(queue, plan, state)
                print(f"[{job['rank']}/{len(plan['jobs'])}] importance={job['importance']} pages={job['pages']} {job['label']}", flush=True)
                try:
                    result = execute_job(job, output, engine, executable, args.mineru_home.resolve(), args.timeout_seconds,
                                         verbose=getattr(args, "verbose", False))
                    previous.update(status="completed", finished_utc=now(), result=str(output / job["id"] / "result.json"), quality_issues=result["quality_issues"])
                except Exception as exc:  # noqa: BLE001 -- isolate document failures and preserve diagnostics
                    previous.update(status="failed", finished_utc=now(), error=str(exc))
                    print(f"failed: {job['label']}: {exc}", flush=True)
                save_progress(queue, plan, state)
            else:
                state["status"] = "finished_with_failures" if any(v["status"] == "failed" for v in state["jobs"].values()) else "finished"
        except KeyboardInterrupt:
            state["status"] = "interrupted"
            for item in state["jobs"].values():
                if item["status"] == "running":
                    item["status"] = "interrupted"
        finally:
            save_progress(queue, plan, state)
    return state


def worker_active(queue: Path) -> bool:
    """Probe the OS lock; PIDs may be namespaced in managed command sessions."""
    import fcntl
    path = queue / "worker.lock"
    if not path.exists():
        return False
    with path.open("r") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        fcntl.flock(stream, fcntl.LOCK_UN)
    return False


def verify_models(home: Path) -> None:
    executable = Path(sys.executable).parent / "mineru-kit"
    env = dict(os.environ, MINERU_HOME=str(home.resolve()), MINERU_MODEL_SOURCE="local",
               MINERU_MODEL_SMALL_BACKEND="onnx", PYTHONDONTWRITEBYTECODE="1")
    check = subprocess.run([str(executable), "models", "verify", "--tier", "basic", "--small-backend", "onnx"],
                           env=env, capture_output=True, text=True, check=False)
    if check.returncode:
        raise RuntimeError("Local model preflight failed: " + check.stdout[-1500:] + check.stderr[-1500:])


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    p = commands.add_parser("plan", help="Inventory existing paper pages and write a priority queue")
    p.add_argument("--queue-dir", type=Path, required=True)
    p.add_argument("--output-root", help="Outside-vault cache; default .checkpoints/reocr/<queue-directory-name>")
    p.add_argument("--paths-config", type=Path, default=DEFAULT_CONFIG_PATH)
    p = commands.add_parser("run", help="Run/resume the queue sequentially, using local models only")
    p.add_argument("--queue-dir", type=Path, required=True)
    p.add_argument("--mineru-home", type=Path, required=True)
    p.add_argument("--max-items", type=int, default=0, help="Attempt at most N PDFs; default 0 runs the full queue")
    p.add_argument("--timeout-seconds", type=int, default=0, help="Per-PDF timeout; default 0 means no time limit")
    p.add_argument("--retry-failed", action="store_true")
    p.add_argument("--verbose", action="store_true", help="Show native MinerU progress live while retaining per-document logs")
    p.add_argument("--background", action="store_true", help="Start a detached worker; inspect status/progress.md")
    for name in ("status", "stop"):
        p = commands.add_parser(name)
        p.add_argument("--queue-dir", type=Path, required=True)
    p = commands.add_parser("relocate", help="Move an idle staging cache outside the vault, preserving resumability")
    p.add_argument("--queue-dir", type=Path, required=True)
    p.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        queue = args.queue_dir.resolve()
        if args.command == "run" and (args.max_items < 0 or args.timeout_seconds < 0):
            raise ValueError("Limits must be nonnegative")
        if args.command == "run":
            verify_models(args.mineru_home)
        if args.command == "plan":
            import find_zotero_pdf
            runtime = load_paths(config_path=args.paths_config)
            wiki = resolve_runtime_path("@configured", runtime, role="wiki", require_external=True)
            raw = resolve_runtime_path("@raw-root", runtime, role="raw", require_external=True)
            output = (resolve_runtime_path(args.output_root, runtime, role="output") if args.output_root
                      else runtime.project_root / ".checkpoints/reocr" / queue.name)
            output = validate_staging_root(output, wiki, raw)
            if queue.is_relative_to(output):
                raise ValueError("The queue directory must not be inside its OCR output root")
            if (queue / "queue.json").exists():
                raise ValueError("Queue already exists; resume it or choose a new queue directory")
            roots, _ = find_zotero_pdf._candidate_roots_from_config(runtime.config_path)
            roots = sorted({r for r in roots if (r / "storage").is_dir()})
            rows, jobs = build_plan(wiki, raw, runtime.project_root, roots, exact_zotero_lookup(runtime.config_path))
            plan = {"schema_version": 1, "created_utc": now(), "wiki_root": str(wiki), "output_root": str(output),
                    "paths_config": str(runtime.config_path),
                    "papers": rows, "jobs": jobs}
            atomic_json(queue / "queue.json", plan)
            (queue / "priority.md").write_text(priority_markdown(plan), encoding="utf-8")
            state = {"status": "pending", "jobs": {j["id"]: {"status": "pending"} for j in jobs}}
            save_progress(queue, plan, state)
            print(json.dumps({"papers": len(rows), "pdfs": len(jobs), "pages": sum(j['pages'] for j in jobs),
                              "paper_statuses": dict(Counter(r['status'] for r in rows)), "priority": str(queue / 'priority.md')}, ensure_ascii=False))
        elif args.command == "relocate":
            print(json.dumps(relocate_queue(queue, args.output_root), ensure_ascii=False))
        elif args.command == "status":
            state = json.loads((queue / "progress.json").read_text())
            print(json.dumps({k: v for k, v in state.items() if k != "jobs"} | {
                "worker_active": worker_active(queue),
                "counts": dict(Counter(j["status"] for j in state["jobs"].values())),
                "active": {k: v for k, v in state["jobs"].items() if v["status"] == "running"}}, ensure_ascii=False, indent=2))
        elif args.command == "stop":
            (queue / "STOP").write_text(now(), encoding="utf-8")
            print("Stop requested; the worker will finish the current PDF, then stop.")
        elif args.background:
            cmd = [sys.executable, "-X", "utf8", str(Path(__file__).resolve()), "run", "--queue-dir", str(queue),
                   "--mineru-home", str(args.mineru_home.resolve()), "--max-items", str(args.max_items),
                   "--timeout-seconds", str(args.timeout_seconds)]
            if args.retry_failed:
                cmd.append("--retry-failed")
            if args.verbose:
                cmd.append("--verbose")
            with (queue / "worker.log").open("a", encoding="utf-8") as log:
                proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True)
            print(json.dumps({"worker_pid": proc.pid, "log": str(queue / 'worker.log')}, ensure_ascii=False))
        else:
            def interrupted(_signum, _frame):
                raise KeyboardInterrupt
            signal.signal(signal.SIGTERM, interrupted)
            state = run_queue(args)
            print(json.dumps({"status": state["status"]}, ensure_ascii=False))
            return 1 if state["status"] == "finished_with_failures" else 0
    except (OSError, ValueError, RuntimeError, ImportError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    configure_utf8_stdio()
    raise SystemExit(main())
