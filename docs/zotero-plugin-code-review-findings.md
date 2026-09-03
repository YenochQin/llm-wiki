# Zotero Wiki Organizer 插件代码审查发现

## 1. 审查范围与方法

审查对象：`zotero_plugin/`（插件源码，v0.1.9）、`tools/zotero_client.py`（Python 客户端）、
`tests/test_zotero_client.py`，对照 `docs/zotero-internal-api-plugin-plan.md` 和
`docs/zotero-cross-platform-support-plan.md` 的设计约束逐项核对。

验证方式：

- 从本机已安装的 Zotero（`/usr/lib/zotero/app/omni.ja`，版本 `10.0.SOURCE.22f08d1ce`）解出
  `collection.js`、`dataObjects.js`、`item.js`、`zotero.js`、`plugins.js`、`server/server.js`
  等源码，核对插件调用的内部 API 签名和行为，不依赖记忆或旧版官方文档。
- 对本机正在运行的插件发了 3 个只读请求（`health`、错误 token、不存在的 `parent`），
  确认认证、错误映射链路可用；未执行任何创建、删除或分类分配操作。
- 运行 `node --check` 检查全部插件源码文件、`uv run python -X utf8 -m unittest
  tests/test_zotero_client.py`（14 个测试通过）、`uv run ruff check`（无告警）。

总体结论：架构与两份计划文档一致——所有写入都经过 `Zotero.Collection`/`Item.saveTx()`，
端点只挂在 loopback server 上，认证只接受 `Authorization: Bearer`，创建操作已串行化，
`erase` 端点有 allowlist + 名称核对 + 确认字符串三重防护。但对照 Zotero 内部源码，
发现若干处**内部 API 签名用错**，集中在两个较少被日常验证覆盖的写路径：历史 collection
整树清理（`migration.js`）和条目分类追加（`items.js`）。所有已确认问题的失败方向都是
"拒绝执行/报错"而非"误删或误写"，但会阻塞计划中的阶段 D/F 或产生误导性的错误分类。

## 2. 高优先级：内部 API 签名错误

### 2.1 `migration.js:180` — `getChildCollections(true)` 返回 ID 数组，不是对象

`Zotero.Collection.prototype.getChildCollections` 的签名是
`(asIDs, includeTrashed)`。当前调用 `c.getChildCollections(true)` 把 `asIDs=true`
传成第一个参数，返回值是 collectionID 数组而不是 Collection 对象数组，于是：

```javascript
let descendants = c.getChildCollections(true) || [];
let outside = descendants.filter((d) => !requestedSet.has(d.key));
```

`d.key` 对数字 ID 恒为 `undefined`，`requestedSet.has(undefined)` 恒为 `false`，
`outside` 恒非空 —— **任何带子 collection 的历史父节点都会被判定为"含非 legacy 子
collection"而拒绝清理**。计划 §2.2/§2.3 中 `DIEOX30F`（"Wiki Documents"）本身带 5 个
legacy 子节点，这意味着按计划描述的整树清理场景在当前实现下永远无法通过校验。

此外该调用只看**直接子级**，不看全部后代；而 `eraseTx()` 底层 `_eraseData` 用
`getDescendents(false, null, true)` 级联删除全部后代（含孙节点）。如果历史数据出现三层
嵌套，孙节点层的非 legacy collection 检查不到，会被连带静默删除。

**修复方向**：改用 `c.getDescendents(false, 'collection', true)` 取全部后代对象后再比对
`.key`，覆盖任意深度。

### 2.2 `items.js:14` — `getByLibraryAndKey` 对已注册未加载的 item 会抛异常

`Zotero.DataObjects.prototype.get`（`getByLibraryAndKey` 内部调用）的行为：

```javascript
if (!this._objectCache[id]) {
  if (this._objectKeys[id]) {
    throw new Zotero.Exception.UnloadedDataException(...);
  }
  else { continue; }  // 静默跳过，返回 false
}
```

而 `zotero.js` 启动流程明确写着："Load all library data except for items, which are
loaded when libraries are first clicked on or if otherwise necessary"。当前
`WikiOrgCollections.waitUntilReady()` 只等 `uiReadyPromise`/`initializationPromise`，
不等 item 数据加载完成。

结果：Zotero 刚启动、用户尚未点开 My Library 时调用 `POST /items/assign`，会在
`items.js:14` 的 `Zotero.Items.getByLibraryAndKey` 上抛 `UnloadedDataException`，
被 `endpoint.js` 的通用 catch 归类为 **500 内部错误**。客户端对 500 的既定语义是
"不要自动重试写入，先用 list 确认状态"（`docs/zotero-internal-api-plugin-plan.md` §7.5），
这会误导阶段 F 批量归类时的重试逻辑——实际只是数据还没加载，不是事务失败。
`item.getCollections()`、`item.addToCollection()` 内部同样调用 `_requireData('collections')`，
存在同样风险。

**修复方向**：改用 `await Zotero.Items.getByLibraryAndKeyAsync(...)`，或在
`assign` 入口调用 `await Zotero.Items.loadDataTypes(items, ["collections"])` /
`await Zotero.Libraries.get(libraryID).waitForDataLoad('item')`；同时将
`Zotero.Exception.UnloadedDataException` 单独捕获并映射为 503，而不是落入 500。

### 2.3 `items.js:76-99` — item 解析发生在写循环内部，"先全部校验"未覆盖 item 存在性

`items.js` 头部注释写道："Resolve all keys before writing any item to prevent
malformed batches from leaving a partially applied change"，但这只对 collection key
成立（44-73 行在写入前完成）；item 是否存在的校验（`getItem`，78 行）发生在写循环
**内部**。如果第 $k$ 个 `itemKey` 不存在，前 $k-1$ 个 item 已经执行了
`item.saveTx()`，整个请求随后抛 400 —— 已发生的部分写入没有对应的审计记录
（`endpoint.js:252` 的 `WikiOrgAudit.record` 只在 handler 成功返回后才执行）。

这与计划 §11.4 的"中途失败后可根据审计记录重试，且重复运行幂等"存在落差：幂等性保证了
重试安全，但审计记录的可追溯性在部分失败时丢失。

**修复方向**：将 item 存在性校验挪到 44-73 行的准备循环中（与 collection key 校验一起，
配合 2.2 的异步加载修复）；作为兜底，也可以在写循环的 catch 分支里把已完成的
`results` 一并写入审计日志和错误响应体。

### 2.4 `migration.js:163` 与 `:176` — `getChildItems`/`loadDataTypes` 调用顺序颠倒

172-174 行的注释准确描述了约束："Load both child data types before calling
getChild*() or eraseTx(), whose descendant traversal requires the parent object's
child-collection cache to be initialized"，但代码顺序与注释相反：163 行的
`c.getChildItems(true)` 检查（用于判断 collection 是否为空）发生在 176 行的
`Zotero.Collections.loadDataTypes(pending, [...])` **之前**。

对 `Zotero.Collections.getByLibrary(libraryID, true)` 拿到的对象没有影响（启动时
`Collections.loadAll` 已加载全部数据类型），但对 `_loadByKeys()` → `getAsync()`
只加载 primaryData 的对象（专门为"缓存里没有、只存在于 DB 里的历史行"这一路径准备的）
会在 163 行触发 `UnloadedDataException` → 500。这恰好是该分支存在的目的场景，也是最容易
在实际清理历史数据时触发的路径。

**修复方向**：把 176 行的 `loadDataTypes` 调用移到 150 行判空循环之前。

### 2.5 `migration.js:163` — `getChildItems(true)` 排除回收站条目，与空判定意图不符

`Zotero.Collection.prototype.getChildItems` 签名同样是
`(asIDs, includeTrashed)`。当前调用 `c.getChildItems(true)` 只传了 `asIDs`，
`includeTrashed` 默认为 `false`，即**不统计回收站中的条目**。而
`collections.js:47-49` 的 `itemCountMap()`（供 `list`/`inspect` 展示用）明确注释
"Rows include trashed items, which matches what the migration audit needs"，两处口径
不一致。

实际影响：一个包含 3 个已放入回收站条目的历史 collection，`inspect` 会如实报告
`itemCount: 3`，但 `eraseLegacy` 内部的空判定 `getChildItems(true)` 返回空数组，
判定为"空"而放行删除；`eraseTx()` 底层 `_eraseData` 执行
`DELETE FROM collectionItems WHERE collectionID IN (...)`，无差别删除该 collection
（及其历史子节点）与这些条目的关联，与 README 和计划 §4 "不删除文献"、"不修改条目已有
collection 列表" 的边界相悖（条目本身不会被删除，但其到该 collection 的归属关系会被移除）。

**修复方向**：改为 `c.getChildItems(true, true)`，与 `itemCountMap()` 口径一致。

## 3. 中优先级：与 Zotero 平台事实或计划文档不符

### 3.1 `defaults/preferences/prefs.js` 不会被 Zotero 7+/10 加载

`plugins.js` 的 `setDefaultPrefs()` 固定读取
`addon.getResourceURI("prefs.js").spec`，即**插件包根目录**下的 `prefs.js`；
`defaults/preferences/` 是 Zotero 6 及更早版本的路径约定，在当前 Zotero 10 主线
构建中不会被读取。

影响：`enabled`/`auditLog`/`token` 三个默认偏好实际不会被注册到
`about:config`，用户在 UI 里看不到可配置项（代码对 `Zotero.Prefs.get` 的
`undefined` 情况都做了兜底，所以功能不受影响，但可发现性和可配置性受损）。

另外三处文档相互矛盾：`docs/zotero-internal-api-plugin-plan.md` §15.3 写
"默认偏好移至 `defaults/preferences/prefs.js`"；`zotero_plugin/README.md`
Layout 一节写的却是根目录 `prefs.js`。

**修复方向**：将 `defaults/preferences/prefs.js` 移到 `zotero_plugin/prefs.js`，
同步更正两处文档描述。

### 3.2 `fs.js:73-96` — IOUtils/PathUtils 的模块降级路径是死代码，且目标 URL 不存在

`resource://gre/modules/IOUtils.sys.mjs`、`PathUtils.sys.mjs` 并不存在——
`IOUtils`/`PathUtils` 是 WebIDL 全局对象，不是 ESM 模块。真正的注入方式已在
`plugins.js` 确认：`Object.assign(scope, { IOUtils, PathUtils, ... })` 在
bootstrap 作用域创建时直接挂载，所以只要插件运行在 Zotero bootstrap 沙箱里，
这两个全局必定存在，`loadModule()` 分支永远不会被触达。

如果未来因为某种原因这两个全局确实缺失，当前 fallback 会抛异常并被
`fs.js:85`/`93` 的 catch 吞掉（只留 debug 日志），随后 `writeUTF8`/`readUTF8`
降级到 `Zotero.File`，而 `setPrivatePermissions` 会直接抛
"IOUtils.setPermissions is unavailable" —— 这条链路会让 token 文件永远写不出，
`health` 永远返回 503，且现象和真正原因（`IOUtils` 缺失）之间隔着好几层日志。

文件头注释把 v0.1.0 的失败原因归为 "the plain globals" 不可用，但
`README.md` troubleshooting 一节又将根因归为 `Zotero.DataDirectory.dir.path`
返回 `undefined`（对应 `WikiOrgFs.dataDirPath()` 里已经修复的问题）——
两处对同一版本历史的归因不一致。

**修复方向**：删除 `loadModule()`/`ChromeUtils.importESModule` 降级分支，直接使用
全局 `IOUtils`/`PathUtils`；若确认缺失应报出明确、单一的错误信息。

### 3.3 `fs.js:34-53` — 审计日志"读旧内容+整体重写"很可能是对 `appendOrCreate` 的误诊

IOUtils 的 `WriteMode` 中，`"append"` 在目标文件**不存在**时会拒绝写入
（这是规范行为，用于防止误创建）；应该使用的是 `"appendOrCreate"`。当前代码注释
"the append mode failed empirically"，但首次运行时审计文件本就不存在，用
`"append"` 失败属预期现象，不代表平台缺陷。

当前"读旧内容+整体重写"的实现代价：

- 每次追加都是 $O(n)$ 的全量读写，$n$ 为审计日志当前大小；
- **非原子操作**——如果进程在"读出旧内容"之后、"写回合并内容"之前崩溃或被杀，
  会导致整份审计日志被截断为空，比"丢失最新一条追加"更糟；
- `items/assign` 单次最多处理 2000 条 item（`items.js:7`
  `MAX_ASSIGNMENTS`），审计记录随批量操作显著增长，与文件头注释
  "Event volume is tiny" 的假设不符。

**修复方向**：改用
`IOUtils.writeUTF8(path, line, { mode: "appendOrCreate" })`；此结论基于
IOUtils 文档行为推断，未在本机实测，建议在下一次实机验证时补充确认。

### 3.4 `auth.js:90-91` — token 文件写入未做原子替换，权限设置存在时间窗口

计划 §4.2 明确要求"写文件时采用临时文件 + 原子替换，避免崩溃留下半写入
token"，当前实现是 `writeUTF8()` 后再 `setPrivatePermissions()`——两次调用
之间存在一个文件已包含明文 token、但权限还是创建时默认权限（通常
`0644`，本机可读）的窗口期；如果进程在两次调用之间异常终止，文件会以非私有
权限残留在磁盘上。

**修复方向**：IOUtils 原生支持 `{ tmpPath }` 选项做原子替换；或调整顺序为
"创建空文件 → 立即设置 0600 权限 → 写入内容"，避免明文 token 在宽权限窗口内
落盘。

### 3.5 `endpoint.js:137-140` — health 的 503 判定与写端点行为不一致

当 token 文件/审计日志写入失败（`startupError` 非空）时，`health` 返回
503/`degraded`；但 `create`/`assign` 等写端点并不检查
`WikiOrganizerPlugin.startupError` 或 `startupReady`，会照常返回 200。
计划 §4.6 的意图是"探测失败时，endpoint 不应执行写入"，当前实现只有
`health` 遵守了这一点，实际写入路径未受阻。

**修复方向**：二选一 —— 让 `WikiOrgEndpoint.handle()` 对写方法额外检查
`startupReady`；或修改文档，明确 `startupError` 仅反映"便利文件"（token 镜像/
审计日志）写入状态，不代表核心写入能力受损。

## 4. 低优先级：加固与文档一致性

- **`auth.js:24` token 随机源**：`Zotero.Utilities.randomString` 底层用
  `Math.random()`（已在 `utilities.js` 确认），不是 CSPRNG。bootstrap 沙箱里
  已注入 `crypto` 全局（`plugins.js` 的 `wantGlobalProperties` 列表），
  `crypto.getRandomValues` 可以零成本替换，规避可预测种子带来的理论风险
  （即使当前只服务于本机 loopback 场景）。
- **`endpoint.js:113`、`:148` 错误详情外泄**：500 响应体和 health 的
  `startupError` 字段回传完整 `e.stack`；计划 §4.6 要求"日志只记录 API 名称和
  错误类型，不记录 token、文献内容或附件路径"。当前虽未泄露 token/文献内容，
  但堆栈中可能包含本机文件系统路径等环境细节，建议裁剪后再暴露给远程响应。
- **`tools/zotero_client.py:373` `assign_items()` 绕过 loopback 校验**：
  该函数的 `base_url` 参数默认 `DEFAULT_BASE_URL`，且直接使用调用方传入的
  `base_url`，不经过 `_resolve_base_url()` 的校验链路。当前没有内部调用者，
  但作为模块导出的公开函数，若未来被脚本以自定义 `base_url` 调用，将绕过
  "始终拒绝非 loopback 地址"这一在计划 §15.3 中已作为安全修复项列出的约束。
- **`collections.js:51` `itemCountMap()` 直接查询 `Zotero.DB`**：
  进程内只读查询没有越过"不碰 SQLite 文件"的红线（`Zotero.DB` 是 Zotero 自己
  的连接），但 `getByLibrary` 返回的对象已经加载了 `childItems` 数据，理论上可以用
  `collection.getChildItems(true, true).length` 替代，减少一次原始 SQL 并让计数
  口径与 `migration.js` 的判空逻辑（3.5 节修复后）共享同一路径。
- **`plugin.js:76` `cleanup()` 不取消 in-flight 的 `_runStartupTasks`**：
  快速 enable → disable 插件时，已经在跑的启动任务（写 token 文件/审计记录）
  会在 `shutdown()` 之后继续执行完成，理论上可能在插件已卸载状态下继续写文件。
  影响面很小（本机场景下几乎不会触发），列为已知限制即可。
- **`package_xpi.py` 用 `rglob()` + 排除表打包**：任何未被排除表覆盖的
  杂散文件（编辑器临时文件、`.orig` 等）都会被打进 XPI。改成显式的
  allowlist（列出 `bootstrap.js`、`manifest.json`、`README.md`、
  `src/*.js`、`prefs.js`）比维护排除表更不容易意外夹带文件。
- **`zotero_plugin/README.md` 内部自相矛盾/过期**：
  - `:121-122` 声称 `migration/erase`（eraseTx）"**not** exposed in v1"，
    与 `:78` 端点表中列出的 `POST /wiki-organizer/v1/migration/erase`
    直接矛盾；
  - Layout 一节缺少 `src/items.js`，`prefs.js` 位置的描述与 3.1 节的实际
    加载路径不符；
  - "Semantics worth knowing" 一节仍将 `migration.js` 整体描述为只读，
    未提及 `eraseLegacy`；
  - "Audit log" 一节列出的动作类型缺少 `legacy_collections_erase` 和
    `item_collection_assign`（对照 `endpoint.js:241`、`:252` 的实际
    `WikiOrgAudit.record` 调用）；
  - "In practice the client works with no configuration at all" 只对
    Linux 的 `~/.zotero/zotero/*/prefs.js` 路径成立，`tools/zotero_client.py`
    尚未实现 `docs/zotero-cross-platform-support-plan.md` §4.1 描述的
    macOS/Windows profile 发现逻辑，这句话在跨平台语境下会误导用户。
- **`docs/zotero-internal-api-plugin-plan.md` §7.2/§15.3 落后于实际实现**：
  §7.2 的"建议 endpoint"列表没有 `POST /wiki-organizer/v1/items/assign`
  （对应计划 §3.2 第二阶段目标，但落地时机文档未更新说明）；§15.3 记录的
  插件版本停在 0.1.5，当前 `manifest.json` 已是 0.1.9，中间的行为变化
  （尤其是 `items/assign`、`migration/erase` 的落地）未追加记录。
- **`manifest.json` 的 `strict_min_version: "9.0"`**：
  `docs/zotero-cross-platform-support-plan.md` §2 明确 Zotero 9.x 上的
  header 小写化 proxy、单参数 `init` 契约等均"待验证"，仅在本机 Zotero 10
  上核实过源码行为。当前 manifest 允许在未经验证的 9.x 上安装，与"设计支持"
  和"已验证支持"应分开标注的原则（§6 尾段）不完全一致，建议在文档中明确
  9.x 目前是"允许安装但未验证"状态。

## 5. 验证记录

以下内容已在本机核实（只读，未产生任何写入）：

```text
$ uv run python -X utf8 tools/zotero_client.py health --json
{
  "status": "ok", "ready": true, "pluginVersion": "0.1.9",
  "zoteroVersion": "10.0.SOURCE.22f08d1ce",
  "libraryID": 1, "collectionCount": 83, "startupError": null
}

$ uv run python -X utf8 tools/zotero_client.py health --token WRONGTOKEN
错误: HTTP 401：token 缺失或错误 ...

$ uv run python -X utf8 tools/zotero_client.py create \
    --name "review-probe-do-not-create" \
    --parent "__review_probe_nonexistent_parent__"
错误: HTTP 400：请求参数错误：Parent collection '...' was not found ...
```

静态检查：

```text
node --check zotero_plugin/bootstrap.js zotero_plugin/src/*.js   → 全部通过
uv run python -X utf8 -m unittest tests/test_zotero_client.py   → 14 passed
uv run ruff check tools/zotero_client.py zotero_plugin/package_xpi.py \
    tests/test_zotero_client.py                                  → 无告警
```

第 2 节全部结论均对照本机 `/usr/lib/zotero/app/omni.ja` 解出的以下源码文件
逐行核实签名，不依赖旧版官方文档或记忆：

```text
chrome/content/zotero/xpcom/data/collection.js
chrome/content/zotero/xpcom/data/dataObjects.js
chrome/content/zotero/xpcom/data/item.js
chrome/content/zotero/xpcom/data/library.js
chrome/content/zotero/xpcom/plugins.js
chrome/content/zotero/xpcom/server/server.js
chrome/content/zotero/xpcom/utilities/utilities.js
chrome/content/zotero/xpcom/zotero.js
```

## 6. 建议修复顺序

1. 2.1、2.4、2.5（`migration.js` 内三处签名/顺序错误）——同一文件，建议合并
   一次修改后重新走一遍阶段 D 的 `inspect`/`erase-legacy` 手工验证。
2. 2.2、2.3（`items.js` 的异步加载与校验顺序）——涉及 `waitUntilReady()` 的
   调用约定，建议同时检查 `collections.js` 里是否有类似的隐式加载假设。
3. 3.1（`prefs.js` 路径）——独立的小改动，顺手更新 README 和计划文档中的
   矛盾描述。
4. 3.2–3.5 与第 4 节按时间余量处理；均为加固/一致性问题，不阻塞阶段 D/E/F
   的功能验证。

修复后需要重新打包 XPI 并在实际 Zotero 环境中至少覆盖：一个带子 collection 的
历史节点清理、一次在 Zotero 刚启动（未点开 My Library）时的 `assign` 调用、
一个含回收站条目的历史 collection 的 `inspect`/`erase-legacy` 组合。
