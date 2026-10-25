# PROJECT_STATE.md

最后核验：2026-10-25T10:41:00+08:00（Asia/Singapore）；合并提交前验证快照，推送结果需以 Git 历史及远端查询确认。

文件定位：本项目实际使用的状态与交接文件，路径为 `docs/templates/PROJECT_STATE.md`，由根目录 `AGENTS.md` 引用并规定读取和维护时机。文件结构参考用户提供的 Downloads/PROJECT_STATE.md 模板；此文件虽位于模板目录，但持续记录实际项目状态，不是指令或授权来源。以下路径除 Markdown 链接外均相对于项目根目录。

填写约定：未知写“未知”，未检查写“未核验”，不适用写“不适用”。本文件只记录核验时点的情况，恢复工作前需重新检查。

## 1. 研究目标

- 项目名称：`llm-wiki`。仓库自述为个人 LLM 维护的研究知识库，支持 Codex 与 Claude Code，采用 MinerU 进行 PDF 预处理；这是文档声明，实际集成可用性未核验。来源：[README.md](../../README.md) 开头及 Requirements。
- 核心问题与研究范围：仓库用于维护研究知识与相关工作流；具体科研课题、研究问题、假设及数据范围未知。来源：[README.md](../../README.md) Architecture；本次未检查外部研究内容。
- 当前阶段与本阶段交付物：按最新请求合并本地文档清理提交与远程 re-OCR/图维护提交，并推送同步 main。科研项目实际阶段未核验。
- 完成标准 / 已确认的截止日期：保留双方提交，合并后无冲突，记录测试结果，推送后核对本地与远端 main 一致且工作区干净。截止日期未知。

## 2. 当前进展与证据

- 已完成：本地文档清理、状态规则和锁文件改动已提交为 `e5e4c15`；fetch 确认远端为 `c9458b0`（re-OCR 可靠性、图边维护和同步冲突文件过滤）。双方已自动合并，无文本冲突；`AGENTS.md` 同时保留本地状态规则和远端跨机器路径规则。两份 Zotero 状态文档继续保留。
- 正在进行：生成包含本快照的合并提交，随后常规推送 origin/main；本快照不预先宣称推送成功。其他运行任务未核验。
- 当前结论：Zotero 核心接口、分类预览和追加归类已实现，但预览到 collection key 的转换、写后验证、失败审计及跨平台验收仍有缺口，不能将两份计划整体视为已完成。详见两份状态文档。
- 证据与限制：上述结论来自本次文件读取、目标路径存在性检查及 `git status --short`、`git branch --show-current`、`git rev-parse HEAD` 的输出；核验时间见文件顶部。命令输出保留在本会话，未另建日志。
- 分析与验证：合并后对 `test_batch_reocr.py`、`test_edge_evidence.py`、`test_grounding_lint.py`、`test_mineru_ocr_compat.py`、`test_remove_edge.py`、`test_sync_conflicts.py`、`test_zotero_client.py` 运行 `.venv/bin/python -m pytest -p no:cacheprovider`。默认 macOS 临时目录下 61 passed、4 failed，失败均在 batch_reocr，涉及 `/var` 与 `/private/var` 路径比较/迁移映射；改用 `TMPDIR=/private/tmp PYTHONDONTWRITEBYTECODE=1` 后 65 passed、7 subtests passed。路径别名限制仍存在，未修改业务代码来掩盖失败。`git diff --cached --check` 通过，无未解决冲突。未执行真实 OCR、wiki 内容操作或 Zotero 写入；完整依赖影响仍未验证。
- 写作进展：主稿、图表源文件、论证进展、引用依据和待核验主张均未核验；当前没有可写入本文件的已核实研究数值或结论。

## 3. 重要决定

- 当前采用的方案与理由：状态维护规则保留在根目录 `AGENTS.md`，实际状态统一维护于 `docs/templates/PROJECT_STATE.md`，按用户指定的位置继续使用现有文件。状态摘要不替代原始材料、研究结果或实际生效的指导，也不自动授权待办动作。
- 决定依据：最新用户请求明确要求合并同步远程与本地改动，替代上轮仅本地提交、不推送的范围。采用 merge 保留双方历史，不 rebase、不强推。
- 存储限制：知识、原始材料和稿件分别使用外部 `wiki_root`、`raw_root`、`paper_root`；本次未解析这些别名，实际位置和可用性未核验。来源：[AGENTS.md](../../AGENTS.md) Storage and source ownership，以及 [README.md](../../README.md) External content paths。
- 已排除 / 暂停的方案：不另建根目录状态副本，不强推，不因文档待办执行真实 Zotero/wiki 数据操作或外部实验；macOS 路径别名问题记录为后续缺口。

## 4. 下一步与阻塞

以下为候选后续行动，不是执行授权。

1. 完成合并提交和普通推送，再用远端查询核对 main 提交及本地工作区；失败时保留实际错误。
2. 后续可修复 batch_reocr 的 macOS 路径别名兼容性：默认临时目录下四项失败，规范化临时目录下通过；不视为已修复。
3. 若后续继续 Zotero 开发，按两份状态文档中的剩余缺口选择范围；当前仅记录待办，不授权自动实现或真实库操作。

## 5. 恢复工作所需信息

- 项目位置与必读文件：Git 根目录与本次工作目录均为 `llm-wiki` 仓库根目录；先读 [AGENTS.md](../../AGENTS.md)，再按任务查阅 [README.md](../../README.md) 和对应 `skills/<name>/SKILL.md`。跨电脑绝对路径映射未知；当前方案或主稿路径未核验。
- 版本与交接状态：合并前 main 为 `e5e4c15`，本次 fetch 后 origin/main 为 `c9458b0`，共同基线 `fee7ef1`；合并前工作区干净。合并包含远端 22 个文件改动及本状态更新；最终提交以 `git log -1` 为准。锁文件沿用本地提交；外部数据和其他电脑工作区未同步或核验。
- 环境与执行入口：已验证项目 Python 3.11.14 可运行上述客户端测试；完整依赖与外部服务可用性未核验。工具入口规范仍为从根目录运行 `uv run python -X utf8 tools/<tool>.py ...`。来源：[AGENTS.md](../../AGENTS.md) Python execution。
- 最小验证与结果位置：在根目录只读运行 `git status --short`、`git branch --show-current`、`git rev-parse HEAD`，检查 `AGENTS.md` 的引用与 `docs/templates/PROJECT_STATE.md` 是否一致，比较本快照；预期是明确实际版本和差异，不要求与旧快照一致。科研验证方法、预期结果及输出位置未知。
- 恢复前确认：按任务核对文件和版本完整性、未提交/未跟踪内容、外部路径映射、数据与环境、仍在运行的任务；本状态文件不证明这些内容已同步，也不保证中断前状态已保存。

维护：只在有实质变化且当前范围允许写入时更新，更新前重读目标；详细证据留在原文件，不积累聊天转录，不保存密码、密钥、令牌、受限个人数据或不必要的敏感路径。无法保存时如实报告，并提供简短交接摘要。
