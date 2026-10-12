# 离线绘画最小实现

当前实现从显式二维笔画生成绘画平面中的三维路径，检查平面边界、绘制段采样间距及抬落笔顺序，并导出 JSON 和 SVG。核心代码仅使用 Python 3.12 标准库，测试可在关闭 site-packages 的解释器中运行。

报告中的 `previewed` 表示几何预演完成。输出固定记录 `physical_execution=unavailable` 和 `robot_adapter=unadapted`。NERO 本体仿真、基坐标标定、TCP、末端姿态、逆运动学、关节约束、碰撞、接触与时间参数化均由后续适配工作提供证据。

## 独立运行

在仓库根目录执行；`python3.12` 可替换为本机已有的 Python 3.12 解释器：

```sh
PYTHONPATH=src python3.12 -S -m agile_nero.api \
  --input examples/drawing/two-strokes.json \
  --output-dir outputs/offline-demo

PYTHONPATH=src python3.12 -S -m unittest discover -s tests/offline -t . -v
```

这些命令使用源码运行，直接验证独立模块。安装完整项目后，也可使用 `nero-dry-run --input ...`；现有项目安装仍包含开发环境依赖。离线命令及测试均不运行 `setup.command`、`nero doctor`、USB 枚举或设备诊断。

`--output-dir` 必须指向新目录；再次运行时换一个目录名，或省略该参数，仅在标准输出读取 JSON。拒绝任务返回非零退出码。新目录策略避免把上一次的预览当作本次结果。

| 文件 | 内容 |
| --- | --- |
| `toolpath.json` | 单位、坐标系、规划配置、源任务指纹及路径点 |
| `report.json` | 流程状态、几何检查、预演范围、路径指纹和长度统计 |
| `preview.svg` | 蓝色绘制线段；橙色虚线表示抬笔后的水平移动 |

示例包含两笔，共 51 个路径点。绘制长度约 88.284 mm，非绘制长度约 48.284 mm；后者包含抬落笔及笔画间移动，起点前的接近路径由后续适配阶段规划。

## 数据和模块边界

任务 schema 版本为 1，强制 `units=mm`、`frame=drawing_plane`。平面原点位于矩形左下角，x 向右、y 向上、z 为离开画面的方向；绘制面 z=0，抬笔面 z=`lift_mm`。该坐标系由任务定义，机器人基坐标变换将在标定后建立。

`examples/drawing/two-strokes.json` 给出完整输入。笔画顺序保持输入顺序，闭合笔画通过重复首点表达，相邻重复点被跳过。每个有效笔画至少含两个不同点，笔画 ID 唯一。

| 模块 | 职责 |
| --- | --- |
| `contracts/drawing.py` | 不可变任务、笔画、配置、路径数据及版本化 JSON |
| `planning/planar.py`、`planning/metrics.py` | 平面路径生成与长度统计 |
| `planning/validation.py` | 独立检查路径边界、绘制间距、笔画切换和动作顺序 |
| `simulation/ports.py`、`simulation/offline.py` | 预演接口及默认离线实现 |
| `robot/ports.py` | 机器人接口和固定拒绝执行的占位实现 |
| `artifacts/svg.py` | 可视化产物导出 |
| `workflow/offline.py` | 固定流程及框架中立的 JSON 工具入口 |
| `api/cli.py` | 文件读取、结构化报告及产物写入 |

规划序列为 `start → lower → draw... → lift`，下一笔通过 `travel → lower` 接续。`start` 定义离线预览的初始位置，真实环境需要独立的接近规划。`max_draw_segment_mm` 约束绘制段的空间间距；抬落笔与空行程保存目标端点，速度、加速度和控制周期由后续轨迹模块定义。

输入拒绝未知字段、非毫米单位、不支持的坐标系、布尔或非有限数值、越界点及退化笔画。CLI 读取上限为 1 MB，任务上限为 10,000 个输入点，生成路径遵守 `max_waypoints`（默认 10,000，上限 100,000），在分配大量采样点前检查预算。

路径 SHA-256 覆盖源任务指纹、配置与全部路径点。预演报告须引用同一路径指纹并返回 `passed=true`；失败、异常或指纹不匹配时，流程停止在 `rejected`。

## 后续接入

MuJoCo 适配器实现 `PreviewBackend.preview(path) -> PreviewReport`，通过 `run_task(task, preview_backend=adapter)` 注入。适配器负责提供实际模型、单位换算、坐标变换、轨迹求解及模型范围内的验证，并在报告中说明 backend 和 scope。现有默认适配器只检查绘画几何，MuJoCo 适配实现仍待开发。

机械臂 SDK 使用独立的 `RobotBackend` 边界。当前 `UnadaptedRobotBackend.execute()` 始终抛出异常，工作流和 CLI 均没有机器人后端选择或执行阶段。后续 SDK 实现需要在适配层建立标定与轨迹契约，再以独立变更接入硬件验收流程。

Codex SDK 或 LangGraph 可包装 `run_tool(payload) -> dict`，或调用独立 CLI 读取 JSON。该入口只接受绘画任务数据，返回规划、校验和预演结果；框架负责节点调度、持久化与重试。当前核心既不导入框架，也不自动加载环境变量指定的适配器。

```python
import json
from pathlib import Path

from agile_nero.workflow.offline import run_tool

payload = json.loads(Path("examples/drawing/two-strokes.json").read_text())
report = run_tool(payload)
assert report["status"] == "previewed"
assert report["physical_execution"] == "unavailable"
```

旧的 `python -m agile_nero.drawing` 和 `agile_nero.drawing.*` 导入仍通过兼容入口工作；新开发使用上述职责目录。

## 验证范围

标准库测试覆盖数据契约、闭合与重复点、已知几何长度、采样预算、路径篡改、SVG 结构、预演失败与过期报告、硬件占位拒绝，以及无 site-packages 的 CLI 运行。单独的导入拦截测试在新进程中禁止加载 USB/CAN、机械臂 SDK、MuJoCo、视觉和工作流框架模块。

GitHub Actions 的离线测试只准备 Python 3.12 并执行这套标准库测试。现有诊断模块的回归测试在项目开发环境中另行运行；硬件、标定及 NERO 仿真验收属于后续阶段。
