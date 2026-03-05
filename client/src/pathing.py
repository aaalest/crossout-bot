import time
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
import numpy as np
import keyboard

from actions import steering
from actions import throttle

from toolbox import constants, custom_types as tp, utils
from toolbox.display import display
from toolbox.shared import shared
from toolbox.logger import logger

from scipy.ndimage import sobel
import scipy

from heapq import heappush, heappop
import time


def load_map(filename):
    img = cv2.imread(filename, cv2.IMREAD_GRAYSCALE)
    return img


def is_valid(p, grid):
    x, y = p
    return 0 <= x < grid.shape[1] and 0 <= y < grid.shape[0]


def neighbors(p):
    x, y = p
    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, -1), (-1, 1), (1, 1)]:
        yield (x + dx, y + dy)


def greedy_bfs(grid, start: Tuple[int, int], goal: Tuple[int, int]) -> List[Tuple[int, int]]:
    if start is None or goal is None:
        logger.warn("[greedy_bfs] Error: start or goal is None")
        return []

    h = lambda a: np.linalg.norm(np.array(a) - np.array(goal))
    visited = set()
    prev = {}
    queue = []
    heappush(queue, (h(start), start))

    while queue:
        _, current = heappop(queue)
        if current == goal:
            break
        if current in visited:
            continue
        visited.add(current)
        for n in neighbors(current):
            if not is_valid(n, grid):
                continue
            if grid[n[1], n[0]] >= 255:
                continue
            if n not in visited:
                prev[n] = current
                heappush(queue, (h(n), n))

    # Reconstruct path
    path = []
    p = goal
    while p != start:
        path.append(p)
        if p in prev:
            p = prev[p]
        else:
            logger.warn("[greedy_bfs] Error: path reconstruction failed (no path)")
            return []  # No path found
    path.append(start)
    path.reverse()
    return path


def line_of_sight(grid, a, b):
    """Bresenham-like LOS"""
    x0, y0 = a
    x1, y1 = b
    points = []
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    x, y = x0, y0
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    while True:
        if grid[y, x] >= 255:
            return False
        points.append((x, y))
        if (x, y) == (x1, y1): break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x += sx
        if e2 < dx:
            err += dx
            y += sy
    return True


def furthest_visible(path, current, grid):
    for i in reversed(range(len(path))):
        if line_of_sight(grid, current, path[i]):
            return path[i]
    return path[0]


def near_wall(p, grid):
    x, y = p
    for nx, ny in neighbors((x, y)):
        if is_valid((nx, ny), grid) and grid[ny, nx] == 255:
            return True
    return False


def sample_line(a, b):
    """Bresenham-style line from point a to b"""
    x0, y0 = a
    x1, y1 = b
    points = []
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    x, y = x0, y0
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    while True:
        points.append((x, y))
        if (x, y) == (x1, y1): break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x += sx
        if e2 < dx:
            err += dx
            y += sy
    return points


def get_drive_point(start_point, furthest_point):
    start_point = np.array(start_point)
    soft_grid = constants.MAPS[shared.map_type].soft_grid
    circle_pixels = constants.MAPS[shared.map_type].circle_pixels
    furthest_point_angle = np.arctan2(
        furthest_point[1] - start_point[1],
        furthest_point[0] - start_point[0]
    )
    furthest_point_angle = np.degrees(furthest_point_angle)
    lowest_cost_circle_point = {
        "x": None,
        "y": None,
        "cost": None,
    }
    for circle_point in circle_pixels:
        point = circle_point + start_point
        # logger.info(f"circle_point: {circle_point}, start_point: {start_point}")
        circle_point_angle = np.arctan2(
            point[1] - start_point[1],
            point[0] - start_point[0]
        )
        circle_point_angle = np.degrees(circle_point_angle)
        # angle_price = abs(circle_point_angle - furthest_point_angle) ** 1.1
        # angle_price = abs(circle_point_angle - furthest_point_angle)
        # angle_price = abs((circle_point_angle - furthest_point_angle + 180) % 360 - 180)
        # angle_price = abs(((circle_point_angle - furthest_point_angle + 180) % 360) - 180)
        a, b = circle_point_angle, furthest_point_angle
        angle_price = min(abs(b - a) % 360, 360 - abs(b - a) % 360)
        wall_price = soft_grid[point[1], point[0]]
        # angle_price = abs(furthest_point_angle - circle_point_angle)
        # wall_price = soft_grid[point[1], point[0]]
        # wall_price = 0
        # angle_price = angle_price ** 1.2
        wall_price = wall_price * 1.2
        cost = angle_price + wall_price
        # if wall_price == 0:
        #     print(f"angle_price: {angle_price:.2f}, wall_price: {wall_price:.2f}, cost: {cost:.2f}, point: {point}, furthest_point_angle: {furthest_point_angle:.2f}, circle_point_angle: {circle_point_angle:.2f}")
        if lowest_cost_circle_point["cost"] is None or cost < lowest_cost_circle_point["cost"]:
            lowest_cost_circle_point["x"] = point[0]
            lowest_cost_circle_point["y"] = point[1]
            lowest_cost_circle_point["cost"] = cost
            display.write_text(f"angle_price: {angle_price:.2f}, wall_price: {wall_price:.2f}", tp.Pos(0, 8))
    # time.sleep(0.2)
    if lowest_cost_circle_point["x"] is None or lowest_cost_circle_point["y"] is None:
        logger.error("No valid circle point found")
        return None
    # print(f"Lowest cost circle point: {lowest_cost_circle_point}")
    return tp.Pos(
        lowest_cost_circle_point["x"],
        lowest_cost_circle_point["y"]
    )


class PathingProcessor:
    def __init__(self):
        self.call_time = 0

    @staticmethod
    def get_goal() -> Optional[Tuple[int, int]]:
        if not shared.enemies:
            return

        if not shared.is_target_accurate and shared.target is not None:
            # if target is not accurate, predict 3 pixels forward, as a goal
            distance: tp.Pixel = utils.px2m(3)
            angle_offset = constants.CENTER.x - shared.target.x
            angle = shared.player.yaw - angle_offset / 2
            goal = (
                int(shared.player.x + np.cos(np.radians(angle)) * distance),
                int(shared.player.y + np.sin(np.radians(angle)) * distance)
            )
        elif shared.looking_at_enemy:
            if shared.looking_at_enemy.distance < 10:
                # if looking at enemy and distance is less than 10, use it as goal
                goal = None
            else:
                goal = (
                    int(shared.looking_at_enemy.x),
                    int(shared.looking_at_enemy.y)
                )
        else:
            # sort enemies based on distance to player
            start = [shared.player.x, shared.player.y]
            sorted_enemies = sorted(
                shared.enemies,
                key=lambda e: np.linalg.norm(np.array((e.x, e.y)) - np.array(start))
            )
            closest_enemy = sorted_enemies[0]
            goal = (int(closest_enemy.x), int(closest_enemy.y))
        # goal = (274, 196)
        # goal = (274, 236)
        # goal = (114, 306)
        # goal = (163, 123)
        return goal

    def process(self):
        if shared.map_type is None or shared.player.x is None:
            logger.info("Map not loaded")
            return
        if not shared.pathing_state:
            return

        grid = constants.MAPS[shared.map_type].grid
        soft_grid = constants.MAPS[shared.map_type].soft_grid
        circle_pixels = constants.MAPS[shared.map_type].circle_pixels
        show_grid = cv2.cvtColor(soft_grid, cv2.COLOR_GRAY2RGB)

        start = (shared.player.x, shared.player.y)
        goal = self.get_goal()
        if goal is None:
            logger.info("No goal")
            return

        cv2.circle(show_grid, goal, 2, utils.rgb(255, 0, 0), -1)
        display.write_text(f"goal: {goal}", tp.Pos(0, 7))

        path = greedy_bfs(grid, start, goal)
        # logger.info(f"Path planning time: {(time.time() - now) * 1000} ms")
        # if not path:
        #     logger.info("No path found.")

        # driven_path = simulate_drive(grid, path, start)

        for p in path:
            show_grid[p[1], p[0]] = utils.rgb(255, 0, 0)
        # for p in driven_path:
        #     show_grid[p[1], p[0]] = utils.rgb(0, 255, 0)

        if path:
            furthest_point = furthest_visible(path, start, grid)
            cv2.circle(show_grid, furthest_point, 2, utils.rgb(0, 255, 0), -1)
            drive_point = get_drive_point(start, furthest_point)
            if drive_point:
                show_grid[drive_point.y, drive_point.x] = utils.rgb(0, 0, 255)
                # draw a circle around the drive point
                for pixel in circle_pixels:
                    x = pixel[0] + start[0]
                    y = pixel[1] + start[1]
                    show_grid[y, x] = utils.rgb(0, 100, 100)
                cv2.line(show_grid, (start[0], start[1]), (drive_point.x, drive_point.y), utils.rgb(0, 255, 0), 1)
                drive_point_angle = np.degrees(np.arctan2(
                    drive_point.y - start[1],
                    drive_point.x - start[0]
                ))
                # logger.info(f"drive_point_angle: {drive_point_angle:.2f}, car yaw: {shared.player.yaw:.2f}")
                # diff with car yaw
                shared.goal_angle = drive_point_angle

                steering.processor.trigger_processing()
                throttle.processor.trigger_processing()

                # cv2.circle(show_grid, (drive_point.x, drive_point.y), 10, utils.rgb(0, 0, 255), 1)
            # drive_path = simulate_drive_path(soft_grid, path, start)
            # for p in drive_path:
            #     show_grid[p[1], p[0]] = utils.rgb(0, 255, 0)
        show_grid = cv2.resize(show_grid, (0, 0), fx=3, fy=3, interpolation=cv2.INTER_NEAREST)
        display.show_image("driven_path", show_grid, tp.Pos(2560, 770), auto_focus=True)
        # if shared.pathing_state:
        #     # display.write_text(f"target: {shared.target}", tp.Pos(8, 5))
        #     # self._full_targeting()
        #
        #     display.write_text(f"path: {shared.target}", tp.Pos(0, 6))

    @staticmethod
    def mark_point():
        x, y = shared.player
        constants.MAPS[shared.map_type].grid[y, x] = tp.MarkType.NOTHING.value

    def _save_grid(self):
        map_name = shared.map_type.name
        # rename grid.png to grid_{time}
        time_formatted = datetime.now().strftime("%y-%m-%d_%H-%M-%S")
        os.rename(fr"assets/maps/{map_name}/grid.png", fr"assets/maps/{map_name}/grid_{time_formatted}.png")
        save_img = cv2.cvtColor(constants.MAPS[shared.map_type].grid, cv2.COLOR_GRAY2RGB)
        cv2.imwrite(fr"assets/maps/{map_name}/grid.png", save_img)
        logger.info(f"Saved drivable mask, created backup grid_{time_formatted}.png")

    @staticmethod
    @utils.require_game_focus
    def hotkey_flip_pathing_state():
        logger.info(f"Before toggle: shared.pathing_state = {shared.pathing_state}")
        if shared.pathing_state:
            keyboard.release('w')
            keyboard.release('s')
            keyboard.release('a')
            keyboard.release('d')

        shared.pathing_state = not shared.pathing_state
        logger.info(f"After toggle: shared.pathing_state = {shared.pathing_state}")

    @utils.require_game_focus
    def hotkey_save_grid(self):
        self._save_grid()

    def start_event_loop(self):
        def thread():
            while True:
                shared.pathing_event.wait()
                self.process()
                # utils.measure_func(self.run_process)
                shared.pathing_event.clear()

        return threading.Thread(target=thread, daemon=True).start()

    def trigger_processing(self):
        """Call the process from main thread without blocking it."""
        self.call_time = time.time()
        # self.shared = shared.snapshot(self.call_time)
        shared.pathing_event.set()


processor = PathingProcessor()

# async def calculate_path(var: shared.Variables):
#     # start = (int(var.grid_map.player_y_pos), int(var.grid_map.player_x_pos))
#     # end = (int(var.grid_map.checkpoint_y_pos), int(var.grid_map.checkpoint_x_pos))
#     data = {
#         "start": (0, 0),
#         "end": (0, 0),
#     }
#     await var.websocket.send(json.dumps(data))
#     response = await var.websocket.recv()
#     grid_data = json.loads(response)
#     print(f"Received grid data: {grid_data}")
#     # try:
#     #     await var.websocket.send(data)
#     #     path = await var.websocket.recv()
#     # except Exception as e:
#     #     logger.exception(e)
#     #     await create_ws_session(var)
#     #     return
#
#     # var.path = ast.literal_eval(path)
#     logger.log('Received path from server')


# class Grid:
#     def __init__(self):
#         movement_input: Optional[tp.LandMovementInput] = None
#         movement_output: Optional[tp.LandMovementOutput] = None

# async def mark_level(var: shared.Variables, mark_point_input: tp.MarkLandPointInput):
#     if var.movement_input is None:
#         logger.error('Player data is not full')
#         return
#     metadata = {
#         "mark_point_input": tp.encode(mark_point_input)
#     }
#
#     data = aiohttp.FormData()
#     data.add_field('metadata', json.dumps(metadata))
#
#     async with aiohttp.ClientSession() as session:
#         async with session.post(f'http://{var.server_address}/mark_car_point', data=data) as response:
#             response_metadata = json.loads(response.headers.get("metadata"))
#     # response_get = requests.get(f'http://{var.server_address}/mark_car_point', data=data)
#     logger.info(f'response: {response_metadata}')
#     # var.grid_map[int(var.grid_player_x_pos)][int(var.grid_player_y_pos)] = (255, 255, 255)[::-1]
#     # logger.info(f'Marked nothing at {var.grid_player_x_pos}, {var.grid_player_y_pos}')
#
#
# async def save_car_map(var: shared.Variables):
#     data = aiohttp.FormData()
#     data.add_field('metadata', json.dumps({
#         "map_obj": tp.encode(var.movement_input.game_status.map)
#     }))
#
#     async with aiohttp.ClientSession() as session:
#         async with session.post(f'http://{var.server_address}/save_car_map', data=data) as response:
#             response_metadata = json.loads(response.headers.get("metadata"))
#     logger.info(f'save_car_map response_metadata: {response_metadata}')
#
#
# def png_to_grid(grid, include_rocks=True) -> np.ndarray:
#     nothing_color = (255, 255, 255)[::-1]
#     rock_color = (255, 255, 0)[::-1]
#     obstacle_color = (0, 255, 255)[::-1]
#     wall_color = (0, 0, 0)[::-1]
#     checkpoint_color = (255, 0, 0)[::-1]
#
#     if include_rocks:
#         grid[np.all(grid == rock_color, axis=-1)] = wall_color
#     else:
#         grid[np.all(grid == rock_color, axis=-1)] = nothing_color
#     grid[np.all(grid == obstacle_color, axis=-1)] = wall_color
#     grid[np.all(grid == checkpoint_color, axis=-1)] = nothing_color
#
#     # Convert all pixels > 127 to 255 and all pixels <= 127 to 0
#     mask = cv.inRange(grid, (0, 0, 0), (127, 127, 127))
#     grid[mask != 0] = 1
#     grid[mask == 0] = 0
#     grid = grid[:, :, :1]  # convert from RGB to grayscale
#     grid = grid.astype(float)
#
#     return grid
#
#
# def img_to_grid(img, include_rocks=True, include_obstacles=True):
#     nothing_color = (255, 255, 255)[::-1]
#     rock_color = (255, 255, 0)[::-1]
#     obstacle_color = (0, 255, 255)[::-1]
#     wall_color = (0, 0, 0)[::-1]
#     checkpoint_color = (255, 0, 0)[::-1]
#
#     # mask out all checkpoint pixels
#     mask = np.all(img == checkpoint_color, axis=-1)
#     # go through all pixels and check if pixels around it are rock pixels paint them into nothing pixels
#     for x in range(img.shape[0]):
#         for y in range(img.shape[1]):
#             if mask[x][y]:
#                 for i in range(-1, 2):
#                     for j in range(-1, 2):
#                         if x + i < 0 or y + j < 0 or x + i >= img.shape[0] or y + j >= img.shape[1]:
#                             continue
#                         if np.all(img[x + i][y + j] == rock_color) or np.all(img[x + i][y + j] == obstacle_color):
#                             img[x + i][y + j] = nothing_color
#
#     # Prepare object colors to binary colors
#     if include_rocks:
#         img[np.all(img == rock_color, axis=-1)] = wall_color
#     else:
#         img[np.all(img == rock_color, axis=-1)] = nothing_color
#     if include_obstacles:
#         img[np.all(img == obstacle_color, axis=-1)] = wall_color
#     else:
#         img[np.all(img == obstacle_color, axis=-1)] = nothing_color
#     img[np.all(img == checkpoint_color, axis=-1)] = nothing_color
#
#     # Convert image to binary grid
#     img = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
#     _, img = cv.threshold(img, 127, 255, cv.THRESH_BINARY)
#     grid = np.array(img)
#     grid = np.where(grid == 0, 1, 0)
#     grid = np.flip(grid, axis=0)
#     return grid
#
#
# def show_grid_loop(var: shared.Variables):
#     scale = 5
#     while True:
#         # Make sure to update grid and player positions somewhere in your code
#         bigger_grid = cv.resize(var.grid_map, (0, 0), fx=scale, fy=scale, interpolation=cv.INTER_NEAREST)
#         circle_pos = (int(var.grid_player_x_pos * scale), int(abs(var.grid_player_y_pos - 100) * scale))
#         cv.circle(bigger_grid, circle_pos, scale, (0, 255, 0), -1)
#         cv.imshow('grid', bigger_grid)
#         cv.waitKey(1)

#
# def show_grid_loop(var: shared.Variables):
#     while True:
#         print(f'show_path_thread: grid: {var.grid_map}, path: {var.grid_path}, start: {var.grid_start}, end: {var.grid_end}, other_paths: {var.grid_other_paths}')
#
#         # try:
#         if var.grid_map.all():
#             #print(f'var.grid.all() is True, skipping show_path_thread')
#             continue
#
#         grid = np.flip(var.grid_map, axis=0)
#         plt.clf()  # Clear the current figure
#
#         # Plot grid
#         plt.imshow(grid, cgrid='gray_r', extent=[0, 100, 0, 100])
#
#         # try:
#         #     # move window to the x - 1310, y - 100
#         #     # get plt.get_current_fig_manager().window position
#         #     x, y, _, _ = plt.get_current_fig_manager().window.geometry().getRect()
#         #     print(f'x: {x}, y: {y}')
#         #     if x != -2610 or y != 200:
#         #         print(f'Moving window to -2610, 200')
#         #         plt.get_current_fig_manager().window.wm_geometry("-2610+200")
#         # except AttributeError as e:
#         #     if 'FigureManagerInterAgg' in str(e):
#         #         print(f'Failed to move window: {e}, turn off Python Scientific mode. Pycharm: Settings -> Tools -> Python Scientific -> Uncheck "Show plots in toolwindow"')
#
#         # Zoom into the grid
#         plt.xlim(0, 100)
#         plt.ylim(0, 100)
#
#         # Plot start and end points
#         if var.grid_start:
#             plt.scatter(var.grid_start[1], var.grid_start[0], c='blue', label='Start', zorder=10)
#         if var.grid_end:
#             plt.scatter(var.grid_end[1], var.grid_end[0], c='red', label='End', zorder=10)
#
#         # Plot original path
#         if var.grid_path:
#             path_x, path_y = zip(*var.grid_path)
#             plt.plot(path_y, path_x, c='orange', label='Original Path', linewidth=2)
#
#         # Plot smoothed path
#         try:
#             if var.grid_other_paths:
#                 for other_path in var.grid_other_paths:
#                     path_x, path_y = zip(*other_path)
#                     colors = ['green', 'purple', 'brown', 'pink', 'gray', 'olive', 'cyan']
#                     plt.plot(path_y, path_x, c=colors[var.grid_other_paths.index(other_path)], label=f'path_{var.grid_other_paths.index(other_path)}', linewidth=2)
#         except ValueError:
#             pass
#
#         plt.legend(loc='upper left') if any([var.grid_start, var.grid_end, var.grid_path]) else None
#         plt.grid(True, which='both', linestyle='--', linewidth=0.5)
#         ax = plt.gca()
#         np_grid = np.array(grid)
#         ax.set_xticks(np.arange(-0.5, np_grid.shape[1], 1))
#         ax.set_yticks(np.arange(-0.5, np_grid.shape[0], 1))
#         ax.set_xticklabels([])
#         ax.set_yticklabels([])
#
#         plt.pause(0.01)
#         # ticks += 1
#         # except Exception as e:
#         #     print(f'Failed to show path: {e}')
