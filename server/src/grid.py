import time
import re
import asyncio
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.websockets import WebSocketDisconnect
import numpy as np
from enum import Enum, auto
import cv2
from typing import get_args
import json
import os

from logger import logger
import custom_types as tp
# from a_star import a_star, get_furthest_point, visualize_path
# from a_star import a_star, get_furthest_point
# from pathfinding_algorithm.a_star_again import a_star, get_furthest_point
# from pathfinding_algorithm.a_star_again2 import a_star, get_furthest_point
from path import a_star, get_furthest_point


class Manager:
    def __init__(self):
        # fill MapsData with data
        maps_data = {}
        for map_obj in tp.LandMaps:
            if not os.path.exists(rf'scr/maps/land/{map_obj.name}'):
                logger.error(f'Could not find map folder: maps/land/{map_obj.name}')
                continue

            grid = cv2.imread(f'scr/maps/land/{map_obj.name}/grid.png')
            if grid is None:
                raise logger.error(f'Could not open map {map_obj.name}.png')
            elif grid.shape[0] != grid.shape[1]:
                logger.error(f'Grid for {map_obj.name} is not square, shape: {grid.shape}')
                continue

            dynamic_obstacles: list[np.ndarray] = []
            for file in os.listdir(f'scr/maps/land/{map_obj.name}'):
                if file.endswith('.png') and file != 'grid.png' and file[:16] == 'dynamic_obstacle':
                    dynamic_obstacles.append(cv2.imread(f'scr/maps/land/{map_obj.name}/{file}'))

            # open data.json as dict
            with open(f'scr/maps/land/{map_obj.name}/data.json', 'r') as f:
                dict_data = json.load(f)
            print(dict_data)

            maps_data[str(map_obj.name)] = {
                "map_px_size": grid.shape[0],
                "px2m_ratio": dict_data["px2m_ratio"],
                "grid": grid,
                "dynamic_obstacles": dynamic_obstacles
            }
        for name, data in maps_data.items():
            logger.info(f'{name}: {data["map_px_size"]}, {data["grid"].shape}, {len(data["dynamic_obstacles"])}')
        # logger.info(f'maps_data: {maps_data}')
        land_maps_data: dict = {}
        for map_name in maps_data:
            land_maps_data[map_name] = tp.LandMapData(
                map_px_size=maps_data[map_name]["map_px_size"],
                px2m_ratio=maps_data[map_name]["px2m_ratio"],
                grid=maps_data[map_name]["grid"],
                dynamic_obstacles=maps_data[map_name]["dynamic_obstacles"]
            )

        self.land_maps_data: tp.LandMapsData = tp.LandMapsData(**land_maps_data)


    def calculate_land_actions(self, movement_input: tp.LandMovementInput) -> tp.LandMovementOutput | None:
        input = movement_input
        map_obj = input.game_status.map
        grid = getattr(self.land_maps_data, map_obj.name).grid
        gray_grid = cv2.cvtColor(grid, cv2.COLOR_BGR2GRAY)
        _, binary_grid = cv2.threshold(gray_grid, 1, 1, cv2.THRESH_BINARY)

        # expand all

        start = (int(input.player_position.x), int(input.player_position.y))
        closest = None
        # goal = (146, 128)
        # goal = (63, 96)
        goal = (83, 164)

        # if data.enemies_data is None:
        #     # goal = (int(data.player_position.x), int(data.player_position.y))
        #     # goal = (83, 164)
        # else:
        #     closest = {
        #         "enemy": data.enemies_data[0],
        #         "distance": np.sqrt((data.enemies_data[0].x - start[0]) ** 2 + (data.enemies_data[0].y - start[1]) ** 2)
        #     }
        #     for enemy in data.enemies_data:
        #         distance = np.sqrt((enemy.x - start[0]) ** 2 + (enemy.y - start[1]) ** 2)
        #         if distance < closest["distance"]:
        #             if binary_grid[int(enemy.y), int(enemy.x)] == 1:
        #                 continue
        #             closest["enemy"] = enemy
        #             closest["distance"] = distance
        #
        #     closest_enemy = (int(closest["enemy"].x), int(closest["enemy"].y))
        #     enemy_direction = np.arctan2(closest_enemy[1] - start[1], closest_enemy[0] - start[0])
        #     enemy_direction = np.degrees(enemy_direction)
        #     # set goal to be 10 units in front of the enemy
        #     goal = (
        #         int(closest_enemy[0] + 10 * np.cos(np.radians(enemy_direction))),
        #         int(closest_enemy[1] + 10 * np.sin(np.radians(enemy_direction)))
        #     )

        show_grid = cv2.bitwise_not(grid.copy())
        cv2.circle(show_grid, start, 2, (0, 255, 0)[::-1], -1)
        cv2.circle(show_grid, goal, 2, (255, 0, 255)[::-1], -1)
        path = a_star(binary_grid, (start[1], start[0]), (goal[1], goal[0]), input)
        if not path:
            self.show_grid = show_grid.copy()
            raise tp.CalculationFailError('Could not find path')

        # target_point = get_furthest_point(binary_grid, path)
        try:
            target_point = path[10]
        except IndexError:
            target_point = path[-1]
        # draw path on red_map_img
        for (x, y) in path:
            show_grid[x, y] = [255, 0, 0]
        cv2.circle(show_grid, (target_point[1], target_point[0]), 2, (255, 0, 0)[::-1], -1)
        self.show_grid = show_grid.copy()
        # cv2.imshow('show_grid', cv2.resize(show_grid, (0, 0), fx=1.5, fy=1.5, interpolation=cv2.INTER_AREA)) if show_grid is not None else None
        # cv2.waitKey(1)

        logger.info(f'Path: {path}')
        return tp.LandMovementOutput(
            goal_position=tp.Position(x=target_point[1], y=target_point[0]),  # TODO: add yaw
            target_enemy=None if closest is None else closest["enemy"]
        )


    def show_grid_loop(self):
        while True:
            if self.land_movement_input is None:
                time.sleep(0.1)
                continue
            input = self.land_movement_input
            show_map = self.land_maps_data[input.game_status.map]["img"].copy()
            # show_map *= 255
            # Convert floating-point coordinates to integers
            player_x = int(input.player_data.x)
            player_y = int(input.player_data.y)
            # Draw 2 purple lines that represent player location using integer coordinates
            cv2.line(show_map, (player_x, 0), (player_x, show_map.shape[0]), (255, 0, 255), 1)
            cv2.line(show_map, (0, player_y), (show_map.shape[1], player_y), (255, 0, 255), 1)
            cv2.imshow(input.game_status.Map, show_map) if show_map is not None else None

            # show red map

            show_map = self.land_maps_data[input.game_status.map]["img"].copy()
            cv2.imshow('show_grid', var.show_grid) if var.show_grid is not None else None
            cv2.imshow('show_grid', cv2.resize(var.show_grid, (0, 0), fx=2, fy=2, interpolation=cv2.INTER_AREA)) if var.show_grid is not None else None
            cv2.waitKey(1)


    # def calculate_air_actions(var: shared.Variables):
    #     data = var.heli_movement_input
    #     map_name = data.game_status.map
    #     map_img = var.maps_data[map_name.name]["img"]
    #     # keep only red color chanel
    #     red_map_img = map_img[:, :, 2]
    #     # keep only pixels that are > 150
    #     _, red_map_img = cv2.threshold(red_map_img, data.player_data.z, 1, cv2.THRESH_BINARY)
    #     logger.info(f'data.player_data.z: {data.player_data.z}')
    #     # inverse
    #     red_map_img = 1 - red_map_img
    #     # var.red_map_img = red_map_img.copy()
    #     # logger.info(f'red_map_img: {red_map_img.shape}, max: {np.max(red_map_img)}, min: {np.min(red_map_img)}')
    #     if data.player_data is None or data.enemies_data is None:
    #         logger.info(f'Player data or enemies data is not full, {data.player_data}, {data.enemies_data}')
    #         return {"path": None}
    #     start = (int(data.player_data.x), int(data.player_data.y))
    #     # start = (0, 0)
    #     goal = (int(data.enemies_data[0].x), int(data.enemies_data[0].y))
    #     show_red_map = cv2.cvtColor(red_map_img.copy() * 255, cv2.COLOR_GRAY2BGR)
    #     cv2.circle(show_red_map, start, 5, (0, 0, 255)[::-1], -1)
    #     cv2.circle(show_red_map, goal, 5, (0, 255, 0)[::-1], -1)
    #     path = a_star(red_map_img, (start[1], start[0]), (goal[1], goal[0]))  # red_map_img.T - send flipped map because of the way it is read
    #     logger.info(f'Path: {path}')
    #     if path:
    #         # path = path.reverse()
    #         # path = [(y, x) for (x, y) in path]
    #         furthest_point = get_furthest_point(red_map_img, path)
    #         # furthest_point = (furthest_point[1], furthest_point[0])
    #         # reverse
    #         # draw path on red_map_img
    #         for (x, y) in path:
    #             show_red_map[x, y] = [255, 0, 0]
    #         cv2.circle(show_red_map, (furthest_point[1], furthest_point[0]), 5, (255, 0, 0)[::-1], -1)
    #     var.show_red_map = show_red_map
    #
    #
    #
    #     # start = (int(data.player_data.x), int(data.player_data.y))
    #     # end = (int(data.checkpoint_data.x), int(data.checkpoint_data.y))
    #     # path = a_star(map_img, start, end)
    #     # logger.info(f'Path: {path}')
    #     return path


    # def mark_land_point(img: np.ndarray, pos: tp.PlayerLandPositionalData, mark_type: tp.LandMarkType) -> np.ndarray:
    #     logger.info(f'Marking point {pos.x}, {pos.y}, mark_type: {mark_type}')
    #     if mark_type == tp.LandMarkType.obstacle:
    #         img[pos.y, pos.x] = (255, 255, 255)[::-1]
    #     elif mark_type == tp.LandMarkType.nothing:
    #         img[pos.y, pos.x] = (0, 0, 0)[::-1]
    #         # logger.info(img[pos.y, pos.x])
    #         # logger.info(f'Result: {img[pos.y, pos.x]}')
    #     return img


    def mark_land_point(self, mark_point_input: tp.MarkLandPointInput):
        logger.info(f'Marking point {mark_point_input.player_data.x}, {mark_point_input.player_data.y}, '
                    f'mark_type: {mark_point_input.mark_type}, map: {mark_point_input.map_type}')
        img = getattr(self.land_maps_data, mark_point_input.map_type.name).grid
        if mark_point_input.mark_type == tp.LandMarkType.obstacle:
            img[mark_point_input.player_data.y, mark_point_input.player_data.x] = (255, 255, 255)[::-1]
        elif mark_point_input.mark_type == tp.LandMarkType.nothing:
            img[mark_point_input.player_data.y, mark_point_input.player_data.x] = (0, 0, 0)[::-1]
            # logger.info(img[pos.y, pos.x])
            # logger.info(f'Result: {img[pos.y, pos.x]}')


    def save_land_map(self, map_obj: tp.LandMaps):
        map_name = map_obj.name
        img = getattr(self.land_maps_data, map_name).grid

        # if maps is the same don't do anything
        if np.array_equal(img, cv2.imread(f'maps/land/{map_name}/grid.png')):
            return

        # backup
        formated_time = time.strftime("%Y-%m-%d_%H-%M-%S", time.gmtime())
        old_img = cv2.imread(f'maps/land/{map_name}/grid.png')
        cv2.imwrite(f'maps/land/{map_name}/grid_backup{formated_time}.png', old_img)

        cv2.imwrite(f'maps/land/{map_name}/grid.png', img)
        # return {"status": "ok", "map_type": map_name}


manager = Manager()

