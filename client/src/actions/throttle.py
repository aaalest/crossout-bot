import random
import time
import numpy as np
import cv2 as cv
import matplotlib.pyplot as plt
import threading
from toolbox.logger import logger
import json
import requests
from dataclasses import dataclass, asdict, field
import aiohttp
from typing import Optional, List, Tuple, Any, Union, Dict
import ast
from datetime import datetime
import os

import threading
import time
import cv2
import keyboard

from toolbox import constants, custom_types as tp, utils
from toolbox.display import display
from toolbox.shared import shared
from toolbox.logger import logger

from scipy.ndimage import sobel
import scipy

from heapq import heappush, heappop
import time


class ThrottleProcessor:
    def __init__(self):
        self.call_time = 0

    def process(self):
        # return
        goal_angle = shared.goal_angle
        current_speed = shared.player.speed

        angle_diff = shared.player.yaw - goal_angle
        angle_diff = -(angle_diff + 180) % 360 - 180
        base_goal_speed = 70
        speed_reduction = min(abs(angle_diff) / 2, 50)
        target_speed = base_goal_speed - speed_reduction  # Reduce speed based on angle difference

        # time_spent_on_steering = time.time() - self.call_time
        throttle_time = target_speed + 10 - current_speed
        throttle_time = max(0, throttle_time)  # Ensure throttle time is non-negative
        # throttle_time = utils.map_number(0, 10, 0, 0.1, throttle_time)
        throttle_time = throttle_time / 100
        throttle_time = min(throttle_time, 0.1)  # Limit throttle time to 0.1 seconds
        # logger.info(f'throttle_time: {throttle_time}, current_speed: {current_speed:.2f}, target_speed: {target_speed:.2f}, angle_diff: {angle_diff:.2f}')
        if throttle_time > 0:
            keyboard.press('w')
            time.sleep(throttle_time)
        if throttle_time < 0.1:
            keyboard.release('w')
        # print(f"Time spent on steering: {time_spent_on_steering * 1000} ms, throttle_time: {throttle_time * 1000:.2f} ms")

        # # Adjust speed based on angle difference
        # w_press_time = 100 - abs(angle_diff)
        # w_press_time = max(0, w_press_time)
        #
        # keyboard.press('w')
        # time.sleep(w_press_time)
        # keyboard.release('w')
        # print(f"Processed steering with angle_diff: {angle_diff:.2f}, sleep_time: {sleep_time:.2f}")

    def start_event_loop(self):
        def thread():
            while True:
                shared.throttle_event.wait()
                self.process()
                # utils.measure_func(self.run_process)
                shared.throttle_event.clear()

        return threading.Thread(target=thread, daemon=True).start()

    def trigger_processing(self):
        """Call the process from main thread without blocking it."""
        self.call_time = time.time()
        # self.shared = shared.snapshot(self.call_time)
        shared.throttle_event.set()


processor = ThrottleProcessor()
