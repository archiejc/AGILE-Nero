"""Decode feedback through the pinned SDK without opening another USB session."""

import time

from pyAgxArm import AgxArmFactory, ArmModel, create_agx_arm_config

JOINT_IDS = (0x2A5, 0x2A6, 0x2A7, 0x2A9)
POSE_IDS = (0x2A2, 0x2A3, 0x2A4)


def decode_firmware(message):
    """Use the exact NERO firmware-reply layout from the pinned SDK codec."""
    if (
        message is None
        or not message.is_rx
        or message.is_extended_id
        or message.is_remote_frame
        or message.is_error_frame
        or message.arbitration_id != 0x4AF
        or message.dlc != 8
        or len(message.data) != 8
        or bytes(message.data) == b"\x01" + b"\x00" * 7
        or message.data[6] == 0
    ):
        return None
    return {"software_version": f"{message.data[6]}.{message.data[7]:02d}"}


class StateDecoder:
    def __init__(self, profile):
        self.robot = AgxArmFactory.create_arm(
            create_agx_arm_config(
                robot=ArmModel.NERO,
                firmeware_version=profile,
                auto_connect=False,
                enable_check_can=False,
                log_level="ERROR",
            )
        )
        self.context = self.robot.get_context()
        self.last_seen = {}
        self.context.fps.start()

    def feed(self, message, received_at=None):
        if (
            not message.is_rx
            or message.is_extended_id
            or message.is_error_frame
            or message.is_remote_frame
            or message.dlc != 8
            or len(message.data) != 8
        ):
            return
        # DriverContext's dispatch is internal to pyAgxArm, hence its exact
        # commit is pinned and seven-axis decoding is covered by regression tests.
        self.context._run_parser_packet_funs(message)
        self.last_seen[message.arbitration_id] = (
            time.monotonic() if received_at is None else received_at
        )

    def snapshot(self, now=None, max_age=1.0):
        now = time.monotonic() if now is None else now

        def fresh(ids):
            return all(x in self.last_seen and now - self.last_seen[x] <= max_age for x in ids)

        joints = self.robot.get_joint_angles() if fresh(JOINT_IDS) else None
        pose = self.robot.get_flange_pose() if fresh(POSE_IDS) else None
        return {
            "joint_angles_rad": joints,
            "flange_pose_m_rad": pose,
            "arm_status": self.robot.get_arm_status() if fresh((0x2A1,)) else None,
            "joint_motors_enabled": [
                self.robot.get_joint_enable_status(i) if fresh((0x260 + i,)) else None
                for i in range(1, 8)
            ],
            "joint_feedback_fresh": joints is not None,
            "max_feedback_age_s": max_age,
        }

    def close(self):
        self.robot.disconnect()
