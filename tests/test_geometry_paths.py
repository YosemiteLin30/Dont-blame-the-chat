import math

from game.geometry import angle_diff, circle_hits_rect, ray_distance, seg_rect_hit, segment_blocked
from game.layout import Layout
from game.pathfinding import shortest_path


def test_segment_and_rect():
    rect = (10, -5, 12, 5)
    assert seg_rect_hit((0, 0), (20, 0), rect) == 0.5
    assert seg_rect_hit((0, 20), (20, 20), rect) is None
    assert segment_blocked((0, 0), (20, 0), [rect]) and not segment_blocked((0, 0), (5, 0), [rect])


def test_ray_and_circle_and_angles():
    assert ray_distance((0, 0), 0.0, 100, [(30, -5, 32, 5)]) == 30
    assert ray_distance((0, 0), 0.0, 100, []) == 100
    assert circle_hits_rect(0, 0, 5, (3, -1, 6, 1)) and not circle_hits_rect(0, 0, 5, (8, -1, 9, 1))
    assert math.isclose(angle_diff(math.pi - 0.1, -math.pi + 0.1), 0.2)


def test_layout_rooms_and_doors(cfgs):
    L = Layout(cfgs[1])
    assert L.room_of(*L.center(5)) == 5 and L.room_of(-50, 9999) == 7
    assert L.neighbors(5) == [4, 6, 2, 8] and sorted(L.neighbors(1)) == [2, 4]
    assert L.door_center(5, 6) == (L.rw * 2, L.center(5)[1])
    walls = L.static_walls()
    # the doorway between rooms 5 and 6 is open, a wall elsewhere on the same line is solid
    assert not segment_blocked(L.center(5), L.center(6), walls)
    assert segment_blocked((L.rw * 2 - 20, 20), (L.rw * 2 + 20, 20), walls)
    # sealing it closes the doorway
    assert segment_blocked(L.center(5), L.center(6), walls + [L.door_rect(5, 6)])


def test_shortest_path_and_blocking(cfgs):
    L = Layout(cfgs[1])
    assert shortest_path(L.neighbors, 1, 9) is not None and len(shortest_path(L.neighbors, 1, 9)) == 5
    assert shortest_path(L.neighbors, 5, 5) == [5]
    assert shortest_path(L.neighbors, 1, 3, blocked={2}) == [1, 4, 5, 6, 3]
    assert shortest_path(L.neighbors, 1, 9, blocked={2, 4}) is None
    assert shortest_path(L.neighbors, 1, 2, blocked={2}) is None
