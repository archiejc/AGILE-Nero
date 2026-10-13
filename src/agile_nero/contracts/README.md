# 共享数据契约 · contracts

**当前状态：已实现。**

## 职责与边界

定义共享笔画、配置、路径与版本化 JSON；具体算法放业务模块。

## 输入与输出

DrawingTask JSON → 不可变 DrawingTask / Stroke / Toolpath。

## 先读哪些文件

- [共享数据契约](README.md)
- [整体模块导航](../../../docs/modules.md)
- [drawing.py](drawing.py)

## 如何验证

测试入口：[tests/offline/contracts](../../../tests/offline/contracts)。

## 双线交付边界

- 所属：两条线之间的共享契约。
- 交付：DrawingTask / Toolpath；后续 MotionPlan / ExecutionPlan 等。
- 验收关口：C2 / J1，定义见 [双线契约](../../../docs/architecture/track-contracts.md)。

## 下一步

现有 JSON schema 不变。新增契约先固定 frame、单位、后端 ID、全部版本指纹及错误语义，明确设计与已实现的区别。
