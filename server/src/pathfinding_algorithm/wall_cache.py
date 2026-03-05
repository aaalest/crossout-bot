import numpy as np
import heapq

class WallCache:
    def __init__(self):
        self.wall_cache = {}
        self.hash_cache = None

    def initialize_wall_cache(self, grid):
        new_hash = hash(str(grid))
        if new_hash == self.hash_cache:
            return

        self.hash_cache = new_hash
        self.wall_cache = {}

        for x in range(len(grid)):
            for y in range(len(grid[0])):
                wall_count = 0
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < len(grid) and 0 <= ny < len(grid[0]) and grid[nx][ny] == 1:
                        wall_count += 1
                self.wall_cache[(x, y)] = wall_count