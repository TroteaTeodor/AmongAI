"""A* pathfinding on a 2D grid with wall-proximity avoidance."""

import heapq


def build_wall_cost(grid, grid_width, grid_height):
    """Pre-compute extra cost for cells near walls. Cells adjacent to a blocked
    cell get a penalty, making A* prefer open corridors over tight corners."""
    cost = [[0.0] * grid_width for _ in range(grid_height)]
    for y in range(grid_height):
        for x in range(grid_width):
            if not grid[y][x]:
                continue
            # Check 8 neighbors — if any is blocked, this cell is "wall-adjacent"
            near_wall = False
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = x + dx, y + dy
                    if nx < 0 or nx >= grid_width or ny < 0 or ny >= grid_height:
                        near_wall = True
                        break
                    if not grid[ny][nx]:
                        near_wall = True
                        break
                if near_wall:
                    break
            cost[y][x] = 3.0 if near_wall else 0.0
    return cost


def astar_search(grid, grid_width, grid_height, start, goal, wall_cost=None):
    """A* search on a boolean grid with wall-avoidance penalty.

    Args:
        grid: 2D list[list[bool]], True=walkable.
        grid_width, grid_height: Dimensions.
        start: (gx, gy) start cell.
        goal: (gx, gy) goal cell.

    Returns:
        List of (gx, gy) cells from start to goal, or None if no path.
    """
    if start == goal:
        return [start]

    # Use pre-computed wall costs or compute on the fly
    if wall_cost is None:
        wall_cost = build_wall_cost(grid, grid_width, grid_height)

    # 8-directional movement with diagonal cost
    DIRS = [
        (0, 1, 1.0), (0, -1, 1.0), (1, 0, 1.0), (-1, 0, 1.0),
        (1, 1, 1.414), (1, -1, 1.414), (-1, 1, 1.414), (-1, -1, 1.414),
    ]

    def heuristic(a, b):
        # Octile distance
        dx = abs(a[0] - b[0])
        dy = abs(a[1] - b[1])
        return max(dx, dy) + 0.414 * min(dx, dy)

    open_set = []
    heapq.heappush(open_set, (0 + heuristic(start, goal), 0, start))
    came_from = {}
    g_score = {start: 0}
    closed = set()

    while open_set:
        _, current_g, current = heapq.heappop(open_set)

        if current == goal:
            # Reconstruct path
            path = []
            node = current
            while node in came_from:
                path.append(node)
                node = came_from[node]
            path.append(start)
            path.reverse()
            return path

        if current in closed:
            continue
        closed.add(current)

        cx, cy = current
        for dx, dy, cost in DIRS:
            nx, ny = cx + dx, cy + dy

            # Bounds check
            if nx < 0 or nx >= grid_width or ny < 0 or ny >= grid_height:
                continue
            # Walkability check
            if not grid[ny][nx]:
                continue
            # Diagonal: check that both adjacent cells are walkable (prevent corner cutting)
            if dx != 0 and dy != 0:
                if not grid[cy][cx + dx] or not grid[cy + dy][cx]:
                    continue

            neighbor = (nx, ny)
            if neighbor in closed:
                continue

            # Base movement cost + wall proximity penalty
            tentative_g = g_score[current] + cost + wall_cost[ny][nx]
            if tentative_g < g_score.get(neighbor, float('inf')):
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f = tentative_g + heuristic(neighbor, goal)
                heapq.heappush(open_set, (f, tentative_g, neighbor))

    return None  # No path found
