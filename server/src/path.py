import numpy as np
from heapq import heappop, heappush
import cv2
from scr import custom_types as tp


def a_star(binary_grid, start, goal, movement_input: tp.LandMovementInput):
    def heuristic(a, b):
        # Manhattan distance heuristic
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def get_direction(prev, curr):
        return (curr[0] - prev[0], curr[1] - prev[1])

    def wall_penalty(node, grid, size=3):
        # Define the box range for the 5x5 area around the current node
        x, y = node
        min_x, max_x = max(0, x - size), min(grid.shape[0], x + size + 1)
        min_y, max_y = max(0, y - size), min(grid.shape[1], y + size + 1)

        # Extract the 5x5 area around the node and count the number of walls (1s)
        sub_grid = grid[min_x:max_x, min_y:max_y]
        penalty = np.sum(sub_grid)  # Count number of 1s (walls) in the 5x5 box
        return penalty

    # Initialize open and closed sets
    open_set = []
    heappush(open_set, (0, start, None))  # (f_score, position, previous direction)
    came_from = {}  # For path reconstruction

    # Initialize g_score and f_score
    g_score = np.full(binary_grid.shape, np.inf)
    g_score[start] = 0

    f_score = np.full(binary_grid.shape, np.inf)
    f_score[start] = heuristic(start, goal)

    while open_set:
        _, current, prev_direction = heappop(open_set)

        # If we reached the goal, reconstruct the path
        if current == goal:
            return reconstruct_path(came_from, current)

        # Mark the node as evaluated
        for neighbor in get_neighbors(binary_grid, current):
            current_direction = get_direction(current, neighbor)
            tentative_g_score = g_score[current] + 1

            # if game_data.enemies_data:
            #     enemy_penalty = 0
            #     for enemy in game_data.enemies_data:
            #         distance = heuristic(neighbor, (enemy.x, enemy.y))
            #         if distance < 5:
            #             enemy_penalty += 5 - distance  # The closer the enemy, the higher the penalty
            #     tentative_g_score += enemy_penalty

            if movement_input.allies_data:
                ally_penalty = 0
                for ally in movement_input.allies_data:
                    distance = heuristic(neighbor, (ally.x, ally.y))
                    # The closer the ally, the higher the penalty (to avoid collisions)
                    if distance < 5:
                        ally_penalty += 5 - distance
                    # If the ally is too far, apply a penalty
                    elif distance > 15:
                        ally_penalty += 1
                tentative_g_score += ally_penalty

            # Apply penalty if there is a change in direction
            tentative_g_score += 1 if prev_direction and current_direction != prev_direction else 0

            # Calculate wall penalty for being close to the wall
            tentative_g_score += wall_penalty(neighbor, binary_grid)

            if tentative_g_score < g_score[neighbor]:
                # This path to neighbor is better than any previous one
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g_score
                f_score[neighbor] = tentative_g_score + heuristic(neighbor, goal)
                if neighbor not in [i[1] for i in open_set]:
                    heappush(open_set, (f_score[neighbor], neighbor, current_direction))

    # No path found
    return []


def get_neighbors(grid, node):
    neighbors = []
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]  # Up, down, left, right

    for direction in directions:
        neighbor = (node[0] + direction[0], node[1] + direction[1])

        if (0 <= neighbor[0] < grid.shape[0] and 0 <= neighbor[1] < grid.shape[1]
                and grid[neighbor[0], neighbor[1]] == 0):  # Check if neighbor is not a wall
            neighbors.append(neighbor)

    return neighbors


def reconstruct_path(came_from, current):
    path = [current]
    while current in came_from:
        current = came_from[current]
        path.append(current)
    path.reverse()
    return path


def check_wall_intersection(x1: int, y1: int, x2: int, y2: int, grid: np.ndarray) -> bool:
    # fill the line with 0s
    line = grid.copy()
    line.fill(0)
    cv2.line(line, (y1, x1), (y2, x2), 1, 1)
    # invert line
    combined = cv2.bitwise_and(line, grid)

    # show_line_grid = line.copy() * 255
    # show_grid = grid.copy() * 255
    # combined = combined.copy() * 255
    # cv2.imshow("Line", show_line_grid)
    # cv2.imshow("Grid", show_grid)
    # cv2.imshow("combined", combined)
    # cv2.waitKey(0)
    return not combined.any()


def get_furthest_point(grid, path):
    max_dist = 0
    start_point = path[0]
    furthest_point = path[-1]
    for x, y in path:
        if check_wall_intersection(start_point[0], start_point[1], x, y, grid):
            dist = (x - start_point[0]) ** 2 + (y - start_point[1]) ** 2
            if dist > max_dist:
                max_dist = dist
                furthest_point = (x, y)
    return furthest_point


# Example usage
# binary_grid = np.array([
#     [0, 1, 0, 0, 0],
#     [0, 1, 0, 1, 0],
#     [0, 0, 0, 1, 0],
#     [0, 1, 0, 0, 0],
#     [0, 0, 0, 1, 0]
# ])
#
# start = (0, 0)
# goal = (4, 4)
# path = a_star(binary_grid, start, goal)
# print("Path:", path)
