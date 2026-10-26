"""Small 2D helpers: segment/rectangle tests, ray casting and angles."""
import math

# A rectangle is (x0, y0, x1, y1).


def seg_rect_hit(p, q, rect):
    """Fraction t in [0, 1] where segment p->q first enters rect, or None (Liang-Barsky)."""
    x0, y0 = p
    dx, dy = q[0] - x0, q[1] - y0
    t0, t1 = 0.0, 1.0
    for pp, qq in ((-dx, x0 - rect[0]), (dx, rect[2] - x0), (-dy, y0 - rect[1]), (dy, rect[3] - y0)):
        if pp == 0:
            if qq < 0:
                return None
        else:
            r = qq / pp
            if pp < 0:
                if r > t1:
                    return None
                t0 = max(t0, r)
            else:
                if r < t0:
                    return None
                t1 = min(t1, r)
    return t0


def segment_blocked(p, q, rects):
    return any(seg_rect_hit(p, q, r) is not None for r in rects)


def ray_distance(origin, angle, max_dist, rects):
    """Distance from origin along angle to the first rectangle, capped at max_dist."""
    end = (origin[0] + math.cos(angle) * max_dist, origin[1] + math.sin(angle) * max_dist)
    best = 1.0
    for r in rects:
        t = seg_rect_hit(origin, end, r)
        if t is not None and t < best:
            best = t
    return best * max_dist


def circle_hits_rect(cx, cy, radius, rect):
    nx = min(max(cx, rect[0]), rect[2])
    ny = min(max(cy, rect[1]), rect[3])
    return (cx - nx) ** 2 + (cy - ny) ** 2 < radius * radius


def angle_diff(a, b):
    """Smallest absolute difference between two angles (radians)."""
    d = (a - b + math.pi) % (2 * math.pi) - math.pi
    return abs(d)
