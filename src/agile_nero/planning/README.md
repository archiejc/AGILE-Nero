# 平面路径规划 · planning

**当前状态：基础已实现。**

## 职责与边界

生成抬落笔与采样路径，独立检查平面边界、动作顺序和绘制间距。

## 输入与输出

DrawingTask → Toolpath、ValidationReport、路径长度统计。

## 先读哪些文件

- [共享数据契约](../contracts/README.md)
- [整体模块导航](../../../docs/modules.md)
- [planar.py](planar.py)
- [validation.py](validation.py)
- [metrics.py](metrics.py)

## 如何验证

测试入口：[tests/offline/planning](../../../tests/offline/planning)。

## 双线交付边界

- 所属：内容线。
- 交付：DrawingTask → Toolpath + 几何报告。
- 验收关口：C2，定义见 [双线契约](../../../docs/architecture/track-contracts.md)。

## 下一步

保留现有离线接口；使用两直线一圆弧样例比较排序、平滑、空行程和抬笔策略。
