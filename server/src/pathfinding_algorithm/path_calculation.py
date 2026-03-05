from pathfinding_algorithm.smooth_a_star import smooth_a_star
from pathfinding_algorithm.simplify_path import simplify_path
import cv2 as cv
import numpy as np


class Grid():
    def __init__(self, path='grid.png'):
        self.img = self._open_grid_img(path)
        self.bitmap = self.img_to_bitmap(self.img, include_rocks=True, include_obstacles=True)
        self.clear_bitmap = self.img_to_bitmap(self.img, include_rocks=False, include_obstacles=False)

    def _open_grid_img(self, path):
        # load grid img
        img = cv.imread(path)
        img = cv.cvtColor(img, cv.COLOR_BGR2RGB)
        img = cv.cvtColor(img, cv.COLOR_RGB2BGR)

        # optimize color threshold
        img[img > 255 / 2] = 255
        img[img <= 255 / 2] = 0

        # backup grid
        # cv.imwrite(f'grid_backups//grid {time.strftime("%Y-%m-%d-%H-%M-%S")}.png', grid)

        return img

    def img_to_bitmap(self, img, include_rocks=True, include_obstacles=True):
        nothing_color = (255, 255, 255)[::-1]
        rock_color = (255, 255, 0)[::-1]
        obstacle_color = (0, 255, 255)[::-1]
        wall_color = (0, 0, 0)[::-1]
        checkpoint_color = (255, 0, 0)[::-1]

        # mask all checkpoint pixels
        mask = np.all(img == checkpoint_color, axis=-1)
        # if pixels around it are rock pixels paint them into nothing pixels
        for x in range(img.shape[0]):
            for y in range(img.shape[1]):
                if mask[x][y]:
                    for i in range(-1, 2):
                        for j in range(-1, 2):
                            if x + i < 0 or y + j < 0 or x + i >= img.shape[0] or y + j >= img.shape[1]:
                                continue
                            if np.all(img[x + i][y + j] == rock_color) or np.all(img[x + i][y + j] == obstacle_color):
                                img[x + i][y + j] = nothing_color

        # Prepare object colors to binary colors
        if include_rocks:
            img[np.all(img == rock_color, axis=-1)] = wall_color
        else:
            img[np.all(img == rock_color, axis=-1)] = nothing_color
        if include_obstacles:
            img[np.all(img == obstacle_color, axis=-1)] = wall_color
        else:
            img[np.all(img == obstacle_color, axis=-1)] = nothing_color
        img[np.all(img == checkpoint_color, axis=-1)] = nothing_color

        # Convert image to binary grid
        img = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
        _, img = cv.threshold(img, 127, 255, cv.THRESH_BINARY)
        grid = np.array(img)
        grid = np.where(grid == 0, 1, 0)
        grid = np.flip(grid, axis=0)

        return grid

    def calculate_path(self, start_x, start_y, end_x, end_y):
        start = (int(start_x), int(start_y))
        end = (int(end_x), int(end_y))

        path = smooth_a_star(self.bitmap, start, end)
        bitmap = self.bitmap
        if not path:
            path = smooth_a_star(self.clear_bitmap, start, end)
            bitmap = self.clear_bitmap
        # simplified_path = simplify_path(path, self.result_bitmap, 1)

        return path, bitmap
