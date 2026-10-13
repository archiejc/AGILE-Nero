# 离线预演与仿真适配 · simulation

**当前状态：几何预演与接口已有；MuJoCo 待接入。**

## 职责与边界

提供可替换的预演后端，报告所验证的范围和精确路径指纹。

## 输入与输出

当前 Toolpath → PreviewReport；目标 ExecutionPlan → 后端验证报告，补齐模型/标定/场景/能力版本。

## 先读哪些文件

- [共享数据契约](../contracts/README.md)
- [整体模块导航](../../../docs/modules.md)
- [offline.py](offline.py)
- [ports.py](ports.py)

## 如何验证

测试入口：[tests/offline/workflow](../../../tests/offline/workflow)。

## 双线交付边界

- 所属：机器人线验证；兼容已有内容几何预演。
- 交付：ExecutionPlan + 模型/标定/场景/能力 → 后端验证报告（拟定）。
- 验收关口：R3，定义见 [双线契约](../../../docs/architecture/track-contracts.md)。

## 下一步

保留 PreviewBackend(Toolpath) 离线接口；新增机器人验证契约时区分 nominal_preview 和实际后端语义验证。
