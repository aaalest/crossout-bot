import keyboard

from readers import interface
from readers import map
from readers import window
from readers import lockon
from actions import camera
from actions import steering
from actions import throttle
import pathing

from toolbox import constants, custom_types as tp, utils
from toolbox.display import display
from toolbox.shared import shared
from toolbox.logger import logger


def activate():
    keyboard.on_release_key('3', lambda _: pathing.processor.hotkey_flip_pathing_state())
    keyboard.on_release_key('5', lambda _: lockon.processor.hotkey_toggle_aiming_state())
    keyboard.on_release_key('7', lambda _: camera.processor.hotkey_center_camera())
    keyboard.on_release_key('9', lambda _: camera.processor.hotkey_reset_camera_origin())
    # keyboard.on_release_key('0', lambda _: self.take_screenshot())

    keyboard.add_hotkey('ctrl+s', lambda: pathing.processor.hotkey_save_grid())
    keyboard.add_hotkey('shift+s', lambda: display.hotkey_save_data())
