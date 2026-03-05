import random
import time
import win32gui
import threading
from dataclasses import dataclass, fields, field
from typing import Optional, Any, Tuple, Dict
import win32api
import win32con
import ctypes
import _ctypes
import cv2
import numpy as np
import math
import mss
import dxcam
import pygame
from line_profiler import LineProfiler
import tomllib

from toolbox.shared import shared
from toolbox.shared import constants
from toolbox import custom_types as tp
from toolbox.logger import logger

profiler = LineProfiler()


def gray(g: int) -> tuple[int, int, int]:
    return g, g, g


def rgb(r: int, g: int, b: int) -> tuple[int, int, int]:
    return b, g, r


def rgba(r: int, g: int, b: int, a
: int = 255) -> tuple[int, int, int, int]:
    return b, g, r, a


def map_number(number: float, in_min: float, in_max: float, out_min: float, out_max: float) -> float:
    return (number - in_min) * (out_max - out_min) / (in_max - in_min) + out_min


def shift_angle(angle: float, offset: float) -> float:
    return ((angle + offset + 180) % 360) - 180


def img2gray(img: np.ndarray) -> np.ndarray:
    if img.shape[-1] == 4:  # Drop alpha channel
        img = img[..., :3]
    return np.dot(img[..., 0:3], [0.299, 0.587, 0.114]).astype(np.uint8)


scts: Dict[str, mss.mss] = {}
camera = dxcam.create(output_color="BGRA")


def get_mss_frame(region: tp.Region = None) -> np.ndarray | None:
    """
    Capture a frame using mss.
    Mss is best for capturing a region of the screen.
    Mss uses CPU and is not as fast as dxcam.
    """
    thread_name = threading.current_thread().name
    sct = scts.get(thread_name)
    if sct is None:
        sct = mss.mss()
        scts[thread_name] = sct
    try:
        frame = np.array(sct.grab({
            "left": region.left,
            "top": region.top,
            "width": region.width,
            "height": region.height
        }))
    except mss.exception.ScreenShotError as e:
        logger.warn(f"mss Capture Error: {e}")
        scts[thread_name] = mss.mss()
        return None
    return frame


def get_zbl_frame(region: tp.Region = None) -> np.ndarray | None:
    """
    Capture a frame using zbl.
    zbl is best for capturing the entire screen.
    """
    frame = None
    try:
        frame = camera.grab(region=(
            region.left,
            region.top,
            region.left + region.width,
            region.top + region.height
        ))
    except _ctypes.COMError as e:
        logger.warn(f"DirectX Capture Error: {e}")
    # logger.info(f"shared.frame.sum: {shared.frame.sum()}, shared.frame_time: {shared.frame_time}")
    if frame is None:
        logger.warn("Failed to capture frame")
        return None
    # frame = cv2.putText(shared.frame.copy(), f"SUM: {shared.frame.sum()}", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 3, (0, 255, 255), 4)
    # utils.display.write_text(f"SUM: {frame.sum()}", tp.Pos(3, 1))
    # display.show_image("full frame", frame[::4, ::4], initial_pos=tp.Pos(0, 410), auto_focus=True)
    return frame


def measure_func(process, *args, **kwargs) -> Any:
    """
    Measure function execution time and print stats.
    Note: Time is measured in 10000s of a millisecond.
    """

    profiler.add_function(process)
    profiler.enable()
    result = process(*args, **kwargs)
    profiler.disable()
    profiler.print_stats()
    return result


def require_game_focus(func):
    def wrapper(*args, **kwargs):
        if not shared.game_focused:
            return
        return func(*args, **kwargs)

    return wrapper


def is_valid_array(arr) -> bool:
    return isinstance(arr, np.ndarray) and arr.size > 0


# def is_game_focused() -> bool:
#     return win32gui.GetForegroundWindow() == shared.game_hwnd


def flip_state(self, attr):
    setattr(self, attr, not getattr(self, attr))


def key_state(key) -> bool:
    return ctypes.windll.user32.GetAsyncKeyState(key) & 0x8000 != 0


def posterize_img(img: np.ndarray, level: int = 3) -> np.ndarray:
    bins = img // (256 // level)
    img[:] = (bins * (255 // (level - 1))).clip(0, 255).astype(np.uint8)
    return img


def quantize_img(img: np.ndarray, level: int = 3) -> np.ndarray:
    level = 2 ** level
    img[:] = (img // level) * level
    return img


def rotate_image(image, angle):
    (h, w) = image.shape[:2]
    center = (w / 2, h / 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)  # Compute the rotation matrix
    rotated_image = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_LANCZOS4)  # Perform the rotation
    return rotated_image


def rotate_point(point, angle, origin) -> np.ndarray:
    ox, oy = origin
    x, y = point
    x -= ox
    y -= oy

    # Calculate the new coordinates using the rotation matrix
    x_new = x * math.cos(angle) - y * math.sin(angle)
    y_new = x * math.sin(angle) + y * math.cos(angle)

    # Translate point back to its original position relative to the origin
    x_new += ox
    y_new += oy

    return point


def px2m(px: float) -> float:
    """Convert pixels to meters using the px2m ratio."""
    return px * shared.px2m_ratio


def m2px(m: float) -> float:
    """Convert meters to pixels using the px2m ratio."""
    return m / shared.px2m_ratio
