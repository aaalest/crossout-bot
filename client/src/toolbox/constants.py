import cv2
import numpy as np
from dataclasses import dataclass, fields, field
from enum import Enum, auto
from typing import Optional, List, Tuple, Any, Union, Dict
import os

from toolbox import custom_types as tp
from toolbox.shared import shared
from toolbox.logger import logger


# Constants
GAME_TITLE_PREFIX = "Crossout 2."
GAME_WIDTH = 1920
GAME_HEIGHT = 1080
CENTER: tp.Pos = tp.Pos(GAME_WIDTH // 2, GAME_HEIGHT // 2)
FPS = 60


def load_images(path: str, obj: Enum | Any) -> Dict[str, np.ndarray]:
    images: Dict[str, np.ndarray] = {}
    for image_obj in obj:
        image = cv2.imread(rf"{path}/{image_obj.name}.png", cv2.IMREAD_UNCHANGED)
        if image is None:
            raise FileNotFoundError(f"Image {image_obj.name} of {obj.__name__} not found.")
        images[image_obj.name] = image
    logger.info(f"Loaded images for {obj.__name__} from {path}")
    return images


MAP_IMAGES = load_images("assets/maps", tp.Map)
MENU_IMAGES = load_images("assets/menus", tp.Menu)

MAPS: Dict[tp.Map, tp.MapData] = {
    tp.Map.GARAGE: tp.MapData(
        tp.Map.GARAGE, px2m_ratio=2.5026217228464422
    )
}
