# 内容线与机器人线：边界、契约和验收

这是目标设计与验收约定。现有实现只覆盖 DrawingTask / Toolpath、平面几何检查、固定离线预演和 JSON / SVG 导出。以下 MotionPlan、ExecutionPlan、CalibrationBundle、RobotProfile 和 ExecutionPermit 均为待实现契约；本轮不改变运行时接口，不连接设备或执行运动。

## 内容线

**职责：确定画什么，并交付与执行后端无关的绘画几何。**

| 阶段 | 输入 | 输出 | 所属模块与边界 |
| --- | --- | --- | --- |
| 文件接入 | 图片、CAD / SVG、目标尺寸、选定区域 | 原文件引用、格式与来源记录 | ingestion / api；图片与 CAD 接入、上传 API 待实现，现有 CLI 接收任务 JSON |
| 识别与解析 | 原文件、格式配置 | CandidateGeometry（拟定）：候选线条、图层、原始单位、来源及可用置信度 | vision 做图片识别，cad 解析原生几何；均待实现 |
| 统一与确认 | 候选几何、尺度、选线与人工修正 | DrawingTask：有序笔画、毫米单位、绘画平面、工作区和采样配置 | geometry / contracts；数据类型已有，转换和交互确认待实现 |
| 平面规划 | DrawingTask | Toolpath：平面三维点、start / travel / lower / draw / lift | planning；已有采样、抬落笔、边界和动作顺序检查，排序和平滑待扩展 |
| 内容验收 | 原始参考几何、DrawingTask、Toolpath | 几何报告、SVG、输入与结果指纹 | 现有 workflow / simulation/offline 校验，api/cli 写 JSON，artifacts/svg 渲染 SVG |

内容线保留几何和用户意图；机械臂关节、固件控制模式、控制器程序格式由机器人线处理。当前 Toolpath 的 start 只是离线起点，尚无从实机当前位置接近该点的轨迹。

## 机器人线

**职责：把确认的绘画几何转换为特定设备可解释、可验证的运动程序。**

| 阶段 | 输入 | 输出 | 所属模块与边界 |
| --- | --- | --- | --- |
| 共享模型与配置 | 厂商模型、工具与画板描述、标定测量、型号与固件记录 | RobotModelManifest / CalibrationBundle / RobotProfile（拟定） | assets/robots/nero、calibration、robot/profiles；统一供规划、验证和后端转换使用 |
| 运动规划 | Toolpath、共享配置、起始状态、进给与约束 | MotionPlan（拟定）：基座坐标下的笔尖位姿、绘制/空行程段、姿态、速度/加速度约束、接近与撤离 | planning/motion；待实现，负责路径意图和必要的运动学求解 |
| 后端编译 | MotionPlan、RobotProfile、目标后端 | ExecutionPlan（拟定）：不可变后端程序与元数据 | robot/backends；纯准备步骤，不连接或驱动机械臂 |
| 仿真与能力校验 | 具体 ExecutionPlan、模型、标定、场景及初始状态 | BackendValidationReport（拟定）：验证范围、结论、误差和证据 | simulation + 后端校验器；几何通过不等同于执行通过 |
| 执行授权 | 同一版本的程序与报告、适配验收结果、操作者确认 | ExecutionPermit（拟定） | workflow 管理；程序/模型/标定/能力/场景/初始状态条件变化使旧报告和授权失效 |
| 设备执行 | 已授权 ExecutionPlan、有效起始状态 | 执行事件、反馈、停止与故障结果 | robot/backends；仅在适配完成且人工明确授权后接入。现有 UnadaptedRobotBackend 始终拒绝 |
| 结果评价 | 执行记录、期望笔尖路径、测量/配准结果 | EvaluationReport（拟定） | evaluation；区分命令接受、运动完成与线稿质量，误差分析进入下一轮人工复核 |

MotionPlan 保留笔尖运动意图。ExecutionPlan 可是笛卡尔运动段、控制器原生文件，或显式带时间的关节轨迹；关节轨迹是其中一种表示，不能预设所有后端都以同一种方式接收和插值。

## 共用契约

| 契约 | 必须明确的信息 | 状态 |
| --- | --- | --- |
| DrawingTask / Toolpath | schema、task_id、单位 mm、drawing_plane、笔画/动作及配置；Toolpath 绑定源任务指纹 | 已实现；已有 JSON schema 不变 |
| CalibrationBundle | 画板到基座、法兰到笔尖的变换，测量方法与残差、版本/指纹、工具安装条件 | 设计中 |
| RobotModelManifest | 来源与固定提交、文件校验和、许可、关节顺序/限位、URDF/MJCF 对应、工具/画板/碰撞几何版本 | 设计中 |
| RobotProfile | 型号、实际固件及获取来源、SDK/后端版本、控制模式和能力；未知能力默认不支持 | 设计中 |
| MotionPlan | Toolpath 指纹、模型/标定/能力版本、坐标系、位置 m、姿态表示与约定、关节量 rad（若有）、时间 s（若有）、笔状态/进给约束 | 设计中 |
| ExecutionPlan | 后端 ID、来源 MotionPlan、精确程序及指纹、载荷单位/坐标系、单次执行语义、初始状态条件和能力要求 | 设计中 |
| BackendValidationReport | ExecutionPlan 指纹、模型/标定/能力/场景版本、initial-state 条件、scope、passed/failed/unsupported、阈值及证据 | 设计中 |
| ExecutionPermit | 绑定上述指纹、操作者确认及适用条件；不是仅凭 passed=true 就放行 | 设计中 |

所有跨单位和坐标系转换显式记录。MotionPlan 的姿态可在实现时选择四元数或 RPY，但必须固定约定和测试转换；不得把裸数组的含义交给接收方猜测。SDK 的法兰目标转换由后端按同一 CalibrationBundle 完成，避免重复应用 TCP 偏移。

## 三个候选后端

| 后端 | 准备产物 | 首个离线验收目标 | 尚需确认 |
| --- | --- | --- | --- |
| controller_file | 可导入的原生轨迹文件及 manifest | 读取真实导出样例，明确 schema / 单位 / 点段类型 / 单次执行语义，建立解析与回写检查 | 导入执行、暂停停止、段间插值和循环行为；暂时只有其他聊天中的手册观察，不能宣称已适配 |
| pyagxarm | 具有明确完成条件的 SDK 运动段/命令计划 | 能力筛选、TCP 转换、顺序/超时/停止逻辑的模拟测试；不把密集采样点直接循环发送给 move_l | 实际段间停顿、目标覆盖、轨迹跟踪、持续反馈与重连 |
| ros2 | 适配实际驱动的带时间关节轨迹与 Action 请求描述 | 核对关节顺序/单位/时间，模拟反馈与取消，检查对应模型中的轨迹 | Ubuntu/ROS2 部署、驱动与固件能力、真实跟踪效果 |

三条路线共享运动意图、版本和报告契约，不承诺等价的插值或控制表现。第一阶段只选择并验收一条执行路线，其余保留适配边界。

## 仿真证据怎样用于放行

1. 内容几何检查覆盖边界、采样和抬落笔，适用于当前离线预览。
2. 显式关节轨迹可在共享机器人/工具/画板模型中检查运动学、限位和碰撞；接触结论需要匹配经过校准的接触参数。
3. 若原生控制器文件或 SDK 命令的插值/逆解语义尚未验证，MuJoCo 中的名义路径预演只标记 nominal_preview。不能把它当作控制器实际执行的复现。
4. 后端选择、配置或程序变化后重新编译并验证。验证失败、能力未知、适配未验收或缺少人工确认时不进入执行。

## 共同验收样例

首个基准为“两条直线 + 一段圆弧 + 笔画间抬笔”，见 [样例定义](../../examples/acceptance/README.md)。内容线能在完全没有机器人环境时验收；机器人线能直接使用这个已知样例，独立于图片识别开发。

| 关口 | 交付物 | 通过条件 |
| --- | --- | --- |
| C1 内容转换 | 原始几何、单位映射、DrawingTask、SVG | 支持范围明确；缺少单位需显式给定；没有静默丢线；曲线偏差满足预先设定的离线阈值 |
| C2 平面规划 | Toolpath、几何报告 | 工作区内、抬落笔顺序正确、无零长度绘制段、采样受限、指纹可重复；输入变更使指纹变化 |
| R1 模型与标定 | 模型 manifest、CalibrationBundle、能力清单 | 坐标转换往返及已知姿态一致，单位/关节顺序明确；合成标定标为 synthetic，不当作实机标定 |
| R2 程序准备 | MotionPlan、一个后端的 ExecutionPlan | 编译无设备副作用；不支持能力明确失败；包含接近/绘制/撤离及初始状态条件；载荷语义明确 |
| R3 后端验证 | 绑定程序与全部配置的验证报告 | 预先选定的检查全部通过，未知语义明确标记 unsupported；仅 nominal_preview 不自动放行 |
| J1 离线汇合 | 同一源样例到程序与报告的完整证据链 | 所有版本一致，仿真/模拟故障用例覆盖；当前阶段在此结束，物理执行保持不可用 |
| H1 后续实机验收 | 人工授权、执行反馈、测量线稿 | 先确定纸张/笔具/速度条件，以及笔尖偏差、停顿、抬笔间隙、停止响应的数值阈值；未确定阈值不宣布验收通过 |

H1 是后续单独授权任务。本轮只建立设计与离线证据，不填写假想的硬件达标数据。

## 公共流程与产物

workflow 组织内容和机器人准备工具、汇总状态与受控重试；api 提供外部入口。当前固定流程止于几何预演，当前 JSON 文件由 api/cli 写入。未来 artifacts 承担文件与任务版本存储，workflow 通过存储接口持久化事件；这些持久化和跨阶段调度仍属目标设计。

未来状态需区分 content_review、planned、compiled、validated、awaiting_approval、executing、completed、failed 和 cancelled。可重复的纯计算可以重试；部分物理执行后只记录进度并进入显式恢复流程，不能自动重放。

## 已核对的接口依据

- [固定版本 SDK 文档](https://github.com/agilexrobotics/pyAgxArm/blob/841a625f5f4920e776f20b934eb13048b747e6d0/docs/nero/nero_api.md)：TCP 偏移保存在 SDK 实例；move_l 每个新目标重规划，不能用于连续发送密集目标点；get_ik_joint_angles 是运动后的逆解反馈。
- [同版本固件矩阵](https://github.com/agilexrobotics/pyAgxArm/blob/841a625f5f4920e776f20b934eb13048b747e6d0/docs/nero/firmware_reference.md)：按项目记录的 1.11 基线设计时，不依赖 CPV 和 get_ik_joint_angles；能力以实际型号/固件核验记录为准。
- [官方模型](https://github.com/agilexrobotics/agx_arm_urdf)：提供 NERO URDF / mesh 起点；本轮尚未导入或验收模型。
- [官方 ROS2 / MoveIt2 接口](https://github.com/agilexrobotics/agx_arm_ros/blob/ros2/src/agx_arm_moveit/README.md)：提供 FollowJointTrajectory 路线；仓库提供接口不等于本项目的硬件验收完成。
