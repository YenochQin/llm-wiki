# PROJECT_STATE.md

最后核验：2026-10-25T10:44:40+08:00（Asia/Singapore）；macOS 路径修复验证快照，后续提交/推送结果以 Git 历史及远端查询确认。

文件定位：本项目实际使用的状态与交接文件，路径为 `docs/templates/PROJECT_STATE.md`，由根目录 `AGENTS.md` 引用并规定读取和维护时机。文件结构参考用户提供的 Downloads/PROJECT_STATE.md 模板；此文件虽位于模板目录，但持续记录实际项目状态，不是指令或授权来源。以下路径除 Markdown 链接外均相对于项目根目录。

填写约定：未知写“未知”，未检查写“未核验”，不适用写“不适用”。本文件只记录核验时点的情况，恢复工作前需重新检查。

## 1. 研究目标

- 项目名称：`llm-wiki`。仓库自述为个人 LLM 维护的研究知识库，支持 Codex 与 Claude Code，采用 MinerU 进行 PDF 预处理；这是文档声明，实际集成可用性未核验。来源：[README.md](../../README.md) 开头及 Requirements。
- 核心问题与研究范围：仓库用于维护研究知识与相关工作流；具体科研课题、研究问题、假设及数据范围未知。来源：[README.md](../../README.md) Architecture；本次未检查外部研究内容。
- 当前阶段与本阶段交付物：修复 batch_reocr 在 macOS 默认临时路径别名下的四项测试失败，验证后提交并推送。科研项目实际阶段未核验。
- 完成标准 / 已确认的截止日期：默认 macOS 临时目录无需 TMPDIR 覆盖即可通过相关测试；路径迁移及中断恢复正确，不放宽不同 wiki 根目录的保护；提交推送后核对 main 一致且工作区干净。截止日期未知。

## 2. 当前进展与证据

- 已完成：上一轮双方提交已合并为 `3b248ad` 并推送，实时远端查询当时确认一致。本轮修复 `tools/batch_reocr.py`：以规范化路径比较 wiki 根目录、映射迁移后的 artifact 路径；测试按返回的规范化路径断言，并补充显式 symlink 的迁移/中断恢复和 wiki 根目录保护测试。文档见 [batch-reocr.md](../batch-reocr.md)。
- 正在进行：修复和验证已完成，准备提交并推送；本快照不预先宣称本轮推送成功。其他运行任务未核验。
- 当前结论：原四项失败中三项属于路径字符串断言未规范化，一项为缓存移动后回执别名路径未更新。已保留临时目录默认行为修复，并覆盖 quality_report、progress 路径及中断后恢复。Zotero 的其他缺口仍见两份状态文档。
- 证据与限制：上述结论来自本次文件读取、目标路径存在性检查及 `git status --short`、`git branch --show-current`、`git rev-parse HEAD` 的输出；核验时间见文件顶部。命令输出保留在本会话，未另建日志。
- 分析与验证：Darwin 27.0.0、Python 3.11.14，已确认系统默认临时目录包含别名。本轮使用 `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider tests/test_batch_reocr.py tests/test_edge_evidence.py tests/test_grounding_lint.py tests/test_mineru_ocr_compat.py tests/test_remove_edge.py tests/test_sync_conflicts.py tests/test_zotero_client.py -q`，未设置 TMPDIR：67 passed、9 subtests passed。新增回归测试先在修复前失败，再在修复后通过；`git diff --check` 通过。未执行真实 OCR、wiki 内容操作或 Zotero 写入，完整依赖影响仍未验证。
- 写作进展：主稿、图表源文件、论证进展、引用依据和待核验主张均未核验；当前没有可写入本文件的已核实研究数值或结论。

## 3. 重要决定

- 当前采用的方案与理由：状态维护规则保留在根目录 `AGENTS.md`，实际状态统一维护于 `docs/templates/PROJECT_STATE.md`，按用户指定的位置继续使用现有文件。状态摘要不替代原始材料、研究结果或实际生效的指导，也不自动授权待办动作。
- 决定依据：最新用户请求明确要求修复四项 macOS 默认临时路径失败，验证后提交并推送。采用路径规范化和相对路径映射，保留库/原始输入边界及迁移哈希校验；不以覆盖 TMPDIR 绕过问题。
- 存储限制：知识、原始材料和稿件分别使用外部 `wiki_root`、`raw_root`、`paper_root`；本次未解析这些别名，实际位置和可用性未核验。来源：[AGENTS.md](../../AGENTS.md) Storage and source ownership，以及 [README.md](../../README.md) External content paths。
- 已排除 / 暂停的方案：不强推，不改写真实 OCR 结果或外部 wiki，不执行其他文档待办；不放宽不同 wiki 根目录检查。

## 4. 下一步与阻塞

以下为候选后续行动，不是执行授权。

1. 提交本轮已验证的修复并普通推送，实时查询远端 main 与本地 HEAD、工作区状态；失败须保留实际错误。
2. 后续具体开发范围待用户选择；Zotero 未完成事项仍以两份状态文档为准，本清单不授权自动实施或真实库操作。

## 5. 恢复工作所需信息

- 项目位置与必读文件：Git 根目录与本次工作目录均为 `llm-wiki` 仓库根目录；先读 [AGENTS.md](../../AGENTS.md)，再按任务查阅 [README.md](../../README.md) 和对应 `skills/<name>/SKILL.md`。跨电脑绝对路径映射未知；当前方案或主稿路径未核验。
- 版本与交接状态：本轮基线 main 为 `3b248adf307c37cc16e1487d3f503ca476b31469`，开始时工作区干净。本轮改动限 `tools/batch_reocr.py`、`tests/test_batch_reocr.py`、`docs/batch-reocr.md` 和本文件；最终提交以 Git 历史为准。外部数据及其他电脑工作区未同步或核验。
- 环境与执行入口：已验证项目 Python 3.11.14 可运行上述客户端测试；完整依赖与外部服务可用性未核验。工具入口规范仍为从根目录运行 `uv run python -X utf8 tools/<tool>.py ...`。来源：[AGENTS.md](../../AGENTS.md) Python execution。
- 最小验证与结果位置：在根目录只读运行 `git status --short`、`git branch --show-current`、`git rev-parse HEAD`，检查 `AGENTS.md` 的引用与 `docs/templates/PROJECT_STATE.md` 是否一致，比较本快照；预期是明确实际版本和差异，不要求与旧快照一致。科研验证方法、预期结果及输出位置未知。
- 恢复前确认：按任务核对文件和版本完整性、未提交/未跟踪内容、外部路径映射、数据与环境、仍在运行的任务；本状态文件不证明这些内容已同步，也不保证中断前状态已保存。

维护：只在有实质变化且当前范围允许写入时更新，更新前重读目标；详细证据留在原文件，不积累聊天转录，不保存密码、密钥、令牌、受限个人数据或不必要的敏感路径。无法保存时如实报告，并提供简短交接摘要。
