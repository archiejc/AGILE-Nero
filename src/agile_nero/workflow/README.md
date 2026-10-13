# 任务流程与编排 · workflow

**当前状态：固定离线流程已有；Agent 工作流待接入。**

## 职责与边界

组合规划、验证和预演，汇总状态与错误；框架调度放在本模块。

## 输入与输出

run_task(DrawingTask) → WorkflowResult；run_tool(dict) → JSON 兼容字典。

## 先读哪些文件

- [共享数据契约](../contracts/README.md)
- [整体模块导航](../../../docs/modules.md)
- [offline.py](offline.py)

## 如何验证

测试入口：[tests/offline/workflow](../../../tests/offline/workflow)。

## 双线交付边界

- 所属：两条线的公共编排。
- 交付：任务 + 配置 + 工具结果 → 阶段状态与报告。
- 验收关口：J1，定义见 [双线契约](../../../docs/architecture/track-contracts.md)。

## 下一步

先建立版本绑定和离线汇合，再加入 Agent；任务准备与授权执行分开，部分物理执行后不得自动重放。
