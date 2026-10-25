# PROJECT_STATE.md

最后核验：2026-10-25T21:30:25+08:00（Asia/Singapore）。代码合并提交 `9d32fe00069d4b005869cdd404c1e83244c218aa` 已普通推送；实时 `git ls-remote origin refs/heads/main` 与当时本地 HEAD 一致，工作区干净。本文件是其后的交接快照，当前最新提交需以 Git 查询为准。

文件定位：本项目实际使用的状态与交接文件，路径为 `docs/templates/PROJECT_STATE.md`，由根目录 `AGENTS.md` 引用；虽位于模板目录，但持续记录实际项目状态。它不是指令或授权来源，不替代外部研究内容。以下路径除 Markdown 链接外均相对于项目根目录。

## 1. 当前工作与完成标准

- 项目：`llm-wiki`，个人研究知识库工具与技能仓库。当前交付是按用户要求处理本地与远程分叉，保留双方修改并同步。
- 合并前：本地 `main` 为 `4b44b94`，独有 2 个提交；远程为 `95be57f`，独有 3 个提交；共同祖先为 `c9458b0`。工作区无未提交修改。
- 完成标准：合并双方历史，验证后普通推送，直接查询远程 main 与本地 HEAD，并检查工作区。代码合并阶段已满足；携带此快照的后续文档提交仍以实时 Git 状态确认。

## 2. 当前进展与证据

- 已完成：自动合并，无冲突。合并提交为 `9d32fe0`，父提交分别为 `4b44b94` 和 `95be57f`。本地的高精度原子研究规则、独立 experiment/output 根目录功能与远程的文档整理、Zotero 状态说明、re-OCR 路径别名修复全部保留。
- 代码验证：Linux、项目 Python 3.12.14；运行 `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider -q`，结果为 **205 passed, 59 subtests passed**。测试日志在 `.checkpoints/git-sync-20261025/tests.log`（本机忽略缓存，其他机器可能没有）。测试树与 `9d32fe0` 一致。
- Git 验证：`git diff --cached --check`、`git diff --check` 无问题，`git ls-files -u` 为空；普通推送成功，实时远端查询确认 `9d32fe0` 已到达 origin/main。
- 环境边界：合并远程 `uv.lock`，未安装或同步依赖，保留现有 `.venv`。上述测试不等于在新建环境中重建锁定依赖，也不等于完成真实 OCR 或 Zotero 集成写入验证。
- macOS 修复来源：`95be57f`；其历史验证记录为 Darwin 27.0.0 / Python 3.11.14，67 tests 与 9 subtests。此历史结果未在本 Linux 会话中重跑为 macOS 实测；新增符号链接回归已包含在本次完整测试中。实现说明见 [batch-reocr.md](../batch-reocr.md)。
- 科研结果：本次 Git 同步未执行科学计算、LaTeX 编译、真实 OCR 或 Zotero 写入，未生成新的科研数值。

## 3. 保留的设计与约束

- 内容位置：知识与日志使用 `wiki_root`，实验记录使用 `experiment_root`，报告与计划使用 `output_root`，原始输入使用 `raw_root`，作者稿件使用 `paper_root`。实验和输出根目录与 wiki 独立，使用前按 [AGENTS.md](../../AGENTS.md) 验证实际所需别名。
- 图谱身份：`experiments/<slug>`、已有 `outputs/<slug>` 保持逻辑身份，物理位置由 `tools/_content.py` 解析。不能通过拼接 wiki 子目录恢复旧布局。
- 同步方式：正常 merge 与普通 push，保留双方提交历史。恢复分支 `codex/backup-before-sync-20261025-4b44b94` 指向合并前的本地提交，仅在本机创建。
- 本会话先前的外部内容迁移与清理记录位于 `@output-root/independent-roots-migration-2026-10-25.md`、`@output-root/orphan-page-retention-2026-10-25.md`。这些外部内容及本机 `config/paths.json` 不在仓库提交中，本次 Git 同步不证明其他电脑已迁移内容或配置。
- Zotero 的未完成事项见 [跨平台状态](../zotero-cross-platform-support-plan.md) 与 [内部 API 插件状态](../zotero-internal-api-plugin-plan.md)。文档待办不构成操作授权。

## 4. 下一步与阻塞

- 本次代码集成与推送没有剩余阻塞。后续具体开发或研究工作等待用户指定。
- 下一次恢复时先核对 Git 状态、最新提交和实际远端；跨机器使用时另行核验本机根目录配置、外部数据及 Python 环境。先前快照不保证当前同步状态。
- 新研究计算、真实库操作、依赖安装及其他外部写入均需对应的用户授权，不能从本文件的待办或历史记录推导。

## 5. 最小恢复入口

- 先读 [AGENTS.md](../../AGENTS.md)，再按任务读 [README.md](../../README.md)、[路径配置](../../config/README.md) 和相关技能。
- 版本检查：`git status --short --branch`、`git log -3 --oneline`、`git rev-parse HEAD`；需要远端最新状态时执行用户授权范围内的远端查询。
- 代码基线：集成提交 `9d32fe0` 已验证。此后的交接文档提交不改变已测试代码；若后来代码变化，需重新选择相关验证。
- 尚未核验：其他电脑的工作区、外部内容同步状态、外部服务状态及其他运行任务。不要把本机测试或 Git 同步推断为这些项目已完成。

维护：仅在当前授权范围内记录实际状态；更新前重读目标，保留并发编辑。不记录密钥、密码或不必要的敏感路径，不累积聊天转录。
