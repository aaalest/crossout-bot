# Running the modified A* algorithm again after the execution state reset
import heapq
from math import sqrt
from scipy.sparse import csr_matrix
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from .wall_cache import WallCache


# New heuristic function
def heuristic(node, start, end):
    dx1 = node[0] - end[0]
    dy1 = node[1] - end[1]
    dx2 = start[0] - end[0]
    dy2 = start[1] - end[1]
    cross = abs(dx1 * dy2 - dx2 * dy1)

    dx3 = abs(dx1)
    dy3 = abs(dy1)

    return 5 + (cross * 0.01) * (dx3 + dy3) + (sqrt(2) - 2) * min(dx3, dy3)


# Move cost function
def move_cost(current, node):
    cross = abs(current[0] - node[0]) == 1 and abs(current[1] - node[1]) == 1
    return 7 if cross else 5


def wall_penalty(current, node, wall_cache, multiplier=1):
    return wall_cache.wall_cache.get(current, 0) * multiplier


def manhattan_distance(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def get_neighbors(cell, grid):
    neighbors = []
    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        x, y = cell[0] + dx, cell[1] + dy
        if 0 <= x < len(grid) and 0 <= y < len(grid[0]):
            neighbors.append((x, y))
    return neighbors


# sharp_movement_penalty optimized with bitwise operations
def sharp_movement_penalty(current, node, parent):
    penalty = 0
    if parent:
        dx1, dy1 = current[0] - parent[0], current[1] - parent[1]
        dx2, dy2 = node[0] - current[0], node[1] - current[1]

        # Check if the movement direction is the same
        if (dx1, dy1) == (dx2, dy2):
            penalty += 0.1

    return penalty


def smooth_a_star(grid, start, end):
    wall_cache = WallCache()
    wall_cache.initialize_wall_cache(grid)

    open_list = []
    heapq.heappush(open_list, (0, start))

    g_costs = {start: 0}
    f_costs = {start: manhattan_distance(start, end)}
    parents = {start: None}

    while open_list:
        _, current = heapq.heappop(open_list)

        if current == end:
            path = []
            while current:
                path.insert(0, current)
                current = parents[current]
            return path

        for neighbor in get_neighbors(current, grid):
            if grid[neighbor[0]][neighbor[1]] == 1:
                continue

            tentative_g_cost = g_costs[current] + 1 + wall_penalty(current, neighbor, wall_cache)

            if tentative_g_cost < g_costs.get(neighbor, float('inf')):
                parents[neighbor] = current
                g_costs[neighbor] = tentative_g_cost
                f_costs[neighbor] = tentative_g_cost + manhattan_distance(neighbor, end)
                f_costs[neighbor] += sharp_movement_penalty(current, neighbor, parents.get(current, None))

                if neighbor not in [item[1] for item in open_list]:
                    heapq.heappush(open_list, (f_costs[neighbor], neighbor))
