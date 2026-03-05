from typing import List, Optional, TypedDict, Literal, Union, TYPE_CHECKING, Tuple

import numpy as np
from pydantic import BaseModel, conint, confloat, validator, field_validator
from dataclasses import is_dataclass, dataclass, asdict, field
import json
from enum import Flag, IntFlag, Enum, auto
from datetime import datetime
from pathlib import Path
import cv2

import scipy

if TYPE_CHECKING:  # Only imported for type hinting
    from toolbox.shared import shared

Meter = int | float
Pixel = int | float


def map_number(number: float, in_min: float, in_max: float, out_min: float, out_max: float) -> float:
    return (number - in_min) * (out_max - out_min) / (in_max - in_min) + out_min


def shift_angle(angle: float, offset: float) -> float:
    return ((angle + offset + 180) % 360) - 180


def wrap_to_range(value: int, min_val: int, max_val: int) -> int:
    span = max_val - min_val + 1
    return ((value - min_val) % span) + min_val


# classes for Server and Client

class CalculationFailError(Exception):
    pass


# @dataclass
# class Dist:
#     """
#     Stores distance in pixels and provides conversion to meters.
#     """
#     px: float = 0.0
#     px2m_ratio: float = 1.206896551724138
# 
#     @property
#     def int(self) -> int:
#         return int(self)
# 
#     @property
#     def m(self) -> float:
#         return self.px * self.px2m_ratio
# 
#     @m.setter
#     def m(self, new_m: float):
#         self.px = new_m / self.px2m_ratio
# 
#     def __float__(self) -> float:
#         return self.px
# 
#     def __int__(self) -> int:
#         return int(self.px)
# 
#     def __index__(self) -> int:
#         return int(self.px)
# 
#     def __add__(self, other):
#         return Dist(self.px + float(Dist._to_px(other)), self.px2m_ratio)
# 
#     def __iadd__(self, other):
#         self.px += float(Dist._to_px(other))
#         return self
# 
#     def __sub__(self, other):
#         return Dist(self.px - float(Dist._to_px(other)), self.px2m_ratio)
# 
#     def __isub__(self, other):
#         self.px -= float(Dist._to_px(other))
#         return self
# 
#     def __mul__(self, other):
#         return Dist(self.px * float(other), self.px2m_ratio)
# 
#     def __imul__(self, other):
#         self.px *= float(other)
#         return self
# 
#     def __truediv__(self, other):
#         return Dist(self.px / float(other), self.px2m_ratio)
# 
#     def __itruediv__(self, other):
#         self.px /= float(other)
#         return self
# 
#     def __repr__(self) -> str:
#         return f"{round(self.px, 2)}px|{round(self.m, 2)}m"
# 
#     @staticmethod
#     def _to_px(value):
#         if isinstance(value, Dist):
#             return value.px
#         elif isinstance(value, (int, float)):
#             return value
#         else:
#             raise TypeError(f"Unsupported type for arithmetic with Dist: {type(value)}. Expected int, float, or Dist.")
# 
#     @classmethod
#     def from_m(cls, meters: float):
#         return cls(px=meters / cls.px2m_ratio)


# d = Dist.from_m(12.068965517241379)
# print(float(d))  # 12.068965517241379


@dataclass
class Region:
    left: int
    top: int
    width: int
    height: int

    def expand(self, size: int) -> "Region":
        return Region(
            self.left - size,
            self.top - size,
            self.width + size * 2,
            self.height + size * 2,
        )


@dataclass
class Area:
    x1: float | int
    y1: float | int
    x2: float | int
    y2: float | int

    def expand(self, size: float | int) -> "Area":
        return Area(
            self.x1 - size,
            self.y1 - size,
            self.x2 + size,
            self.y2 + size,
        )

    def contains(self, x, y) -> bool:
        return self.x1 <= x <= self.x2 and self.y1 <= y <= self.y2


@dataclass
class Pos:
    x: int | float
    y: int | float

    def __iter__(self):
        yield self.x
        yield self.y

    def np(self) -> np.ndarray:
        return np.array((self.x, self.y), dtype=np.float32)


@dataclass
class Entity:
    x: int | float = None
    y: int | float = None
    distance: float = None
    angle2player: float = None

    def __iter__(self):
        yield self.x
        yield self.y


@dataclass
class Player:
    x: int | float = None
    y: int | float = None
    yaw: int | float = None
    speed: int | float = None

    def __iter__(self):
        yield self.x
        yield self.y


@dataclass
class Camera:  # Pixel 3D position
    """
    Camera position in the game world.
    The x coordinate is wrapped to the range of -2244 to 2244.
    The y coordinate is wrapped to the range of -1003 to 1003.
    """
    x: int
    y: int

    @property
    def yaw(self) -> float:
        """
        The yaw is calculated based on the x to be in the range of -180 to 180 degrees.
        """
        mapped = map_number(self.x, -2244, 2244, -180, 180)
        shifted = shift_angle(mapped, -90)
        return round(shifted, 2)

    # def yaw(self) -> float:
    #     """
    #     Calculate the yaw angle based on the x coordinate.
    #     The yaw is calculated to be in the range of -180 to 180 degrees.
    #     """
    #     mapped = map_number(self.x, -2244, 2244, -180, 180)
    #     shifted = shift_angle(mapped, -90)
    #     return round(shifted, 2)

    def __post_init__(self):
        # Ensure values are wrapped once at creation
        self.x = self.x
        self.y = self.y

    def __setattr__(self, name, value):
        if name == "x":
            super().__setattr__(name, wrap_to_range(value, -2244, 2244))
        elif name == "y":
            super().__setattr__(name, wrap_to_range(value, -1003, 1003))
        else:
            super().__setattr__(name, value)


# camera = Camera(x=2244, y=1003)


class MarkType(Enum):
    OBSTACLE = 255
    NOTHING = 0
    # DYNAMIC_OBSTACLE = 100
    # DYNAMIC_ENTRY = 200


class Map(Enum):
    GARAGE = auto()
    # OLD_TOWN = auto()
    # NAUKOGRAD = auto()


def circle_pixel_indices(radius, thickness=1) -> list:
    """
    Simulate a cv2.circle() and return the pixel indices it would affect.
    """
    shape = (radius * 2 + thickness, radius * 2 + thickness)
    center = (shape[1] // 2, shape[0] // 2)  # center of the circle
    mask = np.zeros(shape, dtype=np.uint8)
    cv2.circle(mask, center, radius, (255,), thickness)
    # cv2.imshow("mask", mask)
    # cv2.waitKey(0)
    # cv2.destroyAllWindows()
    ys, xs = np.nonzero(mask)
    ys -= center[1]
    xs -= center[0]
    # return list(zip(xs, ys))
    return np.stack((xs, ys), axis=1)  # shape: (N, 2)


@dataclass
class MapData:
    map: Map
    px2m_ratio: float

    size: int = 0
    visual_image: Optional[np.ndarray] = None
    identity_mask: Optional[np.ndarray] = None
    grid: Optional[np.ndarray] = None
    soft_grid: Optional[np.ndarray] = None
    circle_pixels: Optional[List[Tuple[int, int]]] = None

    # dynamic_obstacles: List[np.ndarray] = field(default_factory=list)

    def __post_init__(self):
        self.visual_image = cv2.imread(rf"assets/maps/{self.map.name}/visual_image.png", cv2.IMREAD_UNCHANGED)
        if self.visual_image is None:
            raise FileNotFoundError(f"Image visual_image.png of map {self.map.name} not found.")

        self.size = self.visual_image.shape[0]

        self.identity_mask = cv2.imread(rf"assets/maps/{self.map.name}/identity_mask.png", cv2.IMREAD_UNCHANGED)
        if self.identity_mask is None:
            raise FileNotFoundError(f"Image identity_mask.png of map {self.map.name} not found.")
        self.identity_mask = self.identity_mask[:, :, 0]

        self.grid = cv2.imread(rf"assets/maps/{self.map.name}/grid.png", cv2.IMREAD_UNCHANGED)
        if self.grid is None:
            raise FileNotFoundError(f"Image grid.png of map {self.map.name} not found.")
        self.grid = self.grid[:, :, 0]

        # Soft grid
        obstacles = (self.grid == 255)
        dist_to_obstacle = scipy.ndimage.distance_transform_edt(~obstacles)
        max_soft_distance = 6  # affect up to x pixels from a wall
        soft_mask = (self.grid == 0) & (dist_to_obstacle <= max_soft_distance)
        soft_cost = np.zeros_like(self.grid)
        scaled_cost = (1 + (max_soft_distance - dist_to_obstacle)) * (101 / max_soft_distance)
        soft_cost[soft_mask] = scaled_cost[soft_mask].astype(np.uint8)
        self.soft_grid = np.where(soft_mask, soft_cost, self.grid)
        cv2.imwrite(rf"assets/maps/{self.map.name}/soft_grid.png", self.soft_grid)

        # array = np.zeros((100, 100), dtype=np.uint8)

        # self.circle_pixels = circle_pixel_indices(radius=6, thickness=4)
        self.circle_pixels = circle_pixel_indices(radius=10, thickness=1)

        # self.dynamic_obstacles = []
        # for i in range(1, 5):
        #     dynamic_obstacle = cv2.imread(rf"assets/maps/{self.map_name.name}/dynamic_obstacle_{i}.png", cv2.IMREAD_UNCHANGED)
        #     if dynamic_obstacle is None:
        #         break
        #     self.dynamic_obstacles.append(dynamic_obstacle[:, :, 0])


@dataclass
class GameStatus:
    map: Map
    enemy_score: int
    ally_score: int


class Menu(IntFlag):
    BATTLE = auto()
    MAIN = auto()
    QUEUING_FOR_BATTLE = auto()
    WORLD_MAP = auto()
    WORLD_MAP_QUEUING = auto()
    FINISHED_BATTLE = auto()
    # BATTLE_SPECTATE_ALLY = auto()
    # BATTLE_SPECTATE_ENEMY = auto()
    ESC = auto()
    # BLUEPRINTS = auto()
    # ERROR = auto()
    # NETWORK_ERROR = auto()
    # UNSPORTSMANLIKE_ERROR = auto()
    # DISCONNECTED_FROM_GAME = auto()
    # FAILED_TO_CONNECT = auto()
    LOGIN = auto()


# test = Menu(0)
# print(f"test: {test.name}, type: {type(test)}")
# menu = Menu.MAIN | Menu.QUEUING_FOR_BATTLE  # create IntFlag
# menu |= Menu.WORLD_MAP  # add IntFlag
# menu &= ~Menu.WORLD_MAP  # remove IntFlag
# print(f"menu: {menu.name}, type: {type(menu)}")
# if Menu.MAIN in menu:
#     print("MAIN in menu")


@dataclass
class ActionsInput:
    player_position: Player
    player_p3d_camera: Camera
    game_status: GameStatus
    enemies_data: Optional[List[Pos]] = None
    allies_data: Optional[List[Pos]] = None


@dataclass
class ActionsOutput:
    goal_position: Pos
    look_at: Optional[Pos] = None


@dataclass
class MarkPointInput:
    point_position: Pos
    mark_type: MarkType
    map_type: Map


def encode(obj):
    if isinstance(obj, Enum):
        return {"__enum__": f"{obj.__class__.__name__}.{obj.name}"}

    if is_dataclass(obj):
        return {f"__{obj.__class__.__name__}__": {k: encode(v) for k, v in vars(obj).items()}}

    if isinstance(obj, datetime):
        return {"__datetime__": obj.isoformat()}

    if isinstance(obj, np.ndarray):
        return {"__np_array__": {"array": obj.tolist(), "dtype": str(obj.dtype)}}

    if isinstance(obj, list):
        return [encode(i) for i in obj]
    if isinstance(obj, dict):
        return {k: encode(v) for k, v in obj.items()}

    return obj  # Base types (int, str, etc.) are returned as is


def decode(obj):
    if isinstance(obj, dict):
        if "__enum__" in obj:
            name, member = obj["__enum__"].split(".")
            enum_class = globals()[name]
            return enum_class[member]

        if "__datetime__" in obj:
            return datetime.fromisoformat(obj["__datetime__"])

        if "__np_array__" in obj:
            array_data = obj["__np_array__"]["array"]
            dtype = obj["__np_array__"]["dtype"]
            return np.array(array_data, dtype=dtype)

        for key in obj:
            if key.startswith("__") and key.endswith("__"):
                class_name = key.strip("__")
                cls = globals().get(class_name)
                if cls:
                    field_values = {k: decode(v) for k, v in obj[key].items()}
                    return cls(**field_values)

        return {k: decode(v) for k, v in obj.items()}

    if isinstance(obj, list):
        return [decode(i) for i in obj]

    return obj  # Base types are returned as is
