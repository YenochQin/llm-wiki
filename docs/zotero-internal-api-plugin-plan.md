# Zotero 内部 API 分类管理插件：状态与验收

本文保留原文件名作为引用入口；已完成的设计、伪代码和逐版本实施步骤已移除。使用方式见 [插件 README](../zotero_plugin/README.md)，平台事项见 [跨平台状态与验收](zotero-cross-platform-support-plan.md)。

## 当前实现状态

核对日期：2026-10-25（Asia/Singapore，UTC+08:00）。代码基线：`fee7ef1057a67488d3f3986db39a68a717b80585`，插件版本 `0.1.11`；核对时相关实现没有未提交差异。本文的“已实现”指源码存在，不代表当前安装环境已验收。

| 能力 | 当前实现及依据 | 状态 |
|---|---|---|
| 插件与接口（原 A/B） | [bootstrap.js](../zotero_plugin/bootstrap.js)、[endpoint.js](../zotero_plugin/src/endpoint.js)：生命周期、health、collection 查询/创建、迁移和追加归类端点 | 已实现 |
| 创建与客户端（原 C） | [collections.js](../zotero_plugin/src/collections.js) 按名称和父级串行幂等创建；[zotero_client.py](../tools/zotero_client.py) 提供认证配置、超时、错误映射、创建后查询与 JSON 输出 | 已实现 |
| 历史迁移（原 D） | [migration.js](../zotero_plugin/src/migration.js)：跨库检查历史 key；清理限定个人库，检查名称、条目（含回收站）和后代范围 | 工具已实现，实际迁移结果仍待确认 |
| 分类预览（原 E） | [classify_wiki_papers.py](../tools/classify_wiki_papers.py)：DOI、citation key、题名/年份匹配，输出分类分数、匹配项及未解决项 | 已有实现，尚未接通写入输入 |
| 增量归类（原 F） | [items.js](../zotero_plugin/src/items.js) 先解析目标条目和 collection，再追加关联并逐项 `saveTx()`；客户端已有 `assign --file` | 核心接口已实现，批处理闭环未完成 |
| 认证与审计 | [auth.js](../zotero_plugin/src/auth.js) 仅接受 Bearer token；客户端限制 loopback；[audit.js](../zotero_plugin/src/audit.js) 串行追加事件 | 已实现基础机制；失败审计及文件权限仍有缺口 |

本次代码核对已执行现有客户端测试：Python 3.11.14，`PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -X utf8 -m unittest discover -s tests -p test_zotero_client.py`，17 项通过；`node --check` 检查 bootstrap 和全部 `src/*.js` 通过。测试源码见 [test_zotero_client.py](../tests/test_zotero_client.py)。未运行真实 Zotero 写入、重启、同步或跨平台验收；未重新打包 XPI。

历史记录：旧版计划记载 2026-09-02 在 Linux + Zotero `10.0.SOURCE` 上安装和查询成功，并记载七个历史 key 当时在个人库及群组库均不存在。该记录不证明当前库状态；重建和同步恢复没有完整完成证据。原记录可用 `git show fee7ef1:docs/zotero-internal-api-plugin-plan.md` 查阅（原 §15.2）；[v0.1.9 审查报告](zotero-plugin-code-review-findings.md) 也仅代表历史检查。

### 保留的操作约束

- collection 创建、关联追加及受控删除必须经过 Zotero 内部对象 API；Python 客户端不直接读写 SQLite。普通归类不删除文献、不移动附件、不覆盖已有归属。
- 批量归类先输出预览并取得用户确认，再执行写入。文档中的待办、历史确认和验收清单均不授权新的数据操作。
- 历史清理须先重新检查、保存审计结果及可恢复备份，单独确认后执行。allowlist 为 `TSTCOL01`、`DIEOX30F`、`PBY5ON8P`、`0IHICR0L`、`6AQC6W6L`、`I6HRY16Y`、`I4B2NBPP`；名称映射以 `migration.js` 的 `EXPECTED_NAMES` 为准。仅允许符合空集合及后代检查的对象，确认字符串为 `ERASE_LEGACY_COLLECTIONS`。
- 若对象已被使用，或问题属于同步元数据，不自动删除；重建目标树需重新确认。迁移前暂停同步，查询确认后再恢复；数据库恢复仅在 Zotero 退出且备份已核实后另行授权执行。
- 写入失败不得盲目重试，先查询实际状态。错误映射见 [endpoint.js](../zotero_plugin/src/endpoint.js)：`401` 认证、`400` 参数、`409` 歧义父级、`503` 未就绪、`500` 内部错误。

## 剩余缺口

1. **预览到写入的转换。** 分类器输出 `categories` 名称，`assign` 原样提交数组，而插件要求 `collectionKeys`。缺少名称/完整路径到当前 key 的解析及歧义处理，预览文件不能直接用于写入。
2. **预览依据和路径配置。** 分类器输出分数而非逐项命中理由；未专门消费 `paper_type` 和 topic/concept 链接。默认 wiki 根目录仍为旧 Linux 绝对路径，需接入当前外部路径配置；分类规则、匹配歧义和输入异常缺少专门自动化测试。
3. **写后验证。** `create` 已独立查询验证；`assign_items()` 仅接收 POST 响应，没有重新查询条目归属。迁移删除也需确认最终库状态。
4. **批处理与失败审计。** 尚无自动分批、断点恢复、完整变更前后统计及持久化结果文件流程。`items.js` 逐项提交，而 `endpoint.js` 在整批返回后才记审计；中途失败可能留下部分变更而没有对应批次记录。`audit.js` 写失败只记录 debug，不保证可重放审计。
5. **实际验收证据。** 历史对象当前状态、目标树重建、当前版本同步恢复和条目归属保护均未在本次核对中验证。权限与启动兼容性缺口统一见 [跨平台文档](zotero-cross-platform-support-plan.md)。

最小下一步：先补齐预览名称到 collection key 的转换及其离线测试，再衔接写后验证和批次结果记录。

## 验收清单

以下为当前版本仍需留存证据的验收项；代码已存在不自动勾选。

- [ ] 预览输出可转换为有效的 `assign` 输入；匹配依据可追溯，歧义/未匹配项不会自动写入，确认清单与执行清单一致。
- [ ] 分类器使用已验证的外部 wiki 根目录；空输入、无匹配、重复 DOI/citation key、同名 collection 均有测试。
- [ ] collection 创建覆盖顶层/子级、同名同父级幂等、同名不同父级、空名称、歧义父级、无个人库及 `saveTx()` 失败。
- [ ] 追加归类前后独立查询，确认已有归属不减少，重复执行不重复添加，item/附件数量不变。
- [ ] 批次中途失败可识别已提交条目，审计失败可见；保存确认清单、逐批结果、前后统计，并能安全恢复。
- [ ] 历史 key 重新审计后记录无需操作、保留或获授权清理/重建的决定；迁移覆盖后代和回收站条目保护，并完成写后查询。
- [ ] 当前安装版本通过认证、启动未就绪和接口错误测试；失败后不盲目重试写入。
- [ ] 重启后 collection 持久存在，UI/API 状态一致；同步无 `invalid collection key` 或 `Made no progress during upload`，既有数据与归属保持完整。

验收记录至少包含日期和时区、代码/插件/Zotero 版本、测试库或快照标识、操作清单、预期/实际结果、日志及输出位置。未运行、执行成功、结果已验证须分别标记；不记录 token。跨平台安装与权限按配套清单验收。
