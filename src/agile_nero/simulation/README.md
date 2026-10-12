# 离线预演与仿真适配 · simulation

**当前状态：几何预演与接口已有；MuJoCo 待接入。**

## 职责与边界

提供可替换的预演后端，报告所验证的范围和精确路径指纹。

## 输入与输出

Toolpath → PreviewReport；机器人仿真接入时补齐轨迹/模型/标定版本。

## 先读哪些文件

- [共享数据契约](../contracts/README.md)
- [整体模块导航](../../../docs/modules.md)
- [offline.py](offline.py)
- [ports.py](ports.py)

## 如何验证

测试入口：[tests/offline/workflow](../../../tests/offline/workflow)。

## 下一步

结合 motion 的轨迹契约接入实际 NERO 模型；明确几何、碰撞和接触验证范围。
