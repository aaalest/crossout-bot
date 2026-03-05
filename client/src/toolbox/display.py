import os
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
import keyboard
import pyjson5

from toolbox.shared import shared
from toolbox import custom_types as tp
from toolbox.logger import logger

"""metadata classes"""


@dataclass
class Image:
    title: str
    frame: np.ndarray
    initial_pos: Optional[tp.Pos] = None
    auto_focus: bool = False
    hwnd: Optional[int] = None
    new: bool = True


@dataclass
class Text:
    text: str
    pos: tp.Pos
    color: Tuple[int, int, int] = (255, 255, 255)
    timeout: float = 0.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class Data:
    images_pos: Dict[str, tp.Pos] = field(default_factory=dict)


class Display:
    GRID_WIDTH = 700
    GRID_HEIGHT = 400
    X_STEP = 30
    Y_STEP = 30
    X_OFFSET = 2
    Y_OFFSET = 15

    def __init__(self):
        self.data: Data = self._load_data()
        self._images: Dict[str, Image] = {}
        self._texts: Dict[str, Text] = {}
        self._stop_evt = threading.Event()
        self._window_focused = False
        self._thread: Optional[threading.Thread] = None

        # build static grid once
        self._text_template = self._build_grid()

        # # launch thread
        # self._thread = threading.Thread(target=self._loop, daemon=True)
        # self._thread.start()

    @staticmethod
    def _load_data() -> Data:
        # Load and parse TOML
        # with open(", "r") as f:
        #     data = pyjson5.load(f)
        #
        # data = Data(
        #     images_pos=data.get("images_pos", {})
        # )
        path = "data/display.json5"
        if os.path.exists(path):
            with open(path, "r") as f:
                raw = pyjson5.load(f)
        else:
            raw = {}
        data = tp.decode(raw)
        data = Data(
            images_pos=data["__Data__"].get("images_pos", {})
        )
        return data

    def _save_data(self):
        """Save the current state to a JSON file."""
        _images = self._images
        data = tp.encode(Data(
            images_pos={title: win.initial_pos for title, win in self._images.items() if win.initial_pos}
        ))
        with open(r"data/display.json5", "w", encoding="utf-8") as f:
            f.write(pyjson5.dumps(data))
        logger.info(f"Display data saved")

    """public API"""

    def show_image(self,
                   title: str,
                   frame: np.ndarray,
                   initial_pos: Optional[tp.Pos] = None,
                   auto_focus: bool = False):
        """Register or update an image window."""
        win = self._images.get(title)
        initial_pos = self.data.images_pos.get(title) or tp.Pos(0, 0)

        # logger.info(initial_pos)
        if not win:
            win = Image(title=title, frame=frame, initial_pos=initial_pos, auto_focus=auto_focus)
            self._images[title] = win
        else:
            win.frame = frame
            win.auto_focus = auto_focus
        win.new = win.hwnd is None

    def write_text(self,
                   text: str,
                   pos: tp.Pos,
                   color: Tuple[int, int, int] = (255, 255, 255),
                   timeout: float = 0.0):
        """Add or replace a text entry (auto‑erased after timeout)."""
        self._texts[f"{pos.x}, {pos.y}"] = Text(text=text, pos=pos, color=color, timeout=timeout)

    def erase_text(self, pos: tp.Pos):
        """Remove a text entry by its grid position."""
        self._texts.pop(f"{pos.x}, {pos.y}`, None")

    def close_window(self, title: str):
        """Close (and remove) an image window."""
        win = self._images.pop(title, None)
        if win and win.hwnd:
            win32gui.PostMessage(win.hwnd, win32con.WM_CLOSE, 0, 0)

    def stop(self):
        """Stop the display loop and close all windows."""
        self._stop_evt.set()
        self._thread.join()
        for title, win in self._images.items():
            if win.hwnd:
                win32gui.PostMessage(win.hwnd, win32con.WM_CLOSE, 0, 0)

    def hotkey_save_data(self):
        active = win32gui.GetWindowText(win32gui.GetForegroundWindow())
        valid = list(self._images.keys())
        if active in valid:
            # update initial position
            for win in self._images.values():
                pos = win32gui.GetWindowRect(win.hwnd)[:2]
                self._images[win.title].initial_pos = tp.Pos(pos[0], pos[1])
            self._save_data()

    """internal helpers"""

    def _build_grid(self) -> np.ndarray:
        """Draw the background grid once, to be copied each frame."""
        canvas = np.zeros((self.GRID_HEIGHT, self.GRID_WIDTH, 3), np.uint8)
        for x in range(0, self.GRID_WIDTH, self.X_STEP):
            for y in range(0, self.GRID_HEIGHT, self.Y_STEP):
                cv2.line(canvas, (x, 0), (x, self.GRID_HEIGHT), (40, 40, 40), 1)
                cv2.line(canvas, (0, y), (self.GRID_WIDTH, y), (40, 40, 40), 1)
                label = f"{x // self.X_STEP},{y // self.Y_STEP}"
                cv2.putText(canvas, label,
                            (x + 1, y + self.Y_STEP - 3),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.3, (40, 40, 40), 1)
        return canvas

    def _get_focus(self) -> bool:
        """Return True if current foreground window title is one of ours."""
        active = win32gui.GetWindowText(win32gui.GetForegroundWindow())
        valid = list(self._images.keys()) + [shared.game_title]
        valid += ["", "Task Switching"] if self._window_focused else []
        return active in valid

    def _loop(self):
        """Main update loop: redraw texts, manage focus, show windows."""
        while not self._stop_evt.is_set():
            # 1) Text frame
            frame = self._text_template.copy()
            now = time.time()
            for key, entry in list(self._texts.items()):
                if entry.timeout and now - entry.timestamp > entry.timeout:
                    self._texts.pop(key)
                    continue
                x = entry.pos.x * self.X_STEP + self.X_OFFSET
                y = entry.pos.y * self.Y_STEP + self.Y_OFFSET
                cv2.putText(frame, entry.text, (x, y),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.5, entry.color, 1)
            self.show_image("text", frame, initial_pos=tp.Pos(1800, 1130), auto_focus=True)

            # 2) Image windows
            focus_changed = (self._get_focus() != self._window_focused)
            self._window_focused = not self._window_focused if focus_changed else self._window_focused

            try:
                for win in self._images.values():
                    cv2.imshow(win.title, win.frame)
                    if win.new:
                        win.new = False
                        win.hwnd = win32gui.FindWindow(None, win.title)
                        if win.hwnd == 0:
                            logger.error(f"Window not found: {win.title}")
                        elif win.initial_pos:
                            x, y = win.initial_pos.x, win.initial_pos.y
                            win32gui.SetWindowPos(win.hwnd, None, x, y, 0, 0,
                                                  win32con.SWP_NOSIZE | win32con.SWP_NOZORDER)

                    # auto‑focus logic
                    if win.auto_focus and focus_changed and win.hwnd:
                        flag = win32con.HWND_TOPMOST if self._window_focused else win32con.HWND_NOTOPMOST
                        show = win32con.SWP_SHOWWINDOW if self._window_focused else win32con.SWP_HIDEWINDOW
                        win32gui.SetWindowPos(win.hwnd, flag, 0, 0, 0, 0,
                                              win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | show)
            except RuntimeError as e:
                if "dictionary changed size during iteration" in str(e):
                    continue  # retry the loop
                else:
                    raise  # re-raise other RuntimeErrors

            # 3) Diagnostics
            self.write_text(f"mouse: {win32gui.GetCursorPos()}", tp.Pos(10, 11))
            # if shared.frame is not None:
            #     summary = shared.frame.sum() if isinstance(shared.frame, np.ndarray) else shared.frame
            #     self.write_text(f"shared.frame: {summary}", tp.Pos(8, 9))
            cv2.waitKey(100)

    def start(self):
        """Start the display loop."""
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()


display = Display()
