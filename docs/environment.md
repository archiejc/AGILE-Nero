# Mac Studio 环境部署

设备诊断源码位于 [robot/diagnostics](../src/agile_nero/robot/diagnostics/README.md)，离线绘画入口位于 [api](../src/agile_nero/api/README.md)。快速定位其他模块见 [模块导航](modules.md)。

本项目使用 Python 3.12 的独立 `.venv`，由 `uv.lock` 锁定依赖。Mac 负责图像处理、笔画几何、仿真、模型实验与工作流；当前设备工具用于接收 CAN 数据和读取固件。

## 安装与日常使用

系统前置条件：Apple Silicon macOS、`uv`、Homebrew `libusb`。本机已有 `libusb 1.0.29`；如在另一台 Mac 部署，先执行 `brew install uv libusb`。

```sh
cd /Users/jiachenboo/Research/AGILE-Nero
./setup.command
source .venv/bin/activate
nero doctor
nero devices
nero listen --seconds 5
nero read-state --seconds 5
```

`setup.command` 安装核心、workflow、ml 依赖并执行环境检查。`check-environment.command` 执行软件检查并枚举 USB 适配器。`read-status.command` 按 `configs/local/robot.toml` 读取实机状态。机器配置和检查输出均由 Git 忽略。

如果固件查询没有响应，而网页上位机已给出实际版本，可显式提供版本，例如 `nero read-state --firmware 1.20`。这个参数来自操作者记录，输出会标明 `firmware_source=user-supplied`，与设备查询结果分开记录。不要猜测实际版本。

使用 `uv run` 时需保留 extras：

```sh
uv run --locked --extra workflow --extra ml nero doctor
```

直接运行 `.venv/bin/nero` 不会重新同步依赖。

## 已安装的软件层

| 层 | 依赖 | 本次检查 |
| --- | --- | --- |
| 设备 | 官方 pyAgxArm、python-can、gs-usb、PyUSB、pyserial | SDK 导入；USB 适配器枚举与接口申请 |
| 图像 | OpenCV headless、scikit-image、NumPy | 生成线条并计算骨架 |
| 几何 | SciPy、svgpathtools、Matplotlib | SVG 路径长度、样条插值 |
| 仿真 | MuJoCo | 最小物理场景步进与离屏渲染 |
| 模型 | PyTorch、torchvision | MPS 张量矩阵乘法 |
| 工作流 | LangGraph、Pydantic | 状态图编译与执行 |
| 开发 | pytest、Ruff | 传输限制与设备选择测试、代码检查 |

MuJoCo 的基础测试使用小球场景。NERO 本体模型、笔夹、画板、TCP、逆运动学和绘画轨迹仍属于后续实现。模型实验依赖已安装，领域模型及其权重需在选型后部署。

## candleLight 接入

本机识别到 USB `1D50:606F` 的 candleLight 适配器。它通过 USB bulk 接口收发 CAN，不产生 `/dev/cu.usb*` 串口，也不使用 macOS 的 `can0`。

`gs-usb==0.3.1` 的 `start()` 会执行 USB reset 和内核驱动分离。本次在 macOS 上遭遇 `Access denied`，并且该失败路径退出异常。项目的 `nero_gs_usb` 后端采用 PyUSB 原生接口申请，保留相同的 CAN 时序和 USB 帧格式；不修改第三方包，不改驱动或刷写适配器。

这个后端注册为 python-can 的 `can.interface` 插件。它接收状态帧，并只放行 `0x4AF`、单字节 `01` 的固件信息查询。所有运动、使能、模式切换和参数写入帧均被代码拒绝。适配器启动时会改变 USB 采集模式，正常 CAN 模式下硬件会应答 ACK，因此不是电气意义上的静默监听器。

实机命令默认采集 5 秒，最长 60 秒，每次结束释放 USB 资源，并保留适配器 CAN 激活状态及硬件 ACK。测试曾观察到接口关闭重开后反馈停止；保留 ACK 可减少接口生命周期对诊断的干扰，目前尚未证明它是中断的唯一原因。程序重开时清理两个 USB bulk endpoint 的 halt 状态，不执行 CAN stop。

`passed=false` 和非零退出码表示对应验收未通过。七轴角度需要收到全部四组反馈帧，且每组最近到达时间不超过 1 秒，才会输出；法兰位姿也要求完整且新鲜的三组反馈。未收到驱动使能反馈时输出 `null`，与明确的禁用状态 `false` 区分。

固件查询和状态接收共用一次 USB 会话。SDK 仅作为已锁定的协议解码器，不再次打开接口；SDK 内部的数据分发入口由七轴解码回归测试覆盖。

## 固件配置

官方 SDK 固定到提交 `841a625f5f4920e776f20b934eb13048b747e6d0`。SDK 包版本号为 1.0.0，提交号用于区分同版本号的源码变化。

| 实际 NERO 固件 | SDK profile |
| --- | --- |
| ≤ 1.10 | default |
| 1.11 | v111 |
| 1.12 | v112 |
| 1.20 | v120 |
| ≥ 1.21 | v121 |

`read-state` 使用固件查询结果选择 profile。设备没有响应时，默认不把未知固件当作某个已知版本。旧固件的 CAN 推送设置需要通过实际版本与上位机核对。

本机已通过 CAN 查询确认实际固件 **1.11**，应使用 `v111`。这是机械臂固件；USB-CAN 适配器描述符中的 `fw_7d59b2f` 是适配器固件，二者分别记录。

官方 NERO API 文档说明：1.11 的 `set_normal_mode()` 在电机使能后开启 CAN 推送；禁用状态下控制与配置指令不会生效。环境部署不执行 `enable()` 或模式切换。开启电机与持续 CAN 推送属于下一次真机配置操作，需操作者明确授权后安排。当前已收到固件回复和启动阶段反馈，持续读取仍未通过验收。

## 诊断与复现

```sh
.venv/bin/nero doctor --output outputs/deployment/environment.json
.venv/bin/nero listen --config configs/local/robot.toml --output outputs/deployment/can-listen.json
.venv/bin/nero read-state --config configs/local/robot.toml --output outputs/deployment/robot-state.json
.venv/bin/pytest -q
.venv/bin/ruff check src tests
```

状态读取异常时，先确认机械臂电源与指示灯，再核对 CAN H/L、实际固件、推送设置和 1 Mbps 波特率。USB 能枚举只证明适配器可见。状态读取通过后再开展低速动作、TCP / 画板标定和离纸轨迹验证。

macOS 上的 MuJoCo passive viewer 用 `.venv/bin/mjpython` 启动；当前 `doctor` 使用离屏 Renderer，无需窗口。

## 依据

- [AgileX 官方 SDK](https://github.com/agilexrobotics/pyAgxArm)
- [NERO 首次 CAN 使用指南](https://github.com/agilexrobotics/pyAgxArm/blob/841a625f5f4920e776f20b934eb13048b747e6d0/docs/nero/first_time_user_guide_can.md)
- [python-can candleLight 接口](https://python-can.readthedocs.io/en/stable/interfaces/gs_usb.html)
- [gs-usb 源码](https://github.com/jxltom/gs_usb)
- [MuJoCo Python 文档](https://mujoco.readthedocs.io/en/stable/python.html)
- [LangGraph 安装说明](https://docs.langchain.com/oss/python/langgraph/install)
