## 2026-05-06
所有任务已完成。总结如下：

- `setup.sh --lang en` 运行正常：uv 构建了 `.venv`，全部 7 个工具导入成功，仅保留了预期的 `MINERU_API_TOKEN` 警告。
- `pyproject.toml` 现在显式包含了 `[build-system]` 和 `py-modules = []`，避免了 setuptools 尝试打包 `wiki/`、`raw/`、`i18n/` 等目录。
- `setup.sh` 的参数解析已重写为 POSIX 可移植（兼容 zsh）。
- 所有 4 处已去除的技能引用（`/exp-run`、`/exp-status`、`/paper-compile`、`/daily-arxiv`）以及 DeepXiv 提及已从 `i18n/en/skills/` 和 `CLAUDE.md` 中清除。`/init` 中的 `.tex-priority` 预处理语言及其引用已替换为 `mineru-md-canonical` 表述。
- `prepare_paper_source.py --help` 显示预期的 MinerU CLI 参数（`--source`、`--title`、`--arxiv-id`、`--backend api|local`）。
- Wiki 和 raw 目录结构保持完整（9 个 wiki 子目录、5 个 raw 子目录，以及 `index.md`/`log.md` 文件均存在）。

下一步：将一个真实的 PDF 放入 `raw/papers/`，设置 `MINERU_API_TOKEN`，然后通过 Claude Code 运行 `/ingest`，以端到端地测试整个流程。
