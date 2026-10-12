# 2026-10-12 部署验收记录

## 软件环境：通过

平台为 Apple Silicon Mac，macOS 27.0.1，项目解释器 Python 3.12.13。独立环境位于项目 `.venv`，完整依赖版本记录在 `uv.lock`。

环境验收 JSON：`outputs/deployment/environment.json`（本机保存，Git 忽略）。以下七项实际执行通过：

1. OpenCV 线条生成与 scikit-image 骨架计算。
2. SVG 路径解析与长度计算。
3. SciPy 曲线插值。
4. MuJoCo 最小场景物理步进。
5. MuJoCo 离屏渲染。
6. PyTorch MPS 矩阵运算。
7. LangGraph 状态图执行。

主要版本：MuJoCo 3.15.0、PyTorch 2.14.1、torchvision 0.29.1、LangGraph 1.2.14、python-can 4.6.1、gs-usb 0.3.1。官方 pyAgxArm 固定源码提交 `841a625f5f4920e776f20b934eb13048b747e6d0`。

## 实机通信：部分观察，验收待完成

用户确认设备为 AgileX NERO，通过 USB-CAN 直连 Mac。USB 枚举识别到 candleLight `1D50:606F`。PyUSB 原生接口申请成功，并成功设置适配器 1 Mbps 的 CAN 时序。

首次 3 秒接收观察获得 `0x2A5 / 0x2A6 / 0x2A7 / 0x2A9` 各 20 帧，`0x2A1` 27 帧，另有各关节驱动及法兰位姿反馈。该次测试未发送 CAN 查询或运动帧。

后续重新打开接口采集 5 秒，没有新反馈；一次固件信息查询也没有响应。因此，当前证据支持“适配器可访问、收到过一批 NERO 反馈”，持续通信、实际固件版本和七轴状态解码尚待实机验收。首次数据可能包含缓冲帧，不能据此认定持续连接稳定。

诊断结果保存在：

- `outputs/deployment/can-listen.json`
- `outputs/deployment/robot-state.json`

接下来需要操作者确认机械臂当前供电、绿色指示灯，以及可取得的上位机固件版本；据此核对 CAN 推送与接线，再重跑状态工具。未调用运动、使能、模式切换或参数写入接口。

## 后续阶段

软件环境具备开始图像、几何、仿真与模型开发的基础。实机端先完成持续状态读取，再开展低速动作、TCP / 画板标定、NERO 仿真模型和离纸轨迹验证。
