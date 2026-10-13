# AGILE-Nero 开发上下文

## 先定位模块

1. 检查当前 Git 分支和工作树，保留已有未提交改动。
2. 从 docs/modules.md 找本次模块，只读取相关模块 README、数据契约、代码与测试。
3. 实现顺序和验收条件见 docs/roadmap.md；整体连接见 docs/architecture/README.md。

## 放置代码

- 共享笔画/路径数据放 src/agile_nero/contracts。
- 接入、图片、CAD、几何归一化分别放 ingestion、vision、cad、geometry。
- 平面路径放 planning，笔尖运动计划放 planning/motion；共享坐标变换与标定放 calibration。
- 固定机器人资产放 assets/robots/nero；能力放 robot/profiles；候选后端放 robot/backends；测量评价放 evaluation。
- 仿真/预演放 simulation；设备 SDK、传输和诊断放 robot。
- 流程放 workflow，外部入口放 api，导出/存储放 artifacts。
- drawing 和包根的 cli.py、state.py、transport.py、commission.py 是兼容入口，新逻辑写到职责目录。
- 标为规划中的目录尚无实现；新增能力时同步其 README 和验收测试。

双线的输入输出与 C1–H1 验收关口以 docs/architecture/track-contracts.md 为准；共用样例在 examples/acceptance/README.md。

## 边界

核心数据与几何计算保持独立；离线入口不依赖设备、仿真引擎或 Agent 框架的导入。
图片/CAD 先输出可检查的几何，再进入规划。MotionPlan 保留运动意图；ExecutionPlan 才绑定目标后端。编译是无设备副作用的准备，执行需有效的同版本验证、能力验收和明确授权。模型和编排器不直接调用电机运动接口。
当前绘画硬件适配器固定拒绝执行。安装 SDK、基础仿真通过或一次状态读取成功，不作为硬件绘画已适配的证据。
普通代码开发和测试使用离线数据或模拟对象；真实设备配置和运动按用户明确授权的独立任务处理。

## 验证与同步

```sh
PYTHONPATH=src python3.12 -S -m unittest discover -s tests/offline -t . -v
PYTHONPATH=src python -m pytest -q
ruff check src tests
```

离线测试按模块放 tests/offline；使用已安装 SDK 的模拟/解码测试放 tests/robot。
移动文件、修改契约或新增能力时，更新模块 README、模块导航及涉及的运行说明。
新增目录只含设计说明时，明确标记未实现；不得把 nominal_preview 当作实机执行验证。
通过独立分支和 PR 交付。主目录的历史诊断改动已按迁移表移入 robot/diagnostics；开始新任务仍需核对当前分支和未提交改动。
tests/robot/conftest.py 禁止真实设备 I/O。设备验收使用明确授权的独立任务，不能通过取消测试保护来执行。
