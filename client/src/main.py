import threading
import time
import cv2
import ctypes
import asyncio
import numpy as np
import win32gui
# from windows_capture import WindowsCapture, Frame, InternalCaptureControl

from readers import interface
from readers import map
from readers import window
from readers import lockon
from actions import camera
from actions import steering
from actions import throttle
import pathing
import hotkeys

from toolbox import constants, custom_types as tp, utils
from toolbox.shared import shared
from toolbox.display import display
from toolbox.logger import logger


class Bot:
    def __init__(self):
        self.frame_count = 0
        self.frame_interval = 1.0 / 60  # FPS

    def run(self):
        map_thread = map.processor.start_event_loop()
        camera_thread = camera.processor.start_event_loop()
        lockon_thread = lockon.processor.start_event_loop()
        pathing_thread = pathing.processor.start_event_loop()
        steering_thread = steering.processor.start_event_loop()
        throttle_thread = throttle.processor.start_event_loop()
        display_thread = display.start()

        hotkeys.activate()

        shared.map_type = tp.Map.GARAGE
        shared.map_img = constants.MAP_IMAGES[shared.map_type.name]
        shared.map_layers["background"] = shared.map_img

        def process():
            self.frame_count += 1
            display.write_text(f"frame_count: {self.frame_count}", pos=tp.Pos(0, 11))
            timestamp = time.time()

            if self.frame_count % 60 == 0:  # 1 FPS
                window.processor.process()

            if shared.game_focused:
                # logger.info(f"Client area: {shared.client_area}")
                if tp.Menu.BATTLE not in shared.menu:
                    interface.processor.process()

                if tp.Menu.BATTLE not in shared.menu:
                    time.sleep(1)
                elif tp.Menu.BATTLE in shared.menu:
                    # if self.frame_count % 5 == 0:
                    camera.processor.trigger_processing()
                    if self.frame_count % 5 == 0:  # 12 FPS
                        lockon.processor.trigger_processing()
                    if self.frame_count % 6 == 0:  # 10 FPS
                        map.processor.trigger_processing()
                    if self.frame_count % 6 == 0:  # 10 FPS
                        pathing.processor.trigger_processing()

            if time.time() - timestamp < self.frame_interval:  # FPS cap
                time.sleep(abs(self.frame_interval - (time.time() - timestamp)))

        while True:
            process()
            # utils.measure_func(process)


bot = Bot()

if __name__ == "__main__":
    bot.run()
