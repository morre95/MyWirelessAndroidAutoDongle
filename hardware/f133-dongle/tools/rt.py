"""Clearance-aware helpers for finishing routes on the f133-dongle board.

Builds capped distance fields to foreign copper per layer, then offers a grid
A* router and a track widener on top of them.
"""
import heapq
import numpy as np
import pcbnew

G = 0.05
X0, Y0, X1, Y1 = 100.0, 100.0, 180.5, 124.0
NX, NY = int(round((X1 - X0) / G)) + 1, int(round((Y1 - Y0) / G)) + 1
CAP = 1.2
CLEAR = 0.127
MARGIN = 0.04
EDGE = 0.45
KEEPOUT_X = 174.5
LAYERS = [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]
mm = pcbnew.ToMM
iu = pcbnew.FromMM


def cell(x, y):
    return int(round((x - X0) / G)), int(round((y - Y0) / G))


def pos(ix, iy):
    return X0 + ix * G, Y0 + iy * G


def _window(xa, ya, xb, yb):
    ix0, iy0 = cell(xa - CAP, ya - CAP)
    ix1, iy1 = cell(xb + CAP, yb + CAP)
    ix0, iy0, ix1, iy1 = max(ix0, 0), max(iy0, 0), min(ix1, NX - 1), min(iy1, NY - 1)
    if ix1 < ix0 or iy1 < iy0:
        return None
    xs = X0 + np.arange(ix0, ix1 + 1) * G
    ys = Y0 + np.arange(iy0, iy1 + 1) * G
    gx, gy = np.meshgrid(xs, ys)
    return (slice(iy0, iy1 + 1), slice(ix0, ix1 + 1)), gx, gy


def _rect(field, cx, cy, hw, hh):
    w = _window(cx - hw, cy - hh, cx + hw, cy + hh)
    if w:
        sl, gx, gy = w
        d = np.hypot(np.maximum(np.abs(gx - cx) - hw, 0), np.maximum(np.abs(gy - cy) - hh, 0))
        field[sl] = np.minimum(field[sl], d)


def _capsule(field, x1, y1, x2, y2, r):
    w = _window(min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
    if w:
        sl, gx, gy = w
        dx, dy = x2 - x1, y2 - y1
        ll = dx * dx + dy * dy
        t = np.clip(((gx - x1) * dx + (gy - y1) * dy) / ll, 0, 1) if ll else 0
        d = np.hypot(gx - x1 - t * dx, gy - y1 - t * dy) - r
        field[sl] = np.minimum(field[sl], np.maximum(d, 0))


def via_diameter(via):
    return mm(via.GetWidth(pcbnew.F_Cu))


def distance_fields(board, netname):
    """Distance from every grid point to copper not on `netname`, per layer."""
    fields = [np.full((NY, NX), CAP, np.float32) for _ in LAYERS]
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetname() == netname:
                continue
            bb = pad.GetBoundingBox()
            cx, cy = mm(bb.GetCenter().x), mm(bb.GetCenter().y)
            hw, hh = mm(bb.GetWidth()) / 2, mm(bb.GetHeight()) / 2
            through = pad.GetDrillSize().x > 0
            for i, layer in enumerate(LAYERS):
                if through or pad.IsOnLayer(layer):
                    _rect(fields[i], cx, cy, hw, hh)
    for t in board.GetTracks():
        if t.GetNetname() == netname:
            continue
        s, e = t.GetStart(), t.GetEnd()
        if t.GetClass() == 'PCB_VIA':
            for f in fields:
                _capsule(f, mm(s.x), mm(s.y), mm(s.x), mm(s.y), via_diameter(t) / 2)
        else:
            i = LAYERS.index(t.GetLayer())
            _capsule(fields[i], mm(s.x), mm(s.y), mm(e.x), mm(e.y), mm(t.GetWidth()) / 2)
    return fields


def _board_mask():
    xs = X0 + np.arange(NX) * G
    ys = Y0 + np.arange(NY) * G
    gx, gy = np.meshgrid(xs, ys)
    return (gx > X0 + EDGE) & (gx < KEEPOUT_X) & (gy > Y0 + EDGE) & (gy < Y1 - EDGE)


def track_ok(fields, layer_index, half_width):
    return (fields[layer_index] >= half_width + CLEAR + MARGIN) & _board_mask()


def via_ok(fields, via_radius):
    ok = _board_mask()
    for f in fields:
        ok &= f >= via_radius + CLEAR + MARGIN
    return ok


MOVES = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
         (1, 1, 1.4142), (1, -1, 1.4142), (-1, 1, 1.4142), (-1, -1, 1.4142)]
VIA_COST = 60.0


def astar(ok, vok, start, goal=None):
    """Route on layers 0 (F.Cu) / 1 (B.Cu). `start` is (layer, ix, iy).

    With `goal` (ix, iy) the path ends there on either layer; without it the
    path ends at the first cell where a via fits (plane stitching).
    """
    def h(ix, iy):
        if goal is None:
            return 0.0
        dx, dy = abs(ix - goal[0]), abs(iy - goal[1])
        return max(dx, dy) + 0.4142 * min(dx, dy)

    best = {start: 0.0}
    prev = {}
    heap = [(h(start[1], start[2]), 0.0, start)]
    while heap:
        _, g, node = heapq.heappop(heap)
        if g > best.get(node, 1e18):
            continue
        layer, ix, iy = node
        done = (ix, iy) == goal if goal else bool(vok[iy, ix]) and g > 6
        if done:
            path = [node]
            while node in prev:
                node = prev[node]
                path.append(node)
            return path[::-1]
        steps = [((layer, ix + dx, iy + dy), c) for dx, dy, c in MOVES]
        if goal and vok[iy, ix]:
            steps.append(((1 - layer, ix, iy), VIA_COST))
        for nxt, c in steps:
            nl, nx, ny = nxt
            if not (0 <= nx < NX and 0 <= ny < NY) or not ok[nl][ny, nx]:
                continue
            ng = g + c
            if ng < best.get(nxt, 1e18):
                best[nxt] = ng
                prev[nxt] = node
                heapq.heappush(heap, (ng + h(nx, ny), ng, nxt))
    return None


def add_track(board, net, layer, a, b, width):
    if abs(a[0] - b[0]) < 1e-6 and abs(a[1] - b[1]) < 1e-6:
        return
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(pcbnew.VECTOR2I(iu(a[0]), iu(a[1])))
    t.SetEnd(pcbnew.VECTOR2I(iu(b[0]), iu(b[1])))
    t.SetLayer(layer)
    t.SetWidth(iu(width))
    t.SetNet(net)
    board.Add(t)


def add_via(board, net, p, diameter, drill=0.3):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pcbnew.VECTOR2I(iu(p[0]), iu(p[1])))
    v.SetWidth(pcbnew.F_Cu, iu(diameter))
    v.SetDrill(iu(drill))
    v.SetNet(net)
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    board.Add(v)


def emit(board, net, path, width, start_xy, end_xy=None, via_diameter_mm=0.5):
    """Turn a cell path into merged track segments and vias."""
    cu = [pcbnew.F_Cu, pcbnew.B_Cu]
    pts = [(n[0], pos(n[1], n[2])) for n in path]
    add_track(board, net, cu[pts[0][0]], start_xy, pts[0][1], width)
    run_start = 0
    for i in range(1, len(pts) + 1):
        last = i == len(pts)
        layer_change = not last and pts[i][0] != pts[i - 1][0]
        turn = (not last and not layer_change and i - run_start >= 2 and
                (path[i][1] - path[i - 1][1], path[i][2] - path[i - 1][2]) !=
                (path[i - 1][1] - path[i - 2][1], path[i - 1][2] - path[i - 2][2]))
        if last or layer_change or turn:
            add_track(board, net, cu[pts[run_start][0]], pts[run_start][1], pts[i - 1][1], width)
            run_start = i - 1
        if layer_change:
            add_via(board, net, pts[i][1], via_diameter_mm)
            run_start = i
    if end_xy:
        add_track(board, net, cu[pts[-1][0]], pts[-1][1], end_xy, width)
    else:
        add_via(board, net, pts[-1][1], via_diameter_mm)
