# 2026-10-13 主目录同步与诊断迁移

PR #2 已合并，合并提交为 4879a6b2c1caf8230306b94664518d3ee7efaed4。本地主目录的 main 从 8b4b129 快进到该提交，随后在 codex/migrate-hardware-diagnostics 分支迁移原未提交改动。

## 保留与迁移

| 原内容 | 处理结果 |
| --- | --- |
| cli.py 的反馈配置入口 | 迁入 robot/diagnostics/cli.py，保留显式参数检查 |
| transport.py 的重连修复 | 迁入 robot/diagnostics/transport.py，取消无条件 clear_halt，保留资源释放和允许报文策略 |
| commission.py | 迁入 robot/diagnostics/commission.py；旧导入路径保留兼容别名 |
| 传输和反馈配置测试 | 位于 tests/robot，新增真实 I/O 拦截和入口迁移验证 |
| 重连、配置、网络、移动记录 | 保留于 docs，并区分各日期的观察范围 |
| 原 README 和环境说明的改动 | 整合到新导航和对应模块说明，原始全文保存在本机备份 |
| configs/local 与 .venv | 保留，不重建、不更新依赖 |

## 离线验证

- 51 项测试、59 个子测试通过；设备测试的真实 USB、CAN 和网络 I/O 被主动拦截。
- 25 项标准库离线测试通过。
- 原 .venv/bin/nero --help 能显示新的模块化诊断入口和 enable-feedback 命令。
- 回归测试验证初始化不调用 USB clear_halt / reset，默认后端继续拒绝非固件查询，配置后端继续拒绝运动目标。
- 参数缺失和不支持固件在准备设备之前被拒绝；显式调用的调度测试使用替代函数，无实际设备访问。

这些结果验证迁移后的软件行为。本次未连接设备、未使能电机、未执行实际机械臂运动；历史运动记录属于此前单独授权的任务。

## 本机恢复点

原始 11 个未提交文件已逐个复制并校验 SHA-256，同时保留 Git stash。备份定位文件为 .local/latest-module-sync-backup.txt，完整快照、差异补丁、保护文件指纹及 stash 标识位于其指向的目录。

恢复时先读取 manifest 和 tracked.patch，再按当前模块位置选择性恢复；不要直接把旧文件覆盖到包根兼容入口。测试输出、本机配置、开发环境和本地资料保持在原位置。
