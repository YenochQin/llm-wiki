# Zotero Wiki Organizer 跨平台支持计划

## 1. 目的

本文档规划将 Zotero Wiki Organizer 从“Linux + Zotero 10 已验证”扩展为 macOS、Windows 和 Linux 三个平台可安装、可配置、可验证的版本。

本计划只涉及跨平台兼容性，不改变插件的核心安全边界：所有写入仍必须通过 Zotero 进程内部的 `Zotero.Collection` 和 `saveTx()` 完成，Python 客户端不直接访问或修改 `zotero.sqlite`。

## 2. 当前状态

### 已验证

```text
Linux + Zotero 10.0.SOURCE
```

已验证内容：

- XPI 可打包和安装。
- bootstrap 生命周期可以加载插件模块。
- Zotero 内置本地服务器 endpoint 可用。
- collection 查询和 `create-if-missing` 可用。
- token preference 和 token 文件可以创建。
- Python 客户端可以通过 uv 环境调用接口。

### 尚未验证

- macOS 安装、启动、路径发现、权限和同步。
- Windows 安装、启动、路径发现、权限和同步。
- 不同 Zotero 9/10 小版本之间的内部 API 差异。
- Zotero 关闭、重启、升级和插件更新后的状态迁移。

## 3. 支持范围定义

### 3.1 目标支持矩阵

| 平台 | Zotero 版本 | 目标状态 |
|---|---|---|
| Linux | Zotero 9.x/10.x | 已有环境回归 + 扩展验证 |
| macOS | Zotero 9.x/10.x | 待验证 |
| Windows | Zotero 9.x/10.x | 待验证 |
| 任意平台 | Zotero 11+ | 暂不承诺，需重新适配内部 API |

### 3.2 “支持”的最低定义

某个平台只有同时满足以下条件，才可以标记为已支持：

1. XPI 能成功安装。
2. Zotero 启动时插件无未捕获异常。
3. `health` 能返回就绪状态。
4. `list` 能返回个人库 collection 树。
5. `create-if-missing` 能创建合法 collection key。
6. 重复创建保持幂等。
7. Zotero 重启后 collection 持久存在。
8. 同步不出现 `invalid collection key` 或上传停滞。
9. token 不会暴露给非授权本地进程或写入普通日志。
10. Python 客户端能在该平台的仓库 uv 环境中运行。

## 4. 待补充工作

### 4.1 跨平台 profile 和 token 配置发现

当前 Python 客户端自动读取 `~/.zotero/zotero/*/prefs.js`，这是 Linux 目录约定，不足以覆盖 macOS 和 Windows。

需要实现一个独立的 profile 发现函数，按以下优先级处理：

1. 用户显式传入 `--token`。
2. 环境变量 `ZOTERO_WIKI_ORGANIZER_TOKEN`。
3. 用户显式传入 `--token-file`。
4. 环境变量 `ZOTERO_WIKI_ORGANIZER_TOKEN_FILE`。
5. 根据操作系统搜索 Zotero profile 的标准目录。
6. 如果找不到，返回包含平台相关路径提示的可读错误。

建议搜索位置：

```text
Linux:
  ~/.zotero/zotero/*/prefs.js

macOS:
  ~/Library/Application Support/Zotero/Profiles/*/prefs.js

Windows:
  %APPDATA%/Zotero/Zotero/Profiles/*/prefs.js
```

实现要求：

- 使用 `platform.system()` 或等价标准库接口，不依赖 shell。
- 支持路径中空格和非 ASCII 字符。
- 不递归扫描整个用户目录。
- 只读取 `prefs.js` 中对应的插件 preference。
- 多 profile 命中时给出确定性排序和明确提示。
- profile 自动发现失败不能阻止用户使用显式 token 参数。

### 4.2 插件文件路径和权限

插件中的 [fs.js](../zotero_plugin/src/fs.js) 需要在三种平台验证：

- `Zotero.DataDirectory.dir` 是字符串还是文件对象。
- `PathUtils.join()` 能否正确处理平台路径分隔符。
- `IOUtils.writeUTF8()` 和 `IOUtils.setPermissions()` 是否可用。
- Zotero 数据目录尚未完全初始化时，启动重试是否可靠。

token 文件策略：

- Zotero preference 始终是权威存储。
- token 文件只作为客户端便利入口。
- Unix 平台设置 `0600`。
- Windows 平台验证文件 ACL 或等效私有权限；如果无法保证，应将 token 文件视为可选，并要求使用 preference/环境变量。
- 写文件时采用临时文件 + 原子替换，避免崩溃留下半写入 token。
- 不在 token 文件名、普通 debug 日志或审计日志中包含 token。

### 4.3 XPI 安装和插件生命周期

需要在 Linux、macOS、Windows 分别验证：

1. 从 `Tools → Plugins` 安装 `zotero-wiki-organizer-*.xpi`。
2. Zotero 重启后自动加载插件。
3. 插件升级时旧 endpoint 被正确注销，新 endpoint 被注册。
4. 插件禁用或卸载时 endpoint 被注销。
5. 插件卸载不删除 collection、item、附件或用户配置。
6. 同一插件不会被重复加载两次。
7. `manifest.json` 的 `strict_min_version`/`strict_max_version` 与目标 Zotero 版本匹配。

升级策略：

- 每次行为或兼容性修复都提升插件版本号。
- XPI 文件名从 manifest 版本自动生成。
- `update_url` 未发布时不要声称支持自动更新。
- 重大 Zotero 内部 API 变化应发布新的兼容性说明，而不是静默尝试。

### 4.4 本地 endpoint 和网络边界

三个平台都必须验证：

- endpoint 只挂在 Zotero 的 loopback server 上。
- 客户端始终拒绝非 loopback URL。
- `Authorization: Bearer <token>` 是唯一认证方式。
- query-string token 永远不启用。
- Zotero 的 `Zotero-Allowed-Request: 1` 请求头在三个平台均能正常工作。
- 浏览器 UA、`Origin` 和 `Host` 检查不会导致合法 Python 客户端被静默丢弃。
- Zotero 尚未完成启动时返回 `503`，而不是返回半初始化数据。

### 4.5 Python 客户端跨平台行为

需要补充：

- Windows 路径和环境变量测试。
- macOS 路径中空格的测试。
- 非 ASCII 用户名和 Zotero 数据目录测试。
- `--json` 模式在所有平台都只输出 JSON。
- 连接失败、token 缺失和插件未安装时都返回稳定的退出码。
- 客户端不调用 `pgrep`、`kill` 或平台特定进程命令。
- 所有 Python 命令和测试仍通过：

  ```bash
  uv run python -X utf8 ...
  ```

### 4.6 Zotero 内部 API 兼容性探测

插件启动时应记录但不泄露敏感信息的兼容性摘要：

- Zotero 版本。
- 插件版本。
- `Zotero.Collection` 是否存在。
- `Zotero.Collections.getByLibrary` 是否存在。
- `saveTx()` 是否存在。
- `Zotero.Server.Endpoints` 是否可用。
- `IOUtils`/`PathUtils` 能力。

探测失败时：

- endpoint 不应执行写入。
- `health` 返回 `503` 或明确的兼容性错误。
- 日志只记录 API 名称和错误类型，不记录 token、文献内容或附件路径。

### 4.7 同步和数据保护回归

每个平台都需要建立独立测试库或可恢复快照，测试以下场景：

1. 创建顶层 collection。
2. 创建子 collection。
3. 重复创建同名同父级 collection。
4. 创建同名不同父级 collection。
5. Zotero 重启后查询。
6. 同步完成后再次查询。
7. 检查原有 item 数量和 collection 关联没有减少。
8. 检查插件卸载不会删除用户数据。
9. 模拟 endpoint 失败，确认客户端不会盲目重复写入。
10. 检查 token 和审计日志文件权限。

## 5. 测试矩阵

### 5.1 静态测试

在仓库中运行：

```bash
uv run python -X utf8 -m unittest tests/test_zotero_client.py
uv run ruff check tools/zotero_client.py tools/zotero_create_collection.py \
  zotero_plugin/package_xpi.py tests/test_zotero_client.py
node --check zotero_plugin/bootstrap.js
for file in zotero_plugin/src/*.js; do node --check "$file"; done
uv run python -X utf8 zotero_plugin/package_xpi.py
unzip -t zotero_plugin/dist/zotero-wiki-organizer-*.xpi
```

### 5.2 平台运行测试

每个平台至少记录以下信息：

```text
OS 版本
Zotero 版本
插件版本
profile 路径
dataDir 路径
endpoint 端口
health 结果
list 结果
create 结果
重启结果
同步结果
```

不得在报告中记录真实 token。

### 5.3 自动化与人工测试分工

可自动化：

- Python 路径发现。
- token preference 解析。
- loopback URL 校验。
- JSON 输出。
- XPI manifest 和压缩包检查。
- mock endpoint 下的错误处理和幂等行为。

需要真实 Zotero 环境：

- XPI 安装。
- 内部 API 调用。
- collection 持久化。
- Zotero 重启。
- 同步队列。
- 文件权限实际效果。

## 6. 配置和文档更新

需要同步更新：

- `zotero_plugin/README.md`：平台支持矩阵、profile 路径、token 配置。
- `docs/zotero-internal-api-plugin-plan.md`：引用本文档并记录验证状态。
- `tools/zotero_client.py --help`：平台无关的配置说明。
- 测试报告：记录每个平台的 Zotero 与插件版本。

文档不得把“设计支持”写成“已验证支持”。

## 7. 回滚方案

### 插件回滚

- 在 Zotero 插件管理器中禁用或卸载插件。
- 保留 endpoint 和审计日志用于诊断。
- 不删除任何 collection 或 item。

### 数据回滚

- 任何同步回归前创建独立测试库快照。
- 生产库迁移前保留 `zotero.sqlite` 备份及对应 WAL/SHM 状态。
- 只有在 Zotero 完全退出后恢复数据库备份。
- 恢复后先检查 collection/item 数量，再恢复同步。

## 8. 实施顺序

### 阶段 A：路径与配置抽象

- 实现跨平台 profile 搜索。
- 补充路径、token、非 ASCII 和多 profile 测试。
- 修正 CLI 文档。

### 阶段 B：插件文件与权限验证

- 在三种平台验证 `DataDirectory`、`PathUtils`、`IOUtils`。
- 验证 token 文件私有权限。
- 必要时增加原子写入和平台降级策略。

### 阶段 C：XPI 和生命周期验证

- 三个平台安装、重启、升级、禁用和卸载测试。
- 确认 endpoint 注册/注销无残留。

### 阶段 D：同步和数据保护验证

- 在独立测试库完成 collection 创建和同步回归。
- 验证不影响既有 item collection 归属。

### 阶段 E：发布支持矩阵

- 只有完成最低验收标准的平台才标为“已支持”。
- 发布插件版本、XPI、测试报告和已知限制。

## 9. 验收标准

跨平台版本必须满足：

1. Linux、macOS、Windows 均能安装相同 XPI，或明确记录平台专用构建差异。
2. 三个平台均能通过内部 API 创建 collection。
3. 三个平台均能正确发现或显式配置 token。
4. 三个平台均拒绝非 loopback endpoint。
5. 三个平台均不接受 query-string token。
6. 三个平台的 token 文件权限策略可解释、可测试。
7. 三个平台的 `health/list/create` 行为一致。
8. 三个平台重启后 collection 持久化。
9. 三个平台同步无 invalid collection key 错误。
10. 客户端和插件不会修改、移动或删除已有文献归属。
11. 版本和文档准确区分“已验证”和“设计支持”。

## 10. 当前状态

当前状态：

- Linux：插件核心和客户端已验证；跨平台扩展测试尚未完成。
- macOS：待阶段 A–D 验证。
- Windows：待阶段 A–D 验证。
- Zotero 11+：不在当前承诺范围内。

在阶段 A–D 完成前，不应对外宣称插件是完全全平台通用的。
