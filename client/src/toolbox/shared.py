from dataclasses import dataclass, fields, field
from enum import Enum, auto
from typing import Optional, List, Tuple, Any, Union, Dict
import numpy as np
import threading
import mss
import dxcam
import time

from toolbox import constants, custom_types as tp
from toolbox.logger import logger


# @dataclass
# class Shared:


@dataclass
class Shared:
    # Bot data
    bot_running: bool = True
    game_hwnd: int = 0
    game_title: str = ""
    game_focused: bool = False
    game_region: tp.Region = None

    # Game data
    px2m_ratio: float = 2.5026217228464422  # TODO: update this value based on current map

    # Player data
    player = tp.Player()
    camera: tp.Camera = field(default_factory=lambda: tp.Camera(0, 0))
    camera_angle: int = 0

    # Other entities
    enemies: List[tp.Entity] = field(default_factory=list)
    allies: List[tp.Entity] = field(default_factory=list)

    # Lock-on
    looking_at_enemy: Optional[tp.Entity] = None
    is_target_accurate: bool = False
    aiming_state: bool = False
    target: tp.Pos = None
    target_time: float = 0
    hit_marker: bool = False

    # Pathing
    pathing_state: bool = False
    goal_angle: float = 0.0  # Desired vehicle angle in degrees

    # Events
    mapper_event = threading.Event()
    targeter_event = threading.Event()
    camera_event = threading.Event()
    pathing_event = threading.Event()
    steering_event = threading.Event()
    throttle_event = threading.Event()
    interface_event = threading.Event()
    display_event = threading.Event()

    # Interface
    menu: tp.Menu = tp.Menu(0)
    map: tp.Map = None
    map_type: Optional[tp.Map] = None
    map_img: Optional[np.ndarray] = None

    # Utils
    scts: Dict[str, mss.mss] = field(default_factory=dict)
    dxcam_camera: Optional[dxcam] = None

    # deprecated
    map_layers: Dict[str, np.ndarray] = field(default_factory=lambda: {
        "name": "map",
        "shape": (364, 364, 4)
    })

    @staticmethod
    def attr_to_str(attr) -> str:
        """Convert a dataclass attribute to its string name."""
        for field in fields(Shared):
            if getattr(Shared, field.name) is attr:
                return field.name
        raise ValueError(f"Attribute {attr} not found in Shared.")

    # # Internal fields (not part of the public interface)
    # _history: Dict[str, List[Tuple[float, Any]]] = field(default_factory=dict, init=False, repr=False)
    # _is_snapshot: bool = field(default=False, init=False, repr=False)
    # _snapshot_map: Optional[Dict[str, int]] = field(default=None, init=False, repr=False)
    # # For live instances, track active snapshots in a list.
    # _active_snapshots: List["Shared"] = field(default_factory=list, init=False, repr=False)
    # # For snapshot instances, store a reference to the live instance.
    # _parent: Optional["Shared"] = field(default=None, init=False, repr=False)
    # max_history_length: int = 10  # Default value, can be overridden.
    #
    # def __setattr__(self, attribute_name, value):
    #     # In snapshot mode or during initialization, set normally.
    #     if attribute_name.startswith('_') or '_history' not in self.__dict__ or self.__dict__.get('_is_snapshot', False):
    #         object.__setattr__(self, attribute_name, value)
    #     else:
    #         current_ts = time.time()
    #         # Record change in history.
    #         if attribute_name not in self._history:
    #             self._history[attribute_name] = []
    #         self._history[attribute_name].append((current_ts, value))
    #         object.__setattr__(self, attribute_name, value)
    #         # Trim history for this attribute.
    #         self._trim_history(attribute_name)
    #
    # def _trim_history(self, attr: str):
    #     """Trim the history for a given attribute if possible."""
    #     history_list = self._history.get(attr, [])
    #     current_length = len(history_list)
    #     desired_removals = current_length - self.max_history_length
    #     if desired_removals <= 0:
    #         return
    #
    #     # Determine the minimum index still needed by any active snapshot.
    #     min_active_index = current_length  # default: no snapshot uses older entries.
    #     for snapshot in self._active_snapshots:
    #         if snapshot._snapshot_map and attr in snapshot._snapshot_map:
    #             snap_index = snapshot._snapshot_map[attr]
    #             if snap_index < min_active_index:
    #                 min_active_index = snap_index
    #
    #     allowed_removals = min(desired_removals, min_active_index)
    #     if allowed_removals > 0:
    #         del history_list[:allowed_removals]
    #         # Update each snapshot's index for this attribute.
    #         for snapshot in self._active_snapshots:
    #             if snapshot._snapshot_map and attr in snapshot._snapshot_map:
    #                 snapshot._snapshot_map[attr] -= allowed_removals
    #
    # def __getattribute__(self, attribute_name):
    #     # Always return internal attributes immediately.
    #     if attribute_name.startswith('_'):
    #         return object.__getattribute__(self, attribute_name)
    #
    #     # If this is a snapshot, check the snapshot map first.
    #     if object.__getattribute__(self, '_is_snapshot'):
    #         snapshot_map = object.__getattribute__(self, '_snapshot_map')
    #         history = object.__getattribute__(self, '_history')
    #         if snapshot_map and attribute_name in snapshot_map:
    #             index = snapshot_map[attribute_name]
    #             return history[attribute_name][index][1]
    #         # If not found in snapshot map, raise an error (you can adjust this as needed).
    #         raise AttributeError(
    #             f"No historical record for attribute '{attribute_name}' at snapshot time"
    #         )
    #
    #     # In live mode, return the regular attribute.
    #     return object.__getattribute__(self, attribute_name)
    #
    # def snapshot(self, snapshot_ts: float) -> 'Shared':
    #     """Return a snapshot of the current state, preserving history entries needed by the snapshot."""
    #     snapshot_map: Dict[str, int] = {}
    #     for attr, records in self._history.items():
    #         last_index = -1
    #         for index, (ts, _) in enumerate(records):
    #             if ts <= snapshot_ts:
    #                 last_index = index
    #             else:
    #                 break
    #         if last_index != -1:
    #             snapshot_map[attr] = last_index
    #
    #     snapshot_instance = Shared(max_history_length=self.max_history_length)
    #     snapshot_instance._is_snapshot = True
    #     snapshot_instance._history = self._history  # share history
    #     snapshot_instance._snapshot_map = snapshot_map
    #     snapshot_instance._parent = self
    #     # Add snapshot to the active snapshots list.
    #     self._active_snapshots.append(snapshot_instance)
    #     return snapshot_instance
    #
    # def release(self):
    #     """Release a snapshot so that its required history can be trimmed."""
    #     if self._is_snapshot and self._parent is not None:
    #         # Remove self from the parent's active snapshots list.
    #         if self in self._parent._active_snapshots:
    #             self._parent._active_snapshots.remove(self)
    #         self._parent = None


shared = Shared()


# shared = Shared(max_history_length=3)
# shared.frame_time = 5
# shared_ = shared.snapshot(time.time())
# shared.frame_time = 10
# print(shared_.frame_time)  # prints 0, should be 5

# shape = (10800, 19200, 3)
# shared = Shared(max_history_length=10)
# shared.age = 5  # Records age = 5 with timestamp.
# shared_ = shared.snapshot(time.time())
# shared.frame = np.zeros(shape, dtype=np.uint8)
# for i in range(50):
#     shared.frame = np.zeros(shape, dtype=np.uint8)
# shared_.release()
# shared_ = shared.snapshot(time.time())
# shared.frame = np.ones(shape, dtype=np.uint8)
# shared.age = 10  # Later update to age.
# print(shared_.age)  # prints 5


