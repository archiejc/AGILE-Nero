# 设备诊断 · robot/diagnostics

**当前状态：已有状态解码、CAN 传输和诊断 CLI。**

## 职责与边界

读取并解码状态、处理传输资源与诊断报告；当前 PR 后端只允许固件查询写入。

## 输入与输出

设备配置/反馈帧 → 状态与诊断报告。诊断连接会访问真实设备。

## 先读哪些文件

- [共享数据契约](../../contracts/README.md)
- [整体模块导航](../../../../docs/modules.md)
- [cli.py](cli.py)
- [state.py](state.py)
- [transport.py](transport.py)

## 如何验证

测试入口：[tests/robot](../../../../tests/robot)。

## 下一步

按迁移表核对主目录的 commission、重连与 CLI 改动；软件测试不能证明实机重连稳定。
