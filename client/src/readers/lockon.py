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
import ctypes

pydirectinput.FAILSAFE = False

from toolbox import constants, utils, custom_types as tp
from toolbox.display import display
from toolbox.shared import shared
from toolbox.logger import logger


class TargeterProcessor:
    def __init__(self):
        self.call_time = 0
        self.last_full_targeting_time = 0

        # self.shared: Shared = shared.snapshot(self.call_time)
        # shared.target: Optional[tp.Pos] = None

        self.sct = None
        self.enemy_mark_clear_mask = cv2.imread(r"assets/enemy_mark_mask.png", cv2.IMREAD_UNCHANGED)[:, :, 0]

        self.unclear_lower = utils.rgb(200, 35, 35)
        self.unclear_upper = utils.rgb(255, 55, 55)
        self.enemy_mark_unclear = cv2.imread(r"assets/enemy_mark.png", cv2.IMREAD_UNCHANGED)
        self.enemy_mark_unclear_mask = cv2.inRange(self.enemy_mark_unclear, self.unclear_lower, self.unclear_upper)
        # self.enemy_mark_unclear_matchTemplate_mask = cv2.inRange(self.enemy_mark_unclear_mask, 255, 255)
        # self.target_template_bool = self.target_template_mask > 0

    def _match_unclear_target(self, source: np.ndarray) -> tp.Pos | None:
        def filter_close_points(points, scores, min_distance=3):
            filtered = []
            sorted_data = sorted(zip(points, scores), key=lambda x: x[1], reverse=True)
            for pt, score in sorted_data:
                too_close = False
                for fpt, _ in filtered:
                    dist = np.linalg.norm(np.array(pt) - np.array(fpt))
                    if dist < min_distance:
                        too_close = True
                        break
                if not too_close:
                    filtered.append((pt, score))
            return filtered

        source_mask = cv2.inRange(source, self.unclear_lower, self.unclear_upper)
        template_mask = self.enemy_mark_unclear_mask
        template_size = tp.Pos(template_mask.shape[1], template_mask.shape[0])
        # enemy_mark_unclear_matchTemplate_mask = self.enemy_mark_unclear_matchTemplate_mask
        result = cv2.matchTemplate(source_mask, template_mask, cv2.TM_CCOEFF_NORMED)

        threshold = 0.4
        locations = np.where(result >= threshold)

        points = list(zip(*locations[::-1]))
        scores = [result[y, x] for (x, y) in points]

        filtered_points = filter_close_points(points, scores)

        print(f"Filtered targets: {len(filtered_points)}")

        center_x = source.shape[1] / 2
        center_y = source.shape[0] / 2
        center = np.array([center_x, center_y])

        points_with_dist = []
        for pt, score in filtered_points:
            pt_orig = np.array([pt[0], pt[1]])
            dist = np.linalg.norm(pt_orig - center)
            points_with_dist.append((pt_orig, score, dist))

        # Sort by distance ascending
        points_with_dist.sort(key=lambda x: x[2])

        # Draw rectangles and print info
        source_show = source.copy()
        for pt_orig, score, dist in points_with_dist:
            pt_scaled = (int(pt_orig[0]), int(pt_orig[1]))
            cv2.rectangle(source_show, pt_scaled,
                          (pt_scaled[0] + template_size.x, pt_scaled[1] + template_size.y),
                          (0, 255, 0), 2)
            print(f"Location: {tuple(pt_orig)}, Confidence: {score:.3f}, Distance: {dist:.1f}")

        display.show_image("unclear targets", source_show, auto_focus=True)

        if points_with_dist:
            closest_point = points_with_dist[0][0]
            return tp.Pos(int(closest_point[0]), int(closest_point[1]))
        else:
            return None

    @staticmethod
    def _detect_hit_marker(frame: np.ndarray, indent: tp.Region):
        """
        Detect hit marker in the frame and update shared.hit_marker
        Updates shared.hit_marker to True if the hit marker is detected within the specified tolerance.
        """
        valid_value = 200
        tolerance = 30
        slice = np.array([
            [929, 508],
            [930, 509],
            [992, 507],
            [991, 508],
            [929, 570],
            [930, 569],
            [990, 569],
            [991, 570],
        ])

        slice[:, 0] -= indent.left
        slice[:, 1] -= indent.top

        show_frame = frame.copy()
        for point in slice:
            cv2.circle(show_frame, (point[0], point[1]), 1, utils.rgb(255, 0, 0), -1)
        display.show_image("hit marker", show_frame, auto_focus=True)

        try:
            cut_frame = frame[slice[:, 1], slice[:, 0], :3]
        except IndexError as e:
            return False

        cut_frame = cut_frame.flatten()
        is_valid = np.all((cut_frame >= valid_value - tolerance) & (cut_frame <= valid_value + tolerance))
        shared.hit_marker = is_valid

    def _indentify_target(self, mask: np.ndarray) -> tp.Pos | None:
        """
        Match the target template with the image mask
        """

        display.show_image("cut_mask", mask, initial_pos=tp.Pos(1200, 1155), auto_focus=True)

        ys, xs = np.where(mask)
        center = tp.Pos(mask.shape[0] // 2, mask.shape[1] // 2)

        min_x = min(xs)
        left_row = mask[:, min_x]
        left_row_list = np.where(left_row)[0]
        left_top_y = min(left_row_list)
        left_mask = mask[left_top_y:left_top_y + 4, min_x:min_x + 3]
        left_target_template = self.enemy_mark_clear_mask[1:5, 0:3]
        equal_left = np.array_equal(left_mask, left_target_template)
        if equal_left:
            return tp.Pos(min_x + 4 - center.x, left_top_y + 3 - center.y)
            # return tp.Pos(min_x, left_top_y)
            # return tp.Pos(0, 0)

        max_x = max(xs)
        right_row = mask[:, max_x]
        right_row_list = np.where(right_row)[0]
        right_top_y = min(right_row_list)
        right_mask = mask[right_top_y:right_top_y + 4, max_x - 2:max_x + 1]
        right_target_template = self.enemy_mark_clear_mask[1:5, 7:10]
        equal_right = np.array_equal(right_mask, right_target_template)
        if equal_right:
            # print(f"equal_right")
            return tp.Pos(max_x - 5 - center.x, right_top_y + 3 - center.y)
            # return tp.Pos(0, 0)
        return None

    def _match_clear_target(self, frame: np.ndarray, scaled_mask: np.ndarray, downscale: int) -> tp.Pos | None:
        """
        Find the closest target point to the center of the frame
        """

        scaled_points = np.argwhere(scaled_mask == 255)
        # logger.info(f"scaled_points.size: {scaled_points.size}")
        if scaled_points.size == 0:  # if any point found at low resolution
            shared.target = None
            logger.warn("No matching targets found on the mask.")
            return None

        # sort based on the distance from the center
        center = tp.Pos(scaled_mask.shape[0] // 2, scaled_mask.shape[1] // 2)
        # distances = np.linalg.norm(scaled_points - center, axis=1)
        squared_distances = np.sum((scaled_points - center.np()) ** 2, axis=1)
        sorted_indices = np.argsort(squared_distances)
        scaled_points = scaled_points[sorted_indices]

        # flip the points from left to right so that the closest point to the center is first
        # scaled_points = scaled_points[::-1]

        target = None
        for index, scaled_point in enumerate(scaled_points):
            # distance = ((scaled_point[0] - center[0]) ** 2 + (scaled_point[1] - center[1]) ** 2) ** 0.5
            point = tp.Pos(x=scaled_point[1] * downscale, y=scaled_point[0] * downscale)

            # check if the cut frame is out of bounds
            cut_area = tp.Area(
                point.x,
                point.y,
                point.x,
                point.y,
            ).expand(10)
            # if cut_area.x1 < 0 or cut_area.y1 < 0 or cut_area.x2 > frame.shape[0] or cut_area.y2 > frame.shape[1]:
            #     logger.warn("Cut frame is out of bounds.")
            #     break
            cut_frame = frame[cut_area.y1:cut_area.y2, cut_area.x1:cut_area.x2][:, :, :3]
            if cut_frame.shape[0] != cut_frame.shape[1] or cut_frame.shape[0] == 0:
                logger.warn("Cut frame is out of bounds.")
                break

            cut_mask = cv2.inRange(cut_frame, utils.rgb(255, 50, 50), utils.rgb(255, 50, 50))

            target = self._indentify_target(cut_mask)
            if target:
                target = tp.Pos(point.x + target.x, point.y + target.y)  # adjust based on the cut frame position
                display.show_image("cut_frame", cut_frame, initial_pos=tp.Pos(420, 80), auto_focus=True)
                break
        if target is None:
            logger.warn("No matching targets found on the mask.")
        return target
        # display.show_image("full_targeting_mask", scaled_mask, initial_pos=tp.Pos(0, 815), auto_focus=True)

    def _localized_targeting(self):
        """
        Locate the target on cropped frame based on the last target position for optimization
        """

        if self.sct is None:
            self.sct = mss.mss()

        # show_frame = frame[::4, ::4].copy()
        # cv2.line(show_frame, (shared.target.x // 4, 0), (shared.target.x // 4, show_frame.shape[0]), utils.gray(255), 1)
        # cv2.line(show_frame, (0, shared.target.y // 4), (show_frame.shape[1], shared.target.y // 4), utils.gray(255), 1)
        # display.show_image("full frame", show_frame, initial_pos=tp.Pos(0, 410), auto_focus=True)
        indent = tp.Region(
            left=shared.target.x,
            top=shared.target.y,
            width=0,
            height=0
        ).expand(60)

        frame = utils.get_mss_frame(tp.Region(
            left=shared.game_region.left + indent.left,
            top=shared.game_region.top + indent.top,
            width=indent.width,
            height=indent.height
        ))
        # frame = np.array(self.sct.grab({
        #     "left": shared.game_region.left + constants.CENTER.x - indent // 2,
        #     "top": shared.game_region.top + constants.CENTER.y - indent // 2,
        #     "width": indent,
        #     "height": indent
        # }))[:, :, :3]
        # scaled_frame = frame[
        #                shared.target.x - indent:shared.target.x + indent,
        #                shared.target.y - indent:shared.target.y + indent
        #                ][::downscale, ::downscale, :].copy()

        # TODO: Group mask groups of pixels work when there are multiple targets, or target targets with text names

        # mask = cv2.inRange(frame, utils.rgb(69, 163, 255), utils.rgb(69, 163, 255))
        display.show_image("optimized_targeting_mask", frame, initial_pos=tp.Pos(500, 815), auto_focus=True)
        # template_img = self.target_template_mask
        # result = cv2.matchTemplate(mask, template_img, cv2.TM_CCOEFF_NORMED)
        # _, max_val, _, max_loc = cv2.minMaxLoc(result)

        self._detect_hit_marker(frame, indent)

        if shared.hit_marker:
            # frame_mono = frame[:, :, 2]
            target = self._match_unclear_target(frame[:, :, :3])
        else:
            downscale = 2
            scaled_frame = frame[::downscale, ::downscale, :][:, :, :3].copy()
            scaled_mask = cv2.inRange(scaled_frame, utils.rgb(255, 50, 50), utils.rgb(255, 50, 50))
            target = self._match_clear_target(frame, scaled_mask, downscale)
        # target = self._indentify_target(mask)
        # logger.info(f"target: {target}")
        if target:
            # cv2.putText(scaled_mask, f"{shared.target}", (shared.target.x // downscale, shared.target.y // downscale), cv2.FONT_HERSHEY_SIMPLEX, 0.3, utils.gray(200), 1)
            # logger.info(f"target: {shared.target}")

            target = tp.Pos(
                indent.left + target.x,
                indent.top + target.y,
            )
        shared.target = target

    def _full_targeting(self):
        """Locate the target on the entire game frame"""

        frame = utils.get_mss_frame(shared.game_region)
        if not utils.is_valid_array(frame):
            logger.warn("Failed to update the game frame.")
            shared.target = None
            return

        """Get whole frame and mask out bad areas"""

        downscale = 5

        # scaled_frame = frame[::downscale, ::downscale, :][:, :, :3].copy()
        scaled_frame = frame[::downscale, ::downscale, :][:, :, :3].copy()
        scaled_mask = cv2.inRange(scaled_frame, utils.rgb(255, 50, 50), utils.rgb(255, 50, 50))
        scaled_mask[682 // downscale:1034 // downscale, 1522 // downscale:1874 // downscale] = 100  # minimap
        scaled_mask[545 // downscale:690 // downscale, 55 // downscale:400 // downscale] = 100  # game logs
        scaled_mask[20 // downscale:240 // downscale, 1835 // downscale:1980 // downscale] = 100  # enemy players score
        scaled_mask[18 // downscale:60 // downscale, 1027 // downscale:1160 // downscale] = 100  # enemy team score
        # mask[916 // downscale:970 // downscale, 960 // 2 // downscale:(960 + 960 // 2) // downscale] = 100  # weapon info

        # h, w = mask.shape  # TODO: Use this to find the closest point to the center faster
        # tl_mask = mask[:h // 2, :w // 2]
        # tr_mask = mask[:h // 2, w // 2:]
        # bl_mask = mask[h // 2:, :w // 2]
        # br_mask = mask[h // 2:, w // 2:]
        #
        # nonzero_indices = np.flatnonzero(mask == 255)
        # if nonzero_indices.size > 0:
        #     # The first element corresponds to the top-most (smallest y) pixel in row-major order
        #     y, x = np.unravel_index(nonzero_indices[0], mask.shape)

        target = self._match_clear_target(frame, scaled_mask, downscale)

        if target:
            cv2.putText(scaled_mask, f"{target}", (target.x // downscale, target.y // downscale), cv2.FONT_HERSHEY_SIMPLEX, 0.3, utils.gray(200), 1)
        shared.target = target
        # logger.info(f"target: {target}")

    def process(self):
        if shared.aiming_state:
            center_aim_area: tp.Area = tp.Area(
                constants.CENTER.x,
                constants.CENTER.y,
                constants.CENTER.x,
                constants.CENTER.y,
            ).expand(100)

            # display.write_text(f"target: {shared.target}", tp.Pos(8, 5))

            old_target = shared.target
            if old_target and center_aim_area.contains(old_target.x, old_target.y):
                # logger.info("Target is close to the center")
                self._localized_targeting()
            else:
                full_targeting_cooldown = 0.5
                if self.call_time - self.last_full_targeting_time > full_targeting_cooldown or old_target:
                    self.last_full_targeting_time = time.time()
                    self._full_targeting()

            display.write_text(f"target: {shared.target}", tp.Pos(6, 6))

    @staticmethod
    @utils.require_game_focus
    def hotkey_toggle_aiming_state():
        if shared.aiming_state:
            ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)  # left mouse button up

        shared.aiming_state = not shared.aiming_state
        logger.info(f"Aiming state: {shared.aiming_state}")

    def start_event_loop(self):
        def thread():
            while True:
                shared.targeter_event.wait()
                self.process()
                # utils.measure_func(self.run_process)
                shared.targeter_event.clear()

        return threading.Thread(target=thread, daemon=True).start()

    def trigger_processing(self):
        """Call the process from main thread without blocking it."""
        self.call_time = time.time()
        # self.shared = shared.snapshot(self.call_time)
        shared.targeter_event.set()


processor = TargeterProcessor()
