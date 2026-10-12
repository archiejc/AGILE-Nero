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

## 下一步

文件输入闭环后增加 task_id、持久化与受控重试，再包装 Codex SDK / LangGraph。
