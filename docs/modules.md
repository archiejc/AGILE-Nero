# 按模块找到上下文

每次只需读取：目标模块 README → 相关数据契约 → 对应实现和测试。架构图负责看连接，模块 README 负责说明本模块怎么继续。

内容线交付 DrawingTask / Toolpath；机器人线接收它们并生成目标后端的执行程序。输入输出和验收关口统一见 [双线契约](architecture/track-contracts.md)。

## 模块索引

| 要做的工作 | 模块入口 | 当前状态 |
| --- | --- | --- |
| 共享数据契约 | [contracts](../src/agile_nero/contracts/README.md) | 已实现 |
| 文件接入 | [ingestion](../src/agile_nero/ingestion/README.md) | 规划；当前只有模块说明 |
| 图片识别与线条提取 | [vision](../src/agile_nero/vision/README.md) | 规划；当前只有模块说明 |
| CAD 几何解析 | [cad](../src/agile_nero/cad/README.md) | 规划；当前只有模块说明 |
| 统一几何与笔画 | [geometry](../src/agile_nero/geometry/README.md) | 规划；已有 DrawingTask 契约在 contracts |
| 平面路径规划 | [planning](../src/agile_nero/planning/README.md) | 基础已实现 |
| 机器人运动规划 | [planning/motion](../src/agile_nero/planning/motion/README.md) | 规划；当前只有模块说明 |
| 离线预演与仿真适配 | [simulation](../src/agile_nero/simulation/README.md) | 几何预演与接口已有；MuJoCo 待接入 |
| 机械臂 SDK 与执行边界 | [robot](../src/agile_nero/robot/README.md) | 执行占位固定拒绝；诊断代码已有 |
| 设备诊断 | [robot/diagnostics](../src/agile_nero/robot/diagnostics/README.md) | 已有状态解码、CAN 传输和诊断 CLI |
| 任务流程与编排 | [workflow](../src/agile_nero/workflow/README.md) | 固定离线流程已有；Agent 工作流待接入 |
| 产物导出与存储 | [artifacts](../src/agile_nero/artifacts/README.md) | SVG 导出已有；任务存储待扩展 |
| 外部入口 | [api](../src/agile_nero/api/README.md) | 离线 CLI 已有；上传/任务 HTTP API 待建 |
| 标定与坐标变换 | [calibration](../src/agile_nero/calibration/README.md) | 设计中 |
| 共享 NERO 模型 | [assets/robots/nero](../assets/robots/nero/README.md) | 设计中；模型尚未导入 |
| 固件与能力描述 | [robot/profiles](../src/agile_nero/robot/profiles/README.md) | 设计中 |
| 执行程序与后端 | [robot/backends](../src/agile_nero/robot/backends/README.md) | 三条候选路线，均未适配 |
| 结果评价 | [evaluation](../src/agile_nero/evaluation/README.md) | 设计中 |

## 依赖方向

contracts 定义共享数据，业务模块依赖它。planning 负责路径计算与检查；simulation 和 artifacts 使用路径；workflow 组合步骤；api 接收输入并调用工作流。

设备依赖集中于 robot/diagnostics。离线入口在禁止加载 SDK、CAN、USB、MuJoCo 和 Agent 框架的测试中运行。仿真与设备适配通过各自的 ports.py 扩展。

模型和解析器输出候选几何，由 geometry 统一为 DrawingTask。未来 planning/motion 生成保留笔尖意图的 MotionPlan；robot/backends 按 RobotProfile 编译成 ExecutionPlan。calibration 与 assets/robots/nero 为规划、仿真和转换提供同一份依据。

## 给下一次任务的上下文模板

```text
本次模块：cad + geometry。
先读：
  src/agile_nero/cad/README.md
  src/agile_nero/geometry/README.md
  src/agile_nero/contracts/README.md
  src/agile_nero/contracts/drawing.py
目标：二维 DXF 转成 DrawingTask，接入现有离线工作流。
验收：单位和曲线转换正确；不支持的实体明确报错；
      示例文件生成可检查的 SVG；相关测试通过。
执行范围：离线文件处理。
```

后续任务记入模块 README 的“下一步”；跨模块顺序写入 [路线图](roadmap.md)。代码变动时同步本模块说明和测试，让重要决定可以从仓库中找到。

机器人线任务使用另一组上下文：planning/motion/README.md、calibration/README.md、robot/profiles/README.md、robot/backends/README.md，以及双线契约中的 R1–R3。首个交付只编译和验证共用样例，执行范围为离线。

## 分支与迁移

2026-10-13：PR #1、#2 已合并，主目录已更新到模块化结构，原未提交诊断代码迁入 robot/diagnostics，测试迁入 tests/robot。迁移在 codex/migrate-hardware-diagnostics 分支单独提交，具体证据见 [迁移记录](diagnostics-migration-2026-10-13.md)。

- 日常开发目录：/Users/jiachenboo/Research/AGILE-Nero。以当前 git status 显示的分支为准。
- 架构工作树保留历史生成证据；继续开发可直接使用日常主目录中的对应模块。
- 原始未提交文件与 Git stash 在本机保留；configs/local 和 .venv 未重建。新改动继续通过独立分支与 PR 交付。

| 原位置 | 当前实现位置 |
| --- | --- |
| drawing/models.py | contracts/drawing.py |
| drawing/planning.py | planning/planar.py |
| drawing/validation.py | planning/validation.py |
| drawing/preview.py | simulation/offline.py、planning/metrics.py、artifacts/svg.py |
| drawing/ports.py | simulation/ports.py、robot/ports.py |
| drawing/workflow.py | workflow/offline.py |
| drawing/cli.py | api/cli.py |
| cli.py、state.py、transport.py | robot/diagnostics 下同名文件 |
| commission.py | robot/diagnostics/commission.py |
| tests/test_drawing.py 中的测试 | tests/offline 下按模块分组 |
| tests/test_state.py、test_transport.py | tests/robot 下同名文件 |
| tests/test_commission.py | tests/robot/test_commission.py |

旧 Python 导入（含 agile_nero.commission）和 python -m agile_nero.drawing 保留兼容。tests/test_drawing.py 只转发旧 unittest 发现命令，CI 继续通过该入口运行完整离线测试。兼容文件只做转发，新功能写到当前实现位置。
