import threading
import time
import numpy as np
import cv2
import ctypes
from typing import Optional, List, Tuple, Any, Union, Dict

from toolbox import constants, utils, custom_types as tp
from toolbox.display import display
from toolbox.shared import shared
from toolbox.logger import logger


class InterfaceProcessor:
    def __init__(self):
        self.call_time = 0
        self.latest_frame_time = 0  # Shared variable for the latest frame time
        self.consumed_frames = 0
        self.diff_frame = None
        # self.camera = dxcam.create(output_color="BGRA")

        # self.menus: Dict[str, np.ndarray] = {}
        # for menu_obj in tp.Menu:
        #     menu_img = cv2.imread(rf"assets/images/menus/{menu_obj.name}.png")
        #     self.menus[menu_obj.name.lower()] = menu_img
        #     logger.info(f"Loaded menu: {menu_obj.name
        self.menus_cut: Dict[str, dict] = {}
        self.BATTLE_MENU_NAME = "BATTLE"
        for menu_obj in tp.Menu:
            img = constants.MENU_IMAGES[menu_obj.name]
            row_indexes, col_indexes = np.where(img[:, :, 3])
            self.menus_cut[menu_obj.name] = {
                "row": row_indexes,
                "col": col_indexes,
                "img": img[row_indexes, col_indexes, :3]
            }

    def is_menu_match(self, name: str, cut_img: np.ndarray, template_img: np.ndarray) -> bool:
        if name == self.BATTLE_MENU_NAME:
            matched_pixels = np.sum(cut_img == template_img)
            match_ratio = matched_pixels / cut_img.size
            return match_ratio > 0.9
        else:
            return np.all(cut_img == template_img)

    def update_menu_flag(self, name: str, match: bool) -> None:
        if match:
            if name == self.BATTLE_MENU_NAME:
                shared.menu = tp.Menu[name]  # set flag
            else:
                shared.menu |= tp.Menu[name]  # add flag
        else:
            shared.menu &= ~tp.Menu[name]  # remove flag

    def classify_menu(self, frame, name, x_offset=0, y_offset=0):
        # logger.warn(f"Classifying menu: {name}")
        col_indexes = self.menus_cut[name]["col"] + x_offset
        row_indexes = self.menus_cut[name]["row"] + y_offset
        template = self.menus_cut[name]["img"]

        source = frame[row_indexes, col_indexes, :3]

        match = self.is_menu_match(name, source, template)
        self.update_menu_flag(name, match)

    def process(self, state: str = ""):
        logger.info(state)
        frame = utils.get_mss_frame(shared.game_region)

        if not utils.is_valid_array(frame):
            shared.menu = tp.Menu(0)
            return

        for name, img in constants.MENU_IMAGES.items():
            self.classify_menu(frame, name)
            if name == "BATTLE" and tp.Menu.BATTLE in shared.menu:
                break
        display.write_text(f"Menu: {shared.menu.name}", tp.Pos(0, 12))

        if utils.key_state(0x11) and utils.key_state(0x04):  # generic ctrl + middle mouse button
            # print("Ctrl + Middle Mouse Button")
            if self.diff_frame is None:
                self.diff_frame = frame
                # self.diff_frame = cv2.imread(r"assets/images/menus/_diff.png", cv2.IMREAD_UNCHANGED)
                # self.diff_frame = cv2.imread(r"assets/images/menus/BATTLE.png", cv2.IMREAD_UNCHANGED)
            else:
                diff_frame = cv2.absdiff(self.diff_frame, frame)
                condition = np.any(diff_frame != 0, axis=2)
                self.diff_frame[condition] = [0, 0, 0, 0]
                # time.sleep(1)

        if self.diff_frame is not None:
            # display.images["diff"] = self.diff_frame[::3, ::3]
            display.show_image("diff", self.diff_frame[::3, ::3], tp.Pos(1145, 1145), auto_focus=True)
            if utils.key_state(0x04) and utils.key_state(0x12):  # generic alt + middle mouse button
                cv2.imwrite(r"assets/images/menus/_diff.png", self.diff_frame)
                logger.info("Diff frame saved")

        # reshape grame to 1x3 long array
        # line = frame[:, :, :3].reshape(-1, 3)
        # mask = np.all(line == [255, 255, 255], axis=1)
        # masked_indices = np.where(mask)[0]
        # white_pixels = line[masked_indices]
        # white_pixels_copy = white_pixels.copy()
        # diff = (white_pixels == white_pixels_copy).all()
        # logger.info(f"fame size: {frame.shape}")
        # cv2.imshow("frame", frame)
        # cv2.waitKey(0)

        # timestamp = time.time()
        # logger.info(f"Frame state time: {(time.time() - timestamp) * 1000:.2f} ms, state: {state}")

        # map_layer = np.zeros(shared.map_layers["shape"], dtype=np.uint8)

        """Classify the interface menu"""
        # shared.menu = tp.Menu.BATTLE
        shared.map_type = tp.Map.GARAGE
        shared.map_img = constants.MAP_IMAGES[shared.map_type.name]
        # cv2.imshow("map", shared.map_img)
        # cv2.waitKey(0)
        # print(shared.menu)


processor = InterfaceProcessor()
