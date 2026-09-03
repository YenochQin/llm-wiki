# Zotero 内部 API 分类管理插件实施计划

## 1. 文档目的

本文档规划一个用于管理 Zotero collection 的本地插件及其仓库端 Python 客户端。目标是让 wiki 中的文献分类可以安全地同步到 Zotero，同时避免直接修改 `zotero.sqlite` 导致同步错误、缓存不一致或数据库损坏。

本文档目前是设计和实施计划，不代表插件已经生成、安装或运行，也不执行任何 Zotero 写入。

## 2. 当前背景

### 2.1 已有 Zotero 环境

- Zotero 运行在 Linux，版本为 `10.0.SOURCE.22f08d1ce`。
- Zotero 数据目录由 profile 配置指向 `/home/yenoch/Projects/Zotero`。
- 本地 API 地址为 `http://127.0.0.1:23119`。
- 本地 API 和 Connector 可用于查询，但本地 API 对已有数据的写入能力不能作为本项目的写入方案。
- 仓库 Python 命令必须通过 `uv run python -X utf8` 执行。

### 2.2 已发生的数据库操作

此前曾直接向 Zotero 数据库的 `collections` 表插入以下 collection：

- `TSTCOL01`
- `DIEOX30F`
- `PBY5ON8P`
- `0IHICR0L`
- `6AQC6W6L`
- `I6HRY16Y`
- `I4B2NBPP`

这些记录在本地 API 中曾经可见，但 Zotero 同步时报告 collection key 无效或上传失败。因此后续必须通过 Zotero 进程内部 API 重新验证、清理或迁移这些记录，不能继续直接编辑 SQLite。

### 2.3 已创建的分类

目前计划中的分类树为：

```text
Wiki Documents
├── Relativistic Atomic Structure
├── Open-Shell Spectroscopy
├── Hyperfine and Nuclear Structure
├── Isotope Shifts and King Plots
└── Astrophysical and Plasma Applications
```

这些 collection 之前也曾通过直接数据库写入方式创建，后续应由 Zotero 内部 API 重新建立或校正。

## 3. 目标

### 3.1 第一阶段目标

实现一个仅面向本机的 Zotero 插件，提供：

1. 健康检查。
2. 查询 collection 树。
3. 幂等创建顶层 collection。
4. 幂等创建指定父 collection 下的子 collection。
5. 返回 collection 名称、父级、内部 ID、合法 key 和创建状态。
6. 记录最小审计日志。

所有写入都必须在 Zotero 进程内部调用 `Zotero.Collection` 和 `saveTx()`，由 Zotero 负责数据库事务、对象缓存、版本字段和同步队列。

### 3.2 第二阶段目标

在用户确认分类映射后：

- 根据 wiki 论文页的结构化分析生成“论文 → 拟加入 collection”的预览。
- 通过插件向已有 Zotero 条目追加 collection 关联。
- 保留每个条目已有的全部 collection 归属。
- 不创建重复条目，不移动附件，不删除文献。

## 4. 非目标和禁止事项

第一版插件不实现以下能力：

- 不直接打开或修改 `zotero.sqlite`。
- 不在 Zotero 进程外伪造 collection key。
- 不自动删除 collection。
- 不覆盖条目已有的 collection 列表。
- 不通过导入 BibTeX/RIS 的方式给已有条目“追加分类”，以免产生重复条目。
- 不把每个理论标签、元素名或实验仪器都创建为独立 collection。
- 不在没有用户确认的情况下批量修改数百篇文献。

删除历史无效 collection 可以作为单独的受控迁移步骤，但不应作为第一版远程接口的默认能力。

## 5. 总体架构

```text
wiki/*.md
    │
    ├── 分类分析器（只读）
    │       └── 生成预览 JSON/Markdown
    │
    └── tools/zotero_client.py
            │  HTTP + token（仅 127.0.0.1）
            ▼
      Zotero Wiki Organizer 插件
            │  Zotero 内部 JavaScript API
            ├── Zotero.Collections
            ├── Zotero.Collection
            └── saveTx()
                    │
                    ▼
              Zotero 数据库与同步队列
```

插件和 Python 客户端之间使用本机 HTTP；Python 不接触数据库文件。插件内部才可以安全访问 Zotero 的对象模型。

## 6. 插件设计

### 6.1 兼容性验证

在正式实现前先完成一个最小兼容性验证：

1. 确认 Zotero 10 当前支持的插件格式（bootstrap、WebExtension 或 Zotero 官方脚手架格式）。
2. 确认插件如何注册启动/关闭生命周期。
3. 确认插件如何访问 `Zotero.Collection`、`Zotero.Collections` 和 `Zotero.Server.Endpoints`。
4. 确认自定义 HTTP endpoint 是否能安全地加入 Zotero 已有本地服务器，或是否需要插件单独监听端口。
5. 确认插件安装、升级和卸载时不会覆盖用户数据。

如果 Zotero 10 的扩展 API 与旧版 bootstrap 行为不兼容，应优先采用当前版本的官方插件模板，而不是套用旧版示例。

### 6.2 插件功能模块

建议的模块划分：

```text
zotero-wiki-organizer/
├── manifest.json 或 install.rdf       # 取决于兼容性验证结果
├── bootstrap.js / background.js       # 生命周期入口
├── src/
│   ├── collections.js                  # collection 查找和创建
│   ├── endpoint.js                     # 本地 HTTP endpoint
│   ├── auth.js                         # token 校验
│   ├── audit.js                        # 审计日志
│   └── migration.js                    # 受控历史数据迁移
├── defaults/
│   └── preferences.js                 # 端口、启用状态等默认设置
└── README.md
```

实际目录结构以 Zotero 10 兼容性验证结果为准。

### 6.3 内部 collection 操作

创建 collection 的内部逻辑应遵循以下语义：

1. 根据 `libraryID`、名称和 `parentID` 查找同层级已有 collection。
2. 找到时返回已有对象，不创建重复项。
3. 找不到时创建 `new Zotero.Collection()`。
4. 设置 `libraryID`、`name` 和 `parentID`。
5. 调用 `await collection.saveTx()`。
6. 重新从 Zotero 对象缓存读取并返回最终 key。

伪代码：

```javascript
async function getOrCreateCollection(name, parentID = null) {
  const libraryID = Zotero.Libraries.userLibraryID;
  const existing = Zotero.Collections
    .getByLibrary(libraryID)
    .find(c => c.name === name && c.parentID === parentID);

  if (existing) {
    return { collection: existing, created: false };
  }

  const collection = new Zotero.Collection();
  collection.libraryID = libraryID;
  collection.name = name;
  collection.parentID = parentID;
  await collection.saveTx();

  return { collection, created: true };
}
```

正式实现时必须以当前 Zotero 版本的接口定义为准，并补充异常处理、权限判断和事务失败处理。

## 7. 外部本地接口

### 7.1 网络边界

- 只监听 `127.0.0.1`。
- 不监听 `0.0.0.0`，不允许局域网访问。
- 使用随机 token 认证。
- token 不写入 git，不出现在普通日志中。
- 请求和响应只传递 collection 元数据，不传递文献全文或附件路径。

### 7.2 建议 endpoint

```text
GET  /wiki-organizer/v1/health
GET  /wiki-organizer/v1/collections
POST /wiki-organizer/v1/collections
```

第一版不提供通用 collection 删除或条目批量移动接口。针对早期直接写入
SQLite 造成的 7 个已核实为空的历史 collection，插件提供了严格 allowlist
和确认字符串保护的一次性清理端点：

```text
POST /wiki-organizer/v1/migration/erase
```

该端点只允许删除计划 §2.2 中的历史 key，且会拒绝包含条目或非历史子
collection 的对象；删除仍通过 Zotero 内部 `eraseTx()` 完成。

### 7.3 创建请求

```json
{
  "name": "Relativistic Atomic Structure",
  "parent": "Wiki Documents",
  "mode": "create-if-missing"
}
```

顶层 collection 的 `parent` 可省略或设为 `null`。

### 7.4 创建响应

```json
{
  "name": "Relativistic Atomic Structure",
  "parent": "Wiki Documents",
  "key": "由 Zotero 生成",
  "collectionID": 123,
  "created": true
}
```

重复请求应返回 `created: false` 和同一个已有 key。

### 7.5 错误模型

客户端需要区分：

- `401`：token 缺失或错误。
- `400`：名称为空、父级不存在或请求格式错误。
- `409`：同名但父级关系冲突。
- `503`：Zotero 尚未完成启动或对象服务不可用。
- `500`：Zotero 内部事务失败；不得自动重试写入，需先查询确认状态。

## 8. 仓库端 Python 客户端

建议新增：

```text
tools/zotero_client.py
```

运行方式必须是：

```bash
uv run python -X utf8 tools/zotero_client.py health
uv run python -X utf8 tools/zotero_client.py list
uv run python -X utf8 tools/zotero_client.py create \
  --name "Relativistic Atomic Structure" \
  --parent "Wiki Documents"
```

客户端职责：

- 从环境变量或用户配置读取 endpoint 和 token。
- 默认拒绝非 loopback 地址。
- 设置合理连接和读取超时。
- 将服务端错误转换为可读的中文提示。
- 写操作后自动执行一次查询验证。
- 不读取、不复制、不修改 Zotero 数据库文件。

## 9. 历史无效 collection 的迁移计划

这是一个独立的高风险步骤，不应和插件首次安装混在一起自动执行。

### 9.1 准备阶段

1. 暂停 Zotero 同步。
2. 确认 Zotero 正在运行且插件可以调用内部 API。
3. 创建带时间戳的数据库备份。
4. 通过内部 API 查询以下 key 对应的名称、父级和条目数量：

   ```text
   TSTCOL01
   DIEOX30F
   PBY5ON8P
   0IHICR0L
   6AQC6W6L
   I6HRY16Y
   I4B2NBPP
   ```

5. 将查询结果保存为迁移审计记录。

### 9.2 清理或重建决策

- 如果 collection 为空且只对应本次测试，可通过 Zotero 内部 `eraseTx()` 删除。
- 如果 collection 已经被用户使用，不能直接删除；应先通过内部 API 创建合法替代 collection，再由用户决定是否保留旧项。
- 如果 key 错误来自同步元数据而非 collection 对象本身，应先停止删除动作，检查 Zotero 同步状态和服务器响应。

### 9.3 重建阶段

使用插件内部 API 按目标树重新执行 `create-if-missing`。只在每个 collection 的 key 已由 Zotero 生成并且 API 查询确认后，恢复同步。

### 9.4 验证阶段

- 同步日志不再出现 `invalid collection key`。
- 不出现 `Made no progress during upload`。
- 旧条目数量、附件数量和原有 collection 归属保持不变。
- 新分类在 Zotero UI、本地 API 和同步状态中一致可见。

## 10. Wiki 分类分析与预览

插件稳定后再做 wiki 批量分类。分析器只读以下信息：

- `paper_type`
- `research_modes`
- `theory_tags`
- `computation_tags`
- `experiment_tags`
- `research_object_tags`
- `domain`
- 论文页中的 topic/concept wikilinks

建议先输出：

```json
{
  "paper": "论文 citation key 或 wiki slug",
  "zotero_match": {
    "status": "matched|ambiguous|missing",
    "item_key": "..."
  },
  "proposed_collections": [
    "Wiki Documents/Relativistic Atomic Structure"
  ],
  "reasons": [
    "domain=atomic-structure",
    "research_modes includes computation",
    "related topic=medium-high-z-atomic-structure"
  ]
}
```

只有用户确认预览后，才进入批量追加 collection 的阶段。归类算法必须采用集合并集：

```text
最终归属 = 原有归属 ∪ wiki 推断归属
```

## 11. 测试计划

### 11.1 插件单元测试

- 空名称被拒绝。
- 顶层 collection 创建成功。
- 子 collection 创建成功。
- 同名同父级请求幂等。
- 同名不同父级不会错误复用。
- 无 personal library 时返回明确错误。
- `saveTx()` 失败时不会返回成功响应。

### 11.2 接口测试

- 无 token 请求返回 `401`。
- 非 loopback 配置被拒绝。
- 健康检查在 Zotero 启动前后返回正确状态。
- 创建后立即查询能看到相同 key。
- 重复请求不会增加 collection 数量。
- Zotero 重启后 collection 仍存在。

### 11.3 同步回归测试

- 新 collection 能进入同步队列。
- 不再出现 `invalid collection key`。
- 不再出现 `Made no progress during upload`。
- 同步失败时客户端不会盲目重复写入。

### 11.4 数据保护测试

- 创建 collection 不增加或删除 item。
- 创建 collection 不修改 item 的已有 collection 列表。
- 批量追加归类只增加目标 collection 关联。
- 中途失败后可根据审计记录重试，且重复运行幂等。

## 12. 回滚方案

### 12.1 插件回滚

- 禁用或卸载插件，不触碰 Zotero 条目。
- 停止仓库端 Python 客户端。
- 保留插件日志和版本信息。

### 12.2 数据回滚

任何历史数据迁移前都必须有备份。若内部 API 迁移造成异常：

1. 退出 Zotero。
2. 保留故障日志和当前数据库副本。
3. 使用迁移前备份恢复数据库。
4. 重启 Zotero 并检查同步状态。

恢复操作属于破坏性操作，必须在确认目标文件和备份完整后执行。

## 13. 实施阶段和交付物

### 阶段 A：兼容性与接口验证

交付物：

- Zotero 10 插件格式调查记录。
- 最小内部 API 原型。
- endpoint 注册方式决定。
- token 存储位置和配置方案。

### 阶段 B：插件最小实现

交付物：

- 可安装插件。
- `health`、`list`、`create-if-missing`。
- 本地认证。
- 审计日志。

### 阶段 C：Python 客户端

交付物：

- `tools/zotero_client.py`。
- `health`、`list`、`create` 子命令。
- uv 环境下的测试和使用说明。

### 阶段 D：历史 collection 修复

交付物：

- 历史 collection 审计报告。
- 用户确认后的内部 API 清理/重建结果。
- 同步恢复验证报告。

### 阶段 E：wiki 分类预览

交付物：

- DOI、citation key、题名/年份匹配报告。
- 文献到 collection 的分类预览。
- 歧义和未匹配列表。

### 阶段 F：增量归类

交付物：

- 用户确认的批量操作清单。
- 分批归类日志。
- 变更前后 collection 归属统计。
- 可重放、可审计的结果文件。

## 14. 验收标准

只有同时满足以下条件，才认为插件方案完成：

1. 所有 collection 写入都通过 Zotero 内部对象 API 完成。
2. Python 客户端不读取或修改 SQLite。
3. collection key 由 Zotero 生成并能通过 API、UI 和同步流程识别。
4. 重复请求不会创建重复 collection。
5. 新建或归类操作不会删除、移动或覆盖已有文献归属。
6. 历史无效 collection 已经过审计，且清理/保留决定可追溯。
7. 同步日志不再出现本次操作相关的无效 key 错误。
8. 所有批量归类先有预览，再有用户确认。
9. 操作前有备份，操作后有验证和审计记录。

## 15. 实施状态

### 15.1 阶段 A：兼容性与接口验证（已完成）

针对 Zotero main 分支（10.0.SOURCE）源码核实的结论：

1. 插件格式：WebExtensions 风格 `manifest.json`（`manifest_version: 2`）+ `bootstrap.js` 生命周期（`install`/`startup`/`shutdown`/`uninstall`）。**注意**：Zotero 10 main 对 `applications.zotero` 的要求比 Zotero 7 文档严格——`id`、`update_url`、`strict_max_version` 三项均为必填，缺失会以“与该版本 Zotero 不兼容”为由拒绝安装（已从本机 Zotero 10 构建的 `Extension.sys.mjs` 补丁源码确认，并与本机已安装可用的 Better BibTeX 等插件 manifest 交叉验证）。本插件使用 `strict_min_version: "9.0"`、`strict_max_version: "10.999"`；`update_url` 指向尚未发布的 GitHub release feed，更新检查会静默失败，属预期行为。
2. 自定义 HTTP endpoint 可以安全地挂在 Zotero 内置本地服务器（127.0.0.1:23119）上，无需插件单独监听端口；Better BibTeX 等插件同样采用该方式。
3. endpoint 注册契约（以当前源码为准，旧版官方文档已过时）：`Zotero.Server.Endpoints["/path"]` 必须赋值为构造函数，`prototype` 上定义 `supportedMethods` 和 `init`；`init` 声明恰好一个参数时收到 `{method, pathname, searchParams, headers, data}`，返回 `[status, contentType, body]`，`application/json` 的 POST body 会被自动解析。
4. 本地服务器自带防护：`Host` 必须为 loopback；浏览器 UA 或携带 `Origin` 的请求默认被直接丢弃，除非带 `Zotero-Allowed-Request` 头（Python 客户端会带上，且不使用浏览器 UA）。
5. 内部 collection API：`Zotero.Collections.getByLibrary(libraryID)`、`new Zotero.Collection()` + `name`/`libraryID`/`parentKey` + `await saveTx()`，与第 6.3 节伪代码一致。
6. token 存储：Zotero 偏好 `extensions.zotero.wikiOrganizer.token`（`Zotero.Prefs.get/set(name, true)` 绝对路径形式），并在数据目录镜像一份 `wiki-organizer-token.txt` 供客户端读取。

### 15.2 阶段 B/C：插件已安装并验证（v0.1.1）

- 插件源码位于 `zotero_plugin/`（阶段 B），Python 客户端位于 `tools/zotero_client.py`（阶段 C），用法见 `zotero_plugin/README.md`。
- 2026-09-02 已在本机 Zotero 10.0.SOURCE 上安装成功：`health` 返回 `ready: true`（26 个 collection），`list` 正常返回全树；客户端无需配置即可自动从 profile 的 prefs.js 读取 token。
- v0.1.0 曾有两个问题已修复：manifest 缺少 Zotero 10 必填的 `update_url`/`strict_max_version` 导致无法安装；启动时写 token 文件/审计文件失败——根因是 `Zotero.DataDirectory.dir` 返回纯字符串路径，访问 `.dir.path` 得到 `undefined`（已从本机构建 `dataDirectory.js` 源码确认）。v0.1.2 修复该问题，并在 health 端点暴露 `startupError` 以便远程诊断。
- 后续不再通过 `tools/zotero_create_collection.py`（直写 SQLite 的旧路径）执行 collection 写入；该脚本现已改为安全停用提示，所有写入必须经过 Zotero 内部 API 插件。
- **阶段 D 审计已完成（2026-09-02，只读）**：7 个历史 key（TSTCOL01、DIEOX30F、PBY5ON8P、0IHICR0L、6AQC6W6L、I6HRY16Y、I4B2NBPP）在用户库与所有群组库中均不存在——历史损坏记录已不在本地数据库，无需删除清理；阶段 D 剩余工作仅为按目标树执行 create-if-missing 重建。
- v0.1.3：审计日志追加写在 0.1.2 的 IOUtils `{mode:"append"}` 下实测失败，改为"读旧内容+整体重写"组合（只用已验证可行的原语）。**0.1.3 已安装并全量验证通过（2026-09-02）**：token 文件与审计日志均正常落盘，追加写可累积记录，health 的 `startupError` 为空。
- 阶段 D（历史 collection 清理/重建）与阶段 E/F（批量归类）仍等待用户确认后才执行；`GET /wiki-organizer/v1/migration/inspect` 端点只读，仅供阶段 D 准备审计数据。

### 15.3：按代码审查意见修复（已完成，待重新安装验证）

- 仅接受 `Authorization: Bearer <token>`，移除 query-string token。
- 客户端始终拒绝非 loopback 地址，移除 `--allow-non-loopback` 绕过选项。
- token 镜像文件写入后使用 `IOUtils.setPermissions(..., 0o600)`；Zotero preference 仍是权威存储。
- `create --json` 现在只向 stdout 输出 JSON；写后验证失败写入 stderr。
- collection 创建和审计日志追加均串行化，避免并发竞态和日志丢失。
- 默认偏好位于插件根目录 `prefs.js`（Zotero 7+/10 的 `setDefaultPrefs()` 加载路径），并实际读取 `enabled`、`auditLog`。
- health 在启动任务失败或尚未完成时返回 `503`，客户端对非对象响应给出受控错误。
- 旧的直接 SQLite 创建脚本已停用，改为提示使用 `tools/zotero_client.py`。
- 插件版本提升至 `0.1.5`，并修正 Zotero 10 manifest 的 `author` 类型；XPI 已重新打包，尚未自动替换 Zotero 当前已安装版本。
- v0.1.10：修复 legacy migration 的后代/回收站检查与数据加载顺序；`items/assign` 改为异步 item 解析并在写入前完成存在性校验；修正默认偏好文件路径、启动失败时写端点门控、token 文件权限窗口和公开客户端函数的 loopback 校验。已完成静态检查与 Python 单元测试，仍待实际 Zotero 环境回归。
- v0.1.11：审计日志优先使用 `appendOrCreate`；token 镜像使用临时文件和原子移动（旧 Zotero 构建保留受保护文件 fallback）；token 改用 `crypto.getRandomValues`；health 不再返回启动堆栈；客户端增加 macOS/Windows profile 自动发现；XPI 打包改为显式 allowlist。

仍待在实际 Zotero 安装环境中完成同步回归、重启持久化和条目归属保护测试。
