import win32api
import win32con
import websockets
import json
import pydirectinput
from dataclasses import dataclass
import threading
import time
import numpy as np
import cv2
import math
import mss
from typing import Optional, List, Tuple, Any, Union, Dict
import copy
import ctypes

pydirectinput.FAILSAFE = False
import keyboard
from pynput.keyboard import Key, Controller

controller = Controller()

from toolbox import constants, utils, custom_types as tp
from toolbox.display import display
from toolbox.shared import shared
from toolbox.logger import logger


class CameraProcessor:
    def __init__(self):
        self.call_time = 0
        # self.shared: Shared = shared.snapshot(self.call_time)

        self.sct = None

    def move_camera_by(self, x: int, y: int):
        if shared.camera.y + y < -997:
            y = -997 - shared.camera.y
        if shared.camera.y + y > 997:
            y = 997 - shared.camera.y
        win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, x, y, 0, 0)
        shared.camera.x += x
        shared.camera.y += y
        # shared.camera.angle = utils.map_number(-2244, 2244, -180, 180, shared.camera.x)

    def move_camera_to(self, x: int | None, y: int | None):
        if x is None:  # don't move x
            x = shared.camera.x
        if y is None:  # don't move y
            y = shared.camera.y
        self.move_camera_by(x - shared.camera.x, y - shared.camera.y)

    def reset_camera_origin(self):
        """
        Reset the camera to the origin point (0, 0) in the game.
        """
        keyboard.press_and_release('t')
        time.sleep(0.1)
        keyboard.press_and_release('t')
        car_yaw = shared.player.yaw
        car_yaw = (car_yaw + 90) % 360
        if car_yaw > 180:
            car_yaw = car_yaw - 360
        camera_x = utils.map_number(car_yaw, -180, 180, -2244, 2244)
        logger.info(f'camera_x: {camera_x}')
        # for i in range(10000):
        #     self.move_mouse_by(0, 1)
        win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, 0, 3000, 0, 0)
        shared.camera = tp.Camera(x=int(camera_x), y=997)
        time.sleep(0.1)
        self.move_camera_to(None, 0)

    @staticmethod
    def _scale_axis(value: float) -> int:
        sensitivity = 0.1
        dead_zone = 4

        if abs(value) < dead_zone:
            return 0
        scaled = max(1, int(abs(value) * sensitivity))
        return scaled if value > 0 else -scaled

    def process(self):
        if shared.aiming_state and shared.target:
            distance: tp.Meter = 18
            shared.is_target_accurate = False
            if shared.looking_at_enemy and shared.looking_at_enemy.distance > utils.px2m(4):
                distance: tp.Meter = utils.px2m(shared.looking_at_enemy.distance)
                shared.is_target_accurate = True
            target_y_offset = (2000 / distance + 4)
            display.write_text(f"target_y_offset: {target_y_offset:.2f}, distance: {distance:.2f}m", tp.Pos(8, 4), timeout=0.1)
            display.write_text(f"is_target_accurate: {shared.is_target_accurate}", tp.Pos(8, 3))

            move_by = tp.Pos(
                shared.target.x - constants.CENTER.x,
                shared.target.y - constants.CENTER.y + target_y_offset,
            )

            move_by.x = self._scale_axis(move_by.x)
            move_by.y = self._scale_axis(move_by.y)
            # logger.info(f"move_by: {move_by}")
            # root = 1
            # multiply = 0.1
            # move_by.x = int(abs(move_by.x) ** root * multiply * np.sign(move_by.x))
            # move_by.y = int(abs(move_by.y) ** root * multiply * np.sign(move_by.y))
            self.move_camera_by(*move_by)
            move_len = math.sqrt(move_by.x ** 2 + move_by.y ** 2)
            display.write_text(f"move_len: {move_len}", tp.Pos(8, 5))
            if move_len < 4:
                ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)  # left mouse button down
            else:
                ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)  # left mouse button up

        if tp.Menu.BATTLE in shared.menu:
            ctrl_state = utils.key_state(0x11)
            alt_state = utils.key_state(0x12)

            pixels_per_sec = 600
            if ctrl_state and alt_state:
                pixels_per_sec = 2500
            elif ctrl_state:
                pixels_per_sec = 200
            elif alt_state:
                pixels_per_sec = 10
            pixels_per_sec = max(int(pixels_per_sec / constants.FPS), 1)
            if utils.key_state(0x25):  # left
                self.move_camera_by(-pixels_per_sec, 0)
            if utils.key_state(0x27):  # right
                self.move_camera_by(pixels_per_sec, 0)
            if utils.key_state(0x26):  # up
                self.move_camera_by(0, -pixels_per_sec)
            if utils.key_state(0x28):  # down
                self.move_camera_by(0, pixels_per_sec)

        display.write_text(f"{shared.camera}", tp.Pos(8, 10))
        display.write_text(f"{shared.camera.yaw}", tp.Pos(15, 10))

    @utils.require_game_focus
    def hotkey_center_camera(self):
        self.move_camera_to(0, 0)

    @utils.require_game_focus
    def hotkey_reset_camera_origin(self):
        self.reset_camera_origin()

    def start_event_loop(self):
        def thread():
            while True:
                shared.camera_event.wait()
                self.process()
                # utils.measure_func(self.process)
                shared.camera_event.clear()

        return threading.Thread(target=thread, daemon=True).start()

    def trigger_processing(self):
        """Call the process from main thread without blocking it."""
        self.call_time = time.time()
        # shared_ = shared
        # self.shared = shared.snapshot(self.call_time)
        shared.camera_event.set()


processor = CameraProcessor()
