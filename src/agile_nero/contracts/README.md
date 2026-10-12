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

## 下一步

新输入适配接入前，确定来源、单位和置信度如何记录；修改 schema 时明确兼容策略。
