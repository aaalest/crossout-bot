from typing import List, Optional, TypedDict, Literal, Union

import numpy as np
from pydantic import BaseModel, conint, confloat, validator, field_validator
from dataclasses import is_dataclass, dataclass, asdict, field
import json
from enum import Enum, auto
from datetime import datetime


# classes for Server and Client

class CalculationFailError(Exception):
    pass


@dataclass
class ScreenArea:
    left: int
    top: int
    width: int
    height: int


@dataclass
class Position:
    x: int | float
    y: int | float


@dataclass
class PlayerLandPosition:
    x: int | float
    y: int | float
    yaw: int | float
    speed: int | float = 0


@dataclass
class P3DPosition:  # Pixel 3D position
    """
    P3DPosition is a type that represents a 3D pixel based on position in the game
    """
    x: conint(ge=-2244, le=2244)
    y: conint(ge=-1003, le=1003)


@dataclass
class TargetEntity:
    x: float
    y: float
    x3d: float
    y3d: float


@dataclass
class Area:
    x1: float | int
    y1: float | int
    x2: float | int
    y2: float | int


class LandMarkType(Enum):
    obstacle = auto()
    nothing = auto()
    dynamic_obstacle = auto()
    dynamic_entry = auto()


@dataclass
class LandMapData:
    map_px_size: int
    px2m_ratio: float
    grid: np.array
    dynamic_obstacles: Optional[List[np.ndarray]] = field(default_factory=list)

    def m2px(self, meters: float | int) -> float:
        return meters * self.m2px_ratio

    def px2m(self, pixels: float | int) -> float:
        return pixels / self.m2px_ratio


class LandMaps(Enum):
    garage = auto()
    old_town = auto()
    # naukograd = auto()


@dataclass
class LandMapsData:
    garage: LandMapData
    old_town: LandMapData
    # naukograd: LandMapData


@dataclass
class LandGameStatus:
    map: LandMaps
    enemy_capsules: int
    ally_capsules: int


class Menu(Enum):
    unknown = auto()
    main = auto()
    main_queuing_for_battle = auto()
    world_map = auto()
    world_map_queuing_for_battle = auto()
    finished_battle = auto()
    battle_spectate_ally = auto()
    battle_spectate_enemy = auto()
    esc_menu = auto()
    battle = auto()
    blueprints = auto()
    error = auto()
    network_error = auto()
    unsportsmanlike_error = auto()
    disconnected_from_game_session_error = auto()
    login = auto()


@dataclass
class LandMovementInput:
    player_position: PlayerLandPosition
    player_p3d_camera: P3DPosition
    game_status: LandGameStatus
    enemies_data: Optional[List[Position]] = None
    allies_data: Optional[List[Position]] = None


movement_input_example = LandMovementInput(
    player_position=PlayerLandPosition(x=0, y=0, yaw=0),
    player_p3d_camera=P3DPosition(x=0, y=0),
    game_status=LandGameStatus(
        map=LandMaps.garage,
        enemy_capsules=10,
        ally_capsules=5
    )
)


@dataclass
class LandMovementOutput:
    goal_position: Position
    target_enemy: Optional[Position] = None


@dataclass
class MarkLandPointInput:
    point_position: Position
    mark_type: LandMarkType
    map_type: LandMaps


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
