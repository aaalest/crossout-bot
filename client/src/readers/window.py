import threading
import time
import cv2
import numpy as np
from PIL import Image
import win32gui
import win32api
import win32con
import ctypes
from ctypes import wintypes
from typing import Optional, List, Tuple, Any, Union, Dict
import concurrent.futures
import dxcam
import mss
import pygame
from line_profiler import LineProfiler
from concurrent.futures import ThreadPoolExecutor
import _ctypes

from toolbox import constants, custom_types as tp, utils
from toolbox.display import display
from toolbox.shared import shared
from toolbox.logger import logger


class Processor:
    def __init__(self):
        self.consumed_frames = 0
        self.frame_event = threading.Event()  # Event to signal frame updates
        self.stop_flag = threading.Event()  # Event to stop threads
        self.update_time = time.time()
        self.condition = threading.Condition()
        self.frame_timestamp = time.time()
        self.display_screen = None

        self.update_game_frame_lock = threading.Lock()

        self.hud_event = threading.Event()
        self.interface_event = threading.Event()
        self.display_event = threading.Event()
        self.actions_event = threading.Event()

        window_title = ""
        window_hwnd = 0
        while not window_title.startswith(constants.GAME_TITLE_PREFIX):  # if starts with "Crossout 2."
            windows = []

            def enum_windows_callback(hwnd, _):
                if win32gui.IsWindowVisible(hwnd):  # Only list visible windows
                    title = win32gui.GetWindowText(hwnd)
                    if title:  # Skip windows without titles
                        windows.append((hwnd, title))

            win32gui.EnumWindows(enum_windows_callback, None)

            for window_hwnd, window_title in windows:
                if window_title.startswith(constants.GAME_TITLE_PREFIX):
                    break
            if not window_title.startswith(constants.GAME_TITLE_PREFIX):
                logger.warn(f"Window not found, retrying...")
                time.sleep(1)

        logger.info(f"Window Title: {window_title}, HWND: {window_hwnd}")
        shared.game_title = window_title
        shared.game_hwnd = window_hwnd

    @staticmethod
    def _get_window_dimensions():
        # Full window rect (with borders)
        window_rect = win32gui.GetWindowRect(shared.game_hwnd)
        window_x, window_y, window_w, window_h = window_rect
        window_width = window_w - window_x
        window_height = window_h - window_y

        # Client area (without borders)
        client_rect = win32gui.GetClientRect(shared.game_hwnd)
        client_w, client_h = client_rect[2], client_rect[3]

        # Map client rect to screen coordinates
        client_topleft = win32gui.ClientToScreen(shared.game_hwnd, (0, 0))

        # Calculate the border sizes
        border_left = client_topleft[0] - window_x
        border_top = client_topleft[1] - window_y
        border_right = window_width - client_w - border_left
        border_bottom = window_height - client_h - border_top

        window_rect = tp.Region(
            left=window_x,
            top=window_y,
            width=window_width,
            height=window_height
        )
        game_region = tp.Region(
            left=client_topleft[0],
            top=client_topleft[1],
            width=client_w,
            height=client_h
        )
        borders = tp.Region(
            left=border_left,
            top=border_top,
            width=border_right,
            height=border_bottom
        )
        return window_rect, game_region, borders

    def process(self):
        # camera = dxcam.create(output_color="BGRA")
        # self.display_init("Game Display", 1500, 600, 1250, 1080)
        # logger.info("Capture thread started")

        # Make sure the window is focused and running
        if win32gui.GetForegroundWindow() != shared.game_hwnd:
            shared.game_focused = False
            logger.warn(f'Window is not focused or not running')
            return

        # Get the window dimensions with borders
        window_rect, game_region, borders = self._get_window_dimensions()
        desirable_width = constants.GAME_WIDTH + borders.left + borders.width
        desirable_height = constants.GAME_HEIGHT + borders.top + borders.height

        if window_rect.width != desirable_width or window_rect.height != desirable_height:
            # shared.game_region = None
            win32gui.MoveWindow(
                shared.game_hwnd,
                window_rect.left,
                window_rect.top,
                desirable_width,
                desirable_height,
                True
            )
            time.sleep(0.01)
            return

        screen_w = win32api.GetSystemMetrics(0)
        screen_h = win32api.GetSystemMetrics(1)

        # Determine new positions
        new_x = max(0, min(window_rect.left, screen_w - desirable_width))
        new_y = max(0, min(window_rect.top, screen_h - desirable_height))

        # Check if the window is out of bounds
        if new_x != window_rect.left or new_y != window_rect.top:
            # shared.game_region = None
            logger.warn("Window is out of screen bounds")
            # Move the window to the new position
            win32gui.MoveWindow(
                shared.game_hwnd,
                new_x,
                new_y,
                desirable_width,
                desirable_height,
                True
            )
            time.sleep(0.01)
            return
        shared.game_region = game_region
        shared.game_focused = True
        display.write_text(f"{game_region}", tp.Pos(7, 12))

        # frame = camera.grab(region=(
        #     game_region["x"],
        #     game_region["y"],
        #     game_region["x"] + game_region["w"],
        #     game_region["y"] + game_region["h"]
        # ))
        # frame = camera.grab(region=(0, 0, 1920, 1080))
        # if frame is None:
        #     return
        # frame = frame.copy()
        # shared.game_layers["background"] = frame[::2, ::2, :][:, :, :3].copy()  # downscale by 2
        # frame = frame[:, :, :3]  # remove alpha channel
        # shared.frame = frame
        # downscaled_img2 = frame[::1, ::1, :]
        # downscaled_img[:] = 0

        # draw a circle in center of image
        # img = downscaled_img2
        # cv2.circle(img, (img.shape[1] // 2, img.shape[0] // 2), 30, (255, 255, 0), -1)

        # downscaled_img[:] = 0
        # cv2.imshow("downscaled_img", downscaled_img)
        # cv2.imshow("downscaled_img2", downscaled_img2)
        # cv2.imshow("frame", frame)
        # cv2.waitKey(0)

        # cv2.imshow("left_half", left_half)
        # cv2.imshow("right_half", right_half)
        # cv2.imshow("frame", frame)
        # cv2.waitKey(1)

        # frame2 = cv2.resize(frame, (0, 0), fx=1, fy=1, interpolation=cv2.INTER_NEAREST)
        # frame3 = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25, interpolation=cv2.INTER_NEAREST)
        # frame4 = frame.copy()

        # cv2.imshow("frame", frame)
        # cv2.waitKey(1)
        # shared.frame_copy = img
        # dummy_img[:] = 0

        # cv2.imshow("capture_thread Frame", frame)
        # cv2.waitKey(0)

        # shallow_copy = np.array(frame, copy=True)
        # # flip array
        # shallow_copy[:] = 0
        # compare array to frame to see if are diff
        # print(np.array_equal(shared.frame, frame))
        # cv2.imshow("show", frame)
        # cv2.waitKey(1)

        # self.frame_timestamp = time.time()
        #
        # self.hud_event.set()
        # self.interface_event.set()
        # self.display_event.set()
        # self.actions_event.set()
        # self.display(frame, time.time())
        # logger.info(f"executor.submit delay: {(time.time() - self.frame_timestamp) * 1000} ms")

        # condition_timestamp = time.time()
        # self.frame_event.set()  # Signal that a new frame is available
        # with self.condition:
        #     self.condition.notify()  # Notify the display thread
        # print(f"frame_event time: {time.time() - condition_timestamp}")

        # cv2.imshow("capture_thread Frame", cv2.resize(frame, (0, 0), fx=0.4, fy=0.4))
        # cv2.waitKey(1)
        # time.sleep(0.016 * 2)
        # logger.warn(f"capture_thread delay: {(time.time() - timestamp) * 1000} ms")
        # fps = 1 / (time.time() - timestamp + 1e-9)
        # print(f"FPS: {fps:.0f}")
        # fps_list.append(fps)
        # fps_list = fps_list[-100:]
        # logger.warn(f"capture_thread Average FPS: {sum(fps_list) / len(fps_list)}")

        # while True:
        #     utils.measure_func(process)
        #     # process()


processor = Processor()
