import random
import os
import threading
import time
import cv2
import numpy as np
import keyboard

from dataclasses import dataclass, asdict, field
from typing import Optional, List, Tuple, Any, Union, Dict

from toolbox import constants, custom_types as tp, utils
from toolbox.display import display
from toolbox.shared import shared
from toolbox.logger import logger


class SteeringProcessor:
    def __init__(self):
        self.call_time = 0

    def process(self):
        # return
        # diff with car yaw
        # speed_diff = shared.player.speed - shared.goal_speed
        # angle_diff = shared.player.yaw - np.degrees(shared.goal_angle)
        goal_angle = shared.goal_angle
        # logger.info(f"goal_speed: {goal_speed:.2f}, goal_angle {goal_angle:.2f}")

        angle_diff = shared.player.yaw - goal_angle
        angle_diff = -(angle_diff + 180) % 360 - 180

        sleep_time = utils.map_number(abs(angle_diff), 0, 50, 0, 0.1)
        sleep_time = abs(sleep_time)
        sleep_time = min(sleep_time, 0.1)  # Limit sleep time to 0.1 seconds

        display.write_text(f"sleep_time: {sleep_time:.2f}", tp.Pos(0, 9))
        if angle_diff < 0:
            keyboard.press('a')
            if sleep_time < 0.1:
                time.sleep(sleep_time)
                keyboard.release('a')
            # time.sleep(sleep_time)
        elif angle_diff > 0:
            keyboard.press('d')
            if sleep_time < 0.1:
                time.sleep(sleep_time)
                keyboard.release('d')

    def start_event_loop(self):
        def thread():
            while True:
                shared.steering_event.wait()
                self.process()
                # utils.measure_func(self.run_process)
                shared.steering_event.clear()

        return threading.Thread(target=thread, daemon=True).start()

    def trigger_processing(self):
        """Call the process from main thread without blocking it."""
        self.call_time = time.time()
        # self.shared = shared.snapshot(self.call_time)
        shared.steering_event.set()


processor = SteeringProcessor()

