# 下一步怎么推进

一次完成一个可离线检查的闭环，每一步保留输入、输出、配置与验证结果。

## 已有基础

- 手工 DrawingTask JSON → 平面路径 → 几何检查 → JSON / SVG。
- 独立数据契约、预演接口、固定工作流和兼容命令。
- SDK 状态解码与 CAN 诊断代码；绘画执行适配固定拒绝执行。

## 推荐顺序

| 顺序 | 交付目标 | 主要模块 | 完成的判据 |
| --- | --- | --- | --- |
| 1 | 二维 DXF 到线稿预览 | cad、geometry、contracts | 明确支持的实体与单位；生成 DrawingTask 和 SVG；诊断不支持或缺少单位的输入 |
| 2 | 图片到候选笔画 | vision、geometry、contracts | 固定图片与人工参考；保存候选线条及尺度；检查断线、重复和交叉点；建立基线后决定训练 |
| 3 | 文件上传与可追踪任务 | ingestion、api、workflow、artifacts | 上传得到 task_id；可查看阶段、失败原因、笔画预览和产物版本；离线测试仍能独立运行 |
| 4 | 线稿编辑与路径改进 | geometry、planning | 可确认/修正笔画；比较排序、平滑、空行程和抬笔次数；输入与结果可追溯 |
| 5 | 机器人轨迹与 MuJoCo | planning/motion、simulation、contracts | 模型、标定和 TCP 明确；产生带时间的关节轨迹；记录可达性、碰撞与约束检查 |
| 6 | 授权执行与结果评估 | robot、workflow、artifacts | 硬件验收完成；验证绑定轨迹版本；操作者明确授权后进入独立实机任务，记录停止与反馈 |
| 7 | Agent 编排 | workflow、api | 包装稳定工具；受控重试和状态持久化；与固定流程比较完成率及调用成本 |

硬件状态与通信稳定性作为独立工作线推进，不影响前四步的离线文件处理。实机运动仍需新的明确任务授权。

## 建议的下一条任务

“实现二维 DXF 的最小输入适配，输出已有 DrawingTask，复用离线流程生成 SVG。首轮支持范围明确列出，对单位未知和不支持实体给出诊断，并用小型样例验证。”

起点是 [cad](../src/agile_nero/cad/README.md) 和 [geometry](../src/agile_nero/geometry/README.md)。先确定格式/实体和验收样例，再选择解析依赖与实现细节。

## 每次交付留下什么

- 当前实现与边界：模块 README。
- 输入输出契约：contracts 或适配器的 ports。
- 可复现证据：examples 与对应 tests。
- 本次运行产物：outputs 中的任务目录。
- 跨模块变化：更新本路线图和架构说明。
