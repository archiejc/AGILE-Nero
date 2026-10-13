# 2026-10-12 CAN 重连诊断与修复

## 故障复现

18:04 的首次状态读取在 10 秒内接收 19,987 帧，七轴反馈新鲜，七个电机报告已使能，CAN 错误帧为 0。关闭接口并重连后，固件查询无响应；后续仅读窗口也没有数据。日志保存在本机 `outputs/deployment/can-check-2026-10-12-1804-*.json`。

## 原因分析与修改

原传输层每次申请 USB 接口后，无条件对 `0x81`（IN）和 `0x02`（OUT）调用 `clear_halt()`，即使端点没有报告 stall。

candleLight `7d59b2f` 源码的 `USBD_GS_CAN_Transmit()` 将 `TxState` 设为 1；只有 USB IN 完成回调 `USBD_GS_CAN_DataIn()` 将它清零。固件主循环在 `TxState` 为 0 时才继续发送排队帧。因此，打断待完成 IN 包却未触发完成回调，可以导致 USB 数据流卡住。macOS 的 libusb `clear_halt()` 调用 `ClearPipeStallBothEnds()`，不是仅检查端点状态。

这是当前最符合现象的故障机制；尚未直接读取适配器 MCU 内的 `TxState`。修复移除每次重连时无条件清理端点的操作，保留接口申请、1 Mbps 时序配置和正常 CAN ACK。不刷写适配器固件，不修改机械臂参数。

恢复诊断中，USB reset 与重新设置 configuration 均未恢复数据；静默内部回环的固件查询 USB 写入完成，但收到 0 帧，恢复普通模式的 USB 控制请求超时。此时需要插拔 USB-CAN 适配器重新上电；在重新上电前不能假定适配器已恢复普通模式。

## 验证状态

21 项软件测试与 Ruff 检查通过。回归测试禁止初始化时调用 USB `clear_halt()` 或 USB reset，并验证关闭时释放资源、不发送 CAN stop。默认诊断后端继续只放行 `0x4AF / 01` 固件查询，运动及配置帧均被拒绝。

### 2026-10-13 实机复测：6 次均通过

用户确认已重新插拔 USB-CAN。10:57:04 至 10:57:35，运行六个独立进程，每次打开接口、读取 5 秒并关闭，交替执行设备固件查询与使用刚查询确认的固件版本仅读。

| 连接次数 | 固件来源 | 接收帧数 | 七轴反馈新鲜 | CAN 错误帧 |
| --- | --- | ---: | --- | ---: |
| 1 | 设备查询 1.11 | 10,991 | 是 | 0 |
| 2 | 使用已确认版本 | 10,581 | 是 | 0 |
| 3 | 设备查询 1.11 | 10,557 | 是 | 0 |
| 4 | 使用已确认版本 | 10,517 | 是 | 0 |
| 5 | 设备查询 1.11 | 10,533 | 是 | 0 |
| 6 | 使用已确认版本 | 10,705 | 是 | 0 |

合计收到 63,884 帧，三次固件查询均回复 1.11，SDK profile 为 `v111`。各窗口末尾七轴反馈均在最近 1 秒内更新，最终七个电机均报告已使能。实机复测发送 3 条固件查询，运动帧、使能帧和机器人模式配置帧均为 0。

最终控制模式码为 3（SDK 映射为以太网控制），机械臂状态码为 3（SDK 映射为奇异点），错误码为 0。当前通过的是 CAN 连接与反馈读取验收，不能据此将机械臂状态记为正常。测试未尝试改变控制模式或机械臂姿态。

移除无条件端点清理并重新上电后，原有重连故障在本次六轮测试中未再出现，支持上述 USB 端点生命周期诊断。该结论覆盖本次重连与状态读取；长时间通信与运动执行仍需各自验证。

汇总日志：`outputs/deployment/can-reconnect-repair-2026-10-13.json`；逐次日志：`outputs/deployment/reconnect-fixed-2026-10-13-cycle-1.json` 至 `cycle-6.json`。

### 2026-10-13 下午移动测试前：再次失联

用户授权移动测试后，17:43 的预检固件查询无响应；17:44 使用已确认的 1.11 固件仅读 5 秒也收到 0 帧，七轴、位姿和电机状态均未知。网络状态页 `http://192.168.31.1/` 也在 3 秒内未响应。未发送运动、使能或机器人模式配置帧。

上午六轮短间隔重连通过，下午首次预检再次失联，说明现有修改尚未覆盖持续使用与长间隔后的连接问题；不能将上午结果推广为连接稳定性已完全修复。本次无法从现有证据区分适配器、机械臂供电/推送或网络变化。等待用户重新插拔 USB-CAN、确认现场条件后，先恢复实时反馈，再准备单次低速 J7 相对转动 2° 测试。

预检日志：`outputs/deployment/pre-motion-2026-10-13.json` 与 `outputs/deployment/pre-motion-2026-10-13-followup.json`；待执行计划：`outputs/deployment/motion-test-plan-2026-10-13.json`。

## 源码依据

- [candleLight USB 数据流与 TxState，适配器版本 7d59b2f](https://github.com/candle-usb/candleLight_fw/blob/7d59b2f/src/usbd_gs_can.c)
- [candleLight 主循环与帧队列](https://github.com/candle-usb/candleLight_fw/blob/7d59b2f/src/main.c)
- [libusb 1.0.29 的 macOS clear_halt 实现](https://github.com/libusb/libusb/blob/v1.0.29/libusb/os/darwin_usb.c)
