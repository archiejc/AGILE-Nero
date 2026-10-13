# 产物导出与存储 · artifacts

**当前状态：SVG 导出已有；任务存储待扩展。**

## 职责与边界

保存和导出可检查的结果；当前 JSON 文件写入仍由 api/cli.py 完成。

## 输入与输出

已验证 Toolpath → SVG；后续扩展原文件、报告、事件和版本化任务存储。

## 先读哪些文件

- [共享数据契约](../contracts/README.md)
- [整体模块导航](../../../docs/modules.md)
- [svg.py](svg.py)

## 如何验证

测试入口：[tests/offline/artifacts](../../../tests/offline/artifacts)。

## 双线交付边界

- 所属：两条线的公共产物管理。
- 交付：原文件/中间产物/程序/报告/事件 → 版本化存储引用。
- 验收关口：J1，定义见 [双线契约](../../../docs/architecture/track-contracts.md)。

## 下一步

现有 SVG 导出继续可用；未来从 api/cli 收拢 JSON 写入与任务存储，记录精确程序和配置指纹。
