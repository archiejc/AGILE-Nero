# 机械臂 SDK 与执行边界 · robot

**当前状态：执行占位固定拒绝；诊断代码已有。**

## 职责与边界

集中设备相关依赖和执行边界；诊断实现在 diagnostics 子目录。

## 输入与输出

ports.py 保留执行协议，UnadaptedRobotBackend 始终拒绝执行。

## 先读哪些文件

- [共享数据契约](../contracts/README.md)
- [整体模块导航](../../../docs/modules.md)
- [ports.py](ports.py)

## 如何验证

测试入口：[tests/offline/robot](../../../tests/offline/robot)。

## 下一步

先核对另一工作树的未提交诊断变更；硬件执行须以新的明确授权和验收任务接入。
