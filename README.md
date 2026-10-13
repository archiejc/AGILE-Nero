# AGILE-Nero

目标：上传图片或 CAD 文件，识别与整理线稿，生成绘画路径，经仿真验证后交给 NERO 机械臂绘制。

当前已实现手工二维笔画 → 平面路径 → 几何检查 → JSON / SVG 离线预览。图片识别、CAD 解析、机器人轨迹和 NERO 仿真仍在规划中；设备绘画执行入口固定拒绝执行。

## 从这里开始

1. 看 [模块导航](docs/modules.md)，找到本次工作的目录。
2. 看 [双线契约](docs/architecture/track-contracts.md)和[路线图](docs/roadmap.md)，从内容线或机器人线选择一个可离线验收的任务。
3. 进入该模块的 README，读取状态、输入输出、代码、测试和下一步。

[后端架构与交互图](docs/architecture/README.md) · [离线运行](docs/offline-drawing.md) · [完整环境](docs/environment.md) · [研究背景](docs/project-background.md)

## 文件夹就是模块

```text
src/agile_nero/
├── contracts/       共享数据契约：DrawingTask、Toolpath
├── ingestion/       文件接入与格式检查                 [规划]
├── vision/          图片识别与线条提取                 [规划]
├── cad/             CAD 图层与曲线解析                [规划]
├── geometry/        单位、坐标与统一笔画               [规划]
├── planning/        平面路径、几何检查与长度统计
│   └── motion/      笔尖运动意图、IK 与进给约束         [规划]
├── calibration/     TCP / 画板坐标变换与标定版本       [规划]
├── simulation/      离线预演与仿真接口；MuJoCo 待接入
├── robot/           禁用的执行占位
│   ├── diagnostics/ 设备状态、CAN 传输与诊断工具
│   ├── profiles/    型号、固件与能力                   [规划]
│   └── backends/    controller_file / pyagxarm / ros2   [规划]
├── evaluation/      反馈、笔尖误差与线稿评价           [规划]
├── workflow/        固定离线流程；Agent 工作流待接入
├── artifacts/       SVG 产物；任务与结果存储待扩展
├── api/             离线 CLI；上传与任务 HTTP API 待接入
└── drawing/         旧导入与旧命令的兼容入口

tests/offline/       无第三方依赖的测试，内部按模块分组
tests/robot/         SDK 解码与模拟传输测试，不连接设备
assets/robots/nero/  共享模型、工具与场景 manifest       [规划]
examples/           小型可复现输入与双线共用验收样例
configs/            示例配置；本机配置放 configs/local/
docs/               导航、路线图、架构和设备记录
outputs/            运行产物，Git 忽略
```

每个业务模块都有中文 README。[规划] 目录目前只有职责说明，目录存在并不代表功能已经实现。包根的 cli.py、state.py、transport.py 也只保留旧路径兼容，新代码写入对应模块。

## 独立运行

在当前检出的仓库根目录使用 Python 3.12：

```sh
PYTHONPATH=src python3.12 -S -m agile_nero.api --input examples/drawing/two-strokes.json --output-dir outputs/offline-demo
PYTHONPATH=src python3.12 -S -m unittest discover -s tests/offline -t . -v
```

--output-dir 必须是新目录，省略时只向终端输出 JSON。以上命令仅使用标准库；安装完整项目后可运行 nero-dry-run。

## 下一步

内容线推进二维向量输入 → DrawingTask → 几何预览；机器人线从同一[两直线一圆弧样例](examples/acceptance/README.md)开始，建立模型/标定/能力，再离线准备并验证一个后端的程序。具体输入输出和 C1–H1 验收条件见 [双线契约](docs/architecture/track-contracts.md)。

开始下一次任务时，先确认 git status --short --branch。PR #1 已合并；本轮架构更新另用 codex/two-track-backend-architecture 分支。主目录的未提交硬件调试内容在同步前仍需独立核对，见 [迁移说明](docs/modules.md#分支与迁移)。

项目尚未选定许可证，第三方依赖和输入资料按各自许可使用。
