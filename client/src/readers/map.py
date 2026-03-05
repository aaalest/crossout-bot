import random
import threading
import time
import asyncio
import numpy as np
import cv2
import math
import mss
from typing import Optional, List, Tuple, Any, Union, Dict
from line_profiler import LineProfiler

from toolbox import constants, utils, custom_types as tp
from toolbox.display import display
from toolbox.shared import shared
from toolbox.logger import logger

import pathing
from readers import interface


class MapperProcessor:
    def __init__(self):
        self.call_time = 0
        self.latest_frame_time = 0  # Shared variable for the latest frame time
        self.consumed_frames = 0
        self.map_type: Optional[tp.Map] = None
        self.source_map_gray: np.array = None
        self.latest_frame_time = 0
        self.expand_map_border_by = 0

        self.speedometer_numbers = []
        for i in range(10):
            img = cv2.imread(rf"assets/speedometer/{i}.png")[:, :, 0]
            # img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            _, img = cv2.threshold(img, 254, 255, cv2.THRESH_BINARY)
            self.speedometer_numbers.append(img)

        # self.target_template = cv2.cvtColor(cv2.imread(r'assets/images/target.png'), cv2.COLOR_BGR2GRAY)

    @staticmethod
    def _get_entities_pos(minimap_img: np.array, map_img: np.array,
                          lower_bound: np.array, upper_bound: np.array) -> List[tp.Entity]:
        entities_mask = cv2.inRange(minimap_img, lower_bound, upper_bound)
        map_center = tp.Pos(x=map_img.shape[0] // 2, y=map_img.shape[1] // 2)
        minimap_center = tp.Pos(x=minimap_img.shape[0] // 2, y=minimap_img.shape[1] // 2)
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(entities_mask, connectivity=8)
        player = shared.player

        entities = []
        for i in range(1, num_labels):  # Start from 1 to skip the background
            # if stats[i, cv2.CC_STAT_AREA] <= 5:  # Consider components with at least 5 pixels
            #     continue
            entity = tp.Entity(x=float(centroids[i][0]), y=float(centroids[i][1]))
            entity.x = entity.x + player.x - minimap_center.x
            entity.y = entity.y + player.y - minimap_center.y
            entity.distance = ((entity.x - player.x) ** 2 + (entity.y - player.y) ** 2) ** 0.5
            entity.distance = round(entity.distance, 2)
            entity.angle2player = math.degrees(math.atan2(entity.y - player.y, entity.x - player.x))
            entity.angle2player = round(entity.angle2player, 2)
            entities.append(entity)

        false_positive_area = tp.Area(x1=119, y1=217, x2=135, y2=234).expand(3)
        entities = [entity for entity in entities if not (false_positive_area.contains(entity.x, entity.y))]
        return entities

    def _find_player_on_minimap(self, template_img):
        """
        Find player on minimap using template matching.
        """
        source_img = self.source_map_gray
        template_center = tp.Pos(x=template_img.shape[0] // 2, y=template_img.shape[1] // 2)

        zoomed_source_img = source_img
        source_img_show = source_img.copy()
        offset_used = tp.Pos(x=0, y=0)
        if None not in (shared.player.x, shared.player.y):
            # optimization: zoom into the player position on source_img
            area = tp.Area(
                x1=self.expand_map_border_by + shared.player.x - template_center.x,
                y1=self.expand_map_border_by + shared.player.y - template_center.y,
                x2=self.expand_map_border_by + shared.player.x + template_center.x,
                y2=self.expand_map_border_by + shared.player.y + template_center.y
            ).expand(10)
            offset_used = tp.Pos(x=area.x1, y=area.y1)
            cv2.rectangle(source_img_show, (area.x1, area.y1), (area.x2, area.y2), utils.gray(255), 1)
            zoomed_source_img = source_img[
                                area.y1:area.y2,
                                area.x1:area.x2
                                ]
            if zoomed_source_img.shape[0] != zoomed_source_img.shape[1]:
                zoomed_source_img = None

        threshold = 0.5
        if zoomed_source_img is not None:
            result = cv2.matchTemplate(zoomed_source_img, template_img, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)
        else:
            max_val = 0
            max_loc = (0, 0)
            offset_used = tp.Pos(x=0, y=0)

        if max_val < threshold:  # try to match on the whole image
            result = cv2.matchTemplate(source_img, template_img, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)

        display.write_text(f"max_loc: {max_loc}", tp.Pos(5, 2))
        display.write_text(f"{round(max_val, 3)}", tp.Pos(21, 0))
        display.write_text(f"offset_used: {offset_used}", tp.Pos(5, 1))

        if max_val < threshold:
            shared.player.x = None
            shared.player.y = None
            return

        shared.player.x = max_loc[0] + offset_used.x - self.expand_map_border_by + template_center.x
        shared.player.y = max_loc[1] + offset_used.y - self.expand_map_border_by + template_center.y

        cv2.circle(source_img_show, (shared.player.x + self.expand_map_border_by, shared.player.y + self.expand_map_border_by), 3, utils.gray(255), -1)
        # display.show_image("source_img_show", source_img_show, initial_pos=tp.Pos(0, 420), auto_focus=True)

    @staticmethod
    def _calc_what_enemy_looking_at():
        """
        Calculate what enemy is looking at
        """
        aligned_enemy: Optional[tp.Entity] = None
        aligned_enemy_diff_angle = 180
        for enemy in shared.enemies:
            angle_diff = enemy.angle2player - shared.camera.yaw
            if abs(aligned_enemy_diff_angle) > abs(angle_diff):
                aligned_enemy = enemy
                aligned_enemy_diff_angle = angle_diff
        if abs(aligned_enemy_diff_angle) > 5 or aligned_enemy is None:
            shared.looking_at_enemy = None
            return
        # display.write_text(f"aligned_enemy: {aligned_enemy.angle2player}", tp.Pos(0, 3))
        shared.looking_at_enemy = aligned_enemy

    def _read_speedometer(self, speedometer_img: np.array):
        _, speedometer_mask = cv2.threshold(speedometer_img, 254, 255, cv2.THRESH_BINARY)
        img_numbers = [
            speedometer_mask[:, 0:13],
            speedometer_mask[:, 13:26],
            speedometer_mask[:, 26:39],
        ]

        speedometer_result = ""
        for img_number in img_numbers:
            for i, speedometer_number in enumerate(self.speedometer_numbers):
                if (img_number == speedometer_number).all():
                    speedometer_result = f"{speedometer_result}{i}"
        if speedometer_result == "":
            logger.warning(f"Failed to read speedometer")
            return
        shared.player.speed = int(speedometer_result)

    def process(self):
        if shared.map_img is None:
            return

        """Capture minimap and speedometer"""

        frame = utils.get_mss_frame(tp.Region(
            top=shared.game_region.top + 682,
            left=shared.game_region.left + 1517,
            width=357,
            height=352
        ))

        if not utils.is_valid_array(frame):
            shared.menu = tp.Menu(0)
            return
        # display.show_image("frame", frame, initial_pos=tp.Pos(0, 0), auto_focus=True)
        interface.processor.classify_menu(frame, "BATTLE", x_offset=-1517, y_offset=-682)

        # frame = np.array(self.sct.grab({
        #     "top": shared.game_region.top + 682,
        #     "left": shared.game_region.left + 1517,
        #     "width": 357,
        #     "height": 352
        # }))
        speedometer_img = cv2.copyMakeBorder(
            frame[331:346, :38, 0].copy(), 0, 0, 0, 1, cv2.BORDER_CONSTANT, 0
        )
        minimap_img = frame[:, 5:, :3]

        if self.map_type != shared.map_type:  # update source_map_gray
            self.map_type = shared.map_type
            source_map_gray = shared.map_img[:, :, 2].copy()
            self.expand_map_border_by = int(source_map_gray.shape[0] * 0.25)
            source_map_gray = cv2.copyMakeBorder(
                source_map_gray,  # source image
                self.expand_map_border_by,  # top
                self.expand_map_border_by,  # bottom
                self.expand_map_border_by,  # left
                self.expand_map_border_by,  # right
                cv2.BORDER_CONSTANT, 0, value=utils.gray(52)  # borderType, value
            )
            self.source_map_gray = source_map_gray
        if self.source_map_gray is None:
            return

        # map_layer = np.zeros(shared.map_layers["shape"], dtype=np.uint8)
        map_layer = shared.map_img.copy()
        # game_layer = np.zeros(shared.game_layers["shape"], dtype=np.uint8)
        player = shared.player

        """Get minimap direction"""

        minimap_center = tp.Pos(x=minimap_img.shape[0] // 2, y=minimap_img.shape[1] // 2)
        minimap_direction_mask = np.full_like(minimap_img, 0)
        cv2.circle(
            minimap_direction_mask,
            (minimap_direction_mask.shape[1] // 2, minimap_direction_mask.shape[0] // 2),
            179, utils.gray(255), -1
        )
        cv2.circle(
            minimap_direction_mask,
            (minimap_direction_mask.shape[1] // 2, minimap_direction_mask.shape[0] // 2),
            173, utils.gray(0), -1
        )
        minimap_direction_mask = minimap_direction_mask[:, :, 0]
        _, minimap_direction_mask = cv2.threshold(minimap_direction_mask, 127, 255, cv2.THRESH_BINARY)
        # cv2.waitKey(0)
        # apply mask to minimap_direction_img
        # minimap_direction_img = cv2.cvtColor(minimap_direction_img, cv2.COLOR_BGR2GRAY)

        minimap_direction_img = minimap_img[:, :, 0]
        minimap_direction_img = cv2.bitwise_and(minimap_direction_img, minimap_direction_img, mask=minimap_direction_mask)

        # apply threshold to minimap_direction_img
        minimap_direction_img = cv2.threshold(minimap_direction_img, 254, 255, cv2.THRESH_BINARY)[1]
        # display.show_image("minimap_direction_img", minimap_direction_img, initial_pos=tp.Pos(0, 780), auto_focus=True)
        # get average pos of white pixels
        non_zero_points = cv2.findNonZero(minimap_direction_img)
        if non_zero_points is None:
            logger.warn("Failed to find minimap direction")
            return

        average_pos = np.mean(non_zero_points, axis=0)[0]
        angle = np.arctan2(average_pos[1] - minimap_center.x, average_pos[0] - minimap_center.y)
        minimap_direction = np.degrees(angle)
        shifted_angle = utils.shift_angle(-minimap_direction, 180)
        player.yaw = round(shifted_angle, 2)

        # TODO: improve map entities detection

        # minimap_mask = cv2.inRange(minimap_img, utils.gray(0), utils.gray(20))
        #
        # # Apply corner detection with the same parameters
        # corners = cv2.goodFeaturesToTrack(
        #     minimap_mask,
        #     maxCorners=10,
        #     qualityLevel=0.1,
        #     minDistance=1
        # )
        #
        # minimap_show = cv2.cvtColor(minimap_mask.copy(), cv2.COLOR_GRAY2RGB) // 2
        #
        # if corners is not None:
        #     corners = np.intp(corners)
        #     for i in corners:
        #         x, y = i.ravel()
        #         cv2.circle(minimap_show, (x, y), 1, utils.rgb(255, 0, 0), -1)
        # display.show_image("minimap_img_corners", minimap_show, initial_pos=tp.Pos(25, 1150), auto_focus=True)

        """Find player on minimap"""

        minimap_img = utils.rotate_image(minimap_img, minimap_direction + 90)

        # cut minimap_img by 25% from all sides
        cut_scale = 0.25
        minimap_gray = minimap_img[
                       int(minimap_img.shape[0] * cut_scale): -int(minimap_img.shape[0] * cut_scale),
                       int(minimap_img.shape[1] * cut_scale): -int(minimap_img.shape[1] * cut_scale)
                       ][:, :, 2]
        display.show_image("minimap_img", minimap_gray, initial_pos=tp.Pos(0, 780), auto_focus=True)

        self._find_player_on_minimap(minimap_gray)
        if player.x is None or player.y is None:
            logger.warning(f"Failed to find player on minimap")
            return

        cv2.circle(map_layer, (player.x, player.y), 3, utils.rgb(0, 255, 255), -1)

        line_length = 10
        line_end = (player.x + int(line_length * math.cos(math.radians(player.yaw))),
                    player.y + int(line_length * math.sin(math.radians(player.yaw))))
        cv2.line(map_layer, (player.x, player.y), line_end, utils.rgb(255, 0, 255), 1)  # player line

        # line_length = 100
        # line_end = (player.x + int(line_length * math.cos(math.radians(shared.camera.yaw))),
        #             player.y + int(line_length * math.sin(math.radians(shared.camera.yaw))))
        # cv2.line(map_layer, (player.x, player.y), line_end, utils.rgb(0, 255, 255), 1)  # camera line

        self._read_speedometer(speedometer_img)

        """Get minimap enemy and ally positions"""

        shared.enemies = self._get_entities_pos(
            minimap_img, map_layer,
            lower_bound=utils.rgb(200, 30, 30),
            upper_bound=utils.rgb(255, 51, 51),
        )
        self._calc_what_enemy_looking_at()
        for enemy in shared.enemies:
            cv2.circle(map_layer, (int(enemy.x), int(enemy.y)), 2, utils.rgb(255, 100, 100), -1)
            cv2.line(map_layer, (player.x, player.y), (int(enemy.x), int(enemy.y)), utils.rgb(255, 100, 100), 1)
            # cv2.putText(map_layer, f"{int(enemy.distance)}", (int(enemy.x), int(enemy.y)), cv2.FONT_HERSHEY_SIMPLEX, 0.35, utils.rgb(255, 220, 220), 1, cv2.LINE_AA)
            cv2.putText(map_layer, f"{enemy.angle2player}", (int(enemy.x), int(enemy.y)), cv2.FONT_HERSHEY_SIMPLEX, 0.35, utils.rgb(255, 220, 220), 1, cv2.LINE_AA)

        if shared.looking_at_enemy:
            cv2.line(map_layer, (player.x, player.y), (int(shared.looking_at_enemy.x), int(shared.looking_at_enemy.y)), utils.rgb(255, 255, 0), 1)

        shared.allies = self._get_entities_pos(
            minimap_img, map_layer,
            lower_bound=utils.rgb(45, 100, 140),
            upper_bound=utils.rgb(75, 170, 255),
        )

        for ally in shared.allies:
            cv2.circle(map_layer, (int(ally.x), int(ally.y)), 2, utils.rgb(100, 100, 255), -1)
            cv2.line(map_layer, (player.x, player.y), (int(ally.x), int(ally.y)), utils.rgb(100, 100, 255), 1)
            cv2.putText(map_layer, f"{int(ally.distance)}", (int(ally.x), int(ally.y)), cv2.FONT_HERSHEY_SIMPLEX, 0.35, utils.rgb(220, 220, 255), 1, cv2.LINE_AA)

        display.show_image("map_layer", map_layer, initial_pos=tp.Pos(0, 0), auto_focus=True)
        display.write_text(f"{player}", tp.Pos(0, 0))

        """Pathing"""

        middle_mouse_state = utils.key_state(0x04)
        if middle_mouse_state:
            pathing.processor.mark_point()
        # display.show_image("drivable_mask", constants.MAPS[shared.map].drivable_mask, tp.Pos(0, 0), auto_focus=True)

    def start_event_loop(self):
        def thread():
            while True:
                shared.mapper_event.wait()
                self.process()
                # utils.measure_func(self.process)
                shared.mapper_event.clear()

        return threading.Thread(target=thread, daemon=True).start()

    def trigger_processing(self):
        """Call the process from main thread without blocking it."""
        self.call_time = time.time()
        shared.mapper_event.set()


processor = MapperProcessor()
