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

## 双线交付边界

- 所属：机器人线。
- 交付：有效授权的 ExecutionPlan → 事件/反馈/停止结果（拟定）。
- 验收关口：R2 / H1，定义见 [双线契约](../../../docs/architecture/track-contracts.md)。

## 下一步

能力放 profiles，准备/执行适配放 backends，设备诊断留 diagnostics。现有 execute(Toolpath) 只是禁用占位，不作为未来统一执行契约。
