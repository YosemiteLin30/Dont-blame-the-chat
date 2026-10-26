"""Breadth-first shortest path over the room graph."""
from collections import deque


def shortest_path(neighbors, start, goal, blocked=()):
    """Rooms from start to goal inclusive, avoiding blocked rooms; None if unreachable."""
    if start == goal:
        return [start]
    if goal in blocked:
        return None
    prev = {start: None}
    queue = deque([start])
    while queue:
        room = queue.popleft()
        for nxt in neighbors(room):
            if nxt in prev or nxt in blocked:
                continue
            prev[nxt] = room
            if nxt == goal:
                path = [nxt]
                while prev[path[-1]] is not None:
                    path.append(prev[path[-1]])
                return path[::-1]
            queue.append(nxt)
    return None
