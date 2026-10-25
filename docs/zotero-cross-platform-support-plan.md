# Zotero Wiki Organizer：跨平台状态与验收

本文保留原文件名作为引用入口，集中记录跨平台实现与验证缺口。通用数据操作约束及分类流程见 [插件状态与验收](zotero-internal-api-plugin-plan.md)，用法见 [插件 README](../zotero_plugin/README.md)。

## 当前实现状态

核对日期：2026-10-25（Asia/Singapore，UTC+08:00）。代码基线：`fee7ef1057a67488d3f3986db39a68a717b80585`，插件 `0.1.11`；核对时相关实现没有未提交差异。“已实现”不等于三平台已验收。

| 能力 | 当前实现及依据 | 验证边界 |
|---|---|---|
| profile 自动发现 | [zotero_client.py](../tools/zotero_client.py) 按 `platform.system()` 选择 Linux、macOS、Windows 标准目录；只扫描一层 profile 并排序 | 已有 macOS 标准路径测试，Windows/多 profile/非 ASCII 测试不足 |
| token 配置 | 优先级为 CLI token → 环境变量 token → CLI token 文件 → 环境变量 token 文件 → profile preference | 显式配置不依赖自动发现；失败提示仍偏 Linux |
| 文件路径与写入 | [fs.js](../zotero_plugin/src/fs.js) 兼容字符串或 `.path` 数据目录，优先使用 PathUtils/IOUtils；[auth.js](../zotero_plugin/src/auth.js) 使用临时文件和 move，缺少 move 时走直接写入 fallback | 权限设置顺序、Windows ACL、可选镜像降级仍未达标 |
| 生命周期与打包 | [bootstrap.js](../zotero_plugin/bootstrap.js)、[endpoint.js](../zotero_plugin/src/endpoint.js) 实现启动/清理及注册/注销；[package_xpi.py](../zotero_plugin/package_xpi.py) 使用文件 allowlist 和 manifest 版本命名 | 三平台安装、升级、重启效果仍待验证 |
| 本地接口 | 客户端拒绝非 loopback URL；Bearer 认证；携带 `Zotero-Allowed-Request: 1`；启动失败时禁止写入 | 已有部分客户端 mock 测试；真实平台网络行为待验收 |
| 就绪状态 | [plugin.js](../zotero_plugin/src/plugin.js) 等待启动并重试文件任务；health 返回版本及启动状态 | 尚无完整 API 能力探测摘要 |

[manifest.json](../zotero_plugin/manifest.json) 允许 Zotero `9.0`–`10.999` 安装，不能据此宣称所有版本兼容；Zotero 11+ 不在当前范围。

| 平台 | 仓库中可追溯的验证状态 |
|---|---|
| Linux + Zotero 10.0.SOURCE | 有旧版本安装、接口和文件落盘记录；当前 0.1.11 完整回归仍未确认 |
| Linux + Zotero 9.x | manifest 允许安装，未找到完整运行验收记录 |
| macOS / Windows + Zotero 9.x/10.x | 路径分支已实现，未找到完整安装、权限、重启和同步验收记录 |

历史记录出处及本次验证命令见 [插件状态文档](zotero-internal-api-plugin-plan.md)。2026-10-25 的客户端 17 项测试和插件 JavaScript 语法检查通过；未执行三平台集成测试、重新打包或发布检查。

## 剩余缺口

1. **profile 提示与测试。** 当前排序后使用第一个命中的 token，没有多 profile 命中提示；发现失败仍只展示 Linux 路径。需补 Windows `APPDATA`、非 ASCII/空格路径、多 profile、配置优先级及失败退出码测试，并更新 CLI 帮助。
2. **token 文件权限与可选降级。** 当前先写含 token 的临时文件，再设置 `0600`，不能保证创建时即私有；没有 Windows ACL 专门处理或验证证据。缺少权限 API/写镜像失败会使启动失败并阻止写接口，尚未实现原计划要求的“镜像可选，继续使用 preference/环境变量”。无 move 的 fallback 也不能当作原子替换已验收。
3. **完整兼容性探测。** 目前仅有部分对象服务/启动检查；需检查 `Zotero.Collection`、`Collections.getByLibrary`、`saveTx()`、`Server.Endpoints` 和 IOUtils/PathUtils 能力，记录版本及能力摘要。必要能力缺失时禁止写入并给出明确诊断；日志避免 token、文献内容和附件路径。
4. **真实平台验收。** 安装、升级/卸载、重复加载、文件权限、冷启动/重试、重启持久化、同步和既有归属保护没有完整三平台证据，不能由 mock 测试代替。
5. **支持矩阵与发布说明。** README 尚无完整已验证平台矩阵。需随实际结果更新版本范围、已知限制和报告位置；`update_url` 的存在不证明更新源已发布，本次未核实自动更新服务。

最小下一步：补 profile 提示与离线测试，修正 token 镜像权限/降级策略，再在独立测试库开展真实平台验收。

## 验收清单

### 离线检查

- [ ] profile/token 测试覆盖三平台标准目录、Windows 环境变量缺失、空格和非 ASCII、多 profile、缺失/无权限文件及显式配置优先级。
- [ ] 客户端覆盖 `--json` 纯 JSON 输出、网络/认证/插件缺失错误和稳定退出码；始终拒绝非 loopback URL，不自动重试写入。
- [ ] API 能力缺失和镜像不可用的行为有测试；必要能力失败时不写入，镜像可选降级不泄露 token。
- [ ] XPI 打包及压缩包完整性检查通过，版本来自 manifest，只包含 allowlist 文件；记录实际输出及版本。

现有回归入口（不代表以上覆盖已齐全）：

```bash
uv run python -X utf8 -m unittest discover -s tests -p test_zotero_client.py
node --check zotero_plugin/bootstrap.js
for file in zotero_plugin/src/*.js; do node --check "$file"; done
```

### 每个平台的运行验收

在独立测试库或可恢复快照上逐平台执行，遵守配套文档的写入授权与迁移约束。只有完成相应版本的全部运行验收，才标记为已验证支持。

- [ ] 安装、冷启动、重启、升级、禁用及卸载正常；endpoint 无重复注册或残留，用户数据和配置不被删除。
- [ ] `health/list/create/assign` 行为正确；版本信息准确，未就绪返回 503；缺失/错误 token 拒绝访问，query-string token 无效。
- [ ] `Zotero-Allowed-Request`、UA、Origin、Host 与 loopback 行为在该平台符合预期，合法 Python 请求不被静默丢弃。
- [ ] 实际 profile/数据目录含空格及非 ASCII 时可用；数据目录初始化、启动重试和 IOUtils/PathUtils 行为经验证。
- [ ] token preference 可用；镜像从创建起具有私有权限（Unix 0600、Windows ACL 或等效策略），镜像不可用时按规定降级；日志无 token，审计文件权限已检查。
- [ ] 创建顶层/子级、同名同父级幂等、同名不同父级正常；追加归类保留旧关联，写后查询通过。
- [ ] 重启和同步后 collection 持久存在，无 invalid key 或上传停滞；item/附件数量与原有关联不减少，失败后不会盲目重复写入。
- [ ] README 发布对应 OS/Zotero/插件版本、已知限制和报告链接；自动更新能力仅在更新源及升级流程验证后声明。

每份报告记录日期与时区、代码/OS/Zotero/插件版本、profile/数据目录的必要脱敏信息、端口、测试库/快照标识、逐项预期与实际结果、日志和输出位置。未运行项保持未勾选；不得记录真实 token。数据库备份恢复须在 Zotero 退出、备份核实且另行授权后执行。
