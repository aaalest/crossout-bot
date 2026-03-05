import math
from typing import List, Tuple


# Helper function to check if a point is inside the grid
def is_inside_grid(x: int, y: int, grid: List[List[int]]) -> bool:
    return 0 <= x < len(grid) and 0 <= y < len(grid[0])


# Pixel traversal using Bresenham's line algorithm to check for wall intersection
def check_wall_intersection(x1: int, y1: int, x2: int, y2: int, grid: List[List[int]]) -> bool:
    dx = abs(x2 - x1)
    dy = abs(y2 - y1)
    x, y = x1, y1
    xi, yi = 1 if x2 > x1 else -1, 1 if y2 > y1 else -1
    if dx > dy:
        err = -dx / 2
        while x != x2:
            if is_inside_grid(x, y, grid) and grid[x][y] == 1:
                return True
            err += dy
            if err > 0:
                y += yi
                err -= dx
            x += xi
    else:
        err = -dy / 2
        while y != y2:
            if is_inside_grid(x, y, grid) and grid[x][y] == 1:
                return True
            err += dx
            if err > 0:
                x += xi
                err -= dy
            y += yi
    return False


# Function to reduce the number of points in the path
def simplify_path(path: List[Tuple[int, int]], grid: List[List[int]], tolerance: float = 0.5) -> List[
    Tuple[int, int]]:
    simplified_path = [path[0]]
    step_size = max(2, int(len(path) * tolerance))  # Ensure step_size is at least 2 to avoid infinite loops

    i = 0
    while i < len(path) - 1:
        j = min(i + step_size, len(path) - 1)  # Control how far to look ahead based on tolerance
        while j > i + 1:  # Skip adjacent points
            x1, y1 = path[i]
            x2, y2 = path[j]
            # Check for wall intersections
            if not check_wall_intersection(x1, y1, x2, y2, grid):
                simplified_path.append(path[j])
                i = j  # Skip to the furthest point that doesn't intersect a wall
                break
            j -= 1  # Move to the previous point and test again
        if j == i + 1:
            # Couldn't skip any points, so add the next point in the path
            simplified_path.append(path[i + 1])
            i += 1

    return simplified_path
