# 外部入口 · api

**当前状态：离线 CLI 已有；上传/任务 HTTP API 待建。**

## 职责与边界

接收参数和输入、调用工作流、输出报告与产物；业务算法由各模块承担。

## 输入与输出

DrawingTask JSON / CLI 参数 → JSON 报告与可选 SVG 文件。

## 先读哪些文件

- [共享数据契约](../contracts/README.md)
- [整体模块导航](../../../docs/modules.md)
- [cli.py](cli.py)
- [__main__.py](__main__.py)

## 如何验证

测试入口：[tests/offline/api](../../../tests/offline/api)。

## 下一步

先通过 ingestion 接入文件，再增加上传、任务查询和结果获取接口。
