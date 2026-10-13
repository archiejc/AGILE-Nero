# 设备诊断 · robot/diagnostics

**当前状态：已有状态解码、重连修复、诊断 CLI 与显式反馈配置工具。绘画执行器仍未适配。**

## 职责与边界

读取并解码状态、处理传输资源与诊断报告。默认 NativeGsUsbBus 只允许固件查询；独立的 FeedbackSetupBus 仅放行已审查的 1.11 使能/推送配置报文与查询，阻止运动目标。

enable-feedback 必须携带 --enable-motors 和确认的 --firmware 1.11。该命令会改变设备状态，不能作为普通开发冒烟测试。模块导入和 CLI --help 不建立设备连接。

## 输入与输出

设备配置/反馈帧 → 状态与诊断报告。诊断连接会访问真实设备。

## 先读哪些文件

- [共享数据契约](../../contracts/README.md)
- [整体模块导航](../../../../docs/modules.md)
- [cli.py](cli.py)
- [state.py](state.py)
- [transport.py](transport.py)
- [commission.py](commission.py)

## 如何验证

测试入口：[tests/robot](../../../../tests/robot)。

该目录的 conftest.py 拦截真实 USB、CAN 和网络 I/O，测试只使用模拟设备或离线反馈帧。原 agile_nero.commission、cli、state、transport 路径保留兼容别名。

## 下一步

在单独授权的设备任务中继续核对长时间/长间隔连接问题。2026-10-13 历史记录包含上午六次短间隔重连通过和下午再次失联，不能据此宣布持续通信已稳定。
