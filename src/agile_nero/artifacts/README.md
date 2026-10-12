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

## 下一步

任务 API 接入时把 JSON 写入与目录管理收拢到这里，保持业务计算独立于文件系统。
