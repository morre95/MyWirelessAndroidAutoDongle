"""Widen power-net tracks as far as clearance allows. Usage: widen.py board.kicad_pcb"""
import sys
import numpy as np
import pcbnew
import rt

BOARD = sys.argv[1]
MAX_WIDTH = {'/VBUS': 0.6, '/SW_3V3': 0.6, '/SW_0V9': 0.6, '/+3V3': 0.5, '/+0V9': 0.5, '/GND': 0.4,
             '/WL_LDO_OUT': 0.4, '/WL_VIN_LDO': 0.4, '/+VDRAM': 0.3, '/+1V8': 0.3}
STEPS = [0.6, 0.5, 0.4, 0.3, 0.25, 0.2]
EDGE_CLEAR = 0.32
PIECE = 0.8


def fits(field, a, b, width):
    n = max(2, int(np.hypot(b[0] - a[0], b[1] - a[1]) / (rt.G / 2)) + 1)
    xs, ys = np.linspace(a[0], b[0], n), np.linspace(a[1], b[1], n)
    reach = width / 2 + EDGE_CLEAR
    if xs.min() - reach < rt.X0 or xs.max() + reach > rt.X1 or ys.min() - reach < rt.Y0 or ys.max() + reach > rt.Y1:
        return False
    ix = np.rint((xs - rt.X0) / rt.G).astype(int)
    iy = np.rint((ys - rt.Y0) / rt.G).astype(int)
    return bool((field[iy, ix] >= width / 2 + rt.CLEAR + rt.MARGIN + rt.G / 2).all())


def split(board, track):
    """Cut a long track into short pieces so one tight spot does not pin its whole length."""
    a = (rt.mm(track.GetStart().x), rt.mm(track.GetStart().y))
    b = (rt.mm(track.GetEnd().x), rt.mm(track.GetEnd().y))
    count = int(np.hypot(b[0] - a[0], b[1] - a[1]) / PIECE)
    if count < 2:
        return
    pts = [(a[0] + (b[0] - a[0]) * i / count, a[1] + (b[1] - a[1]) * i / count) for i in range(count + 1)]
    track.SetEnd(pcbnew.VECTOR2I(rt.iu(pts[1][0]), rt.iu(pts[1][1])))
    for p, q in zip(pts[1:], pts[2:-1] + [b]):
        rt.add_track(board, track.GetNet(), track.GetLayer(), p, q, rt.mm(track.GetWidth()))


board = pcbnew.LoadBoard(BOARD)
for t in list(board.GetTracks()):
    if t.GetNetname() in MAX_WIDTH and t.GetClass() == 'PCB_TRACK':
        split(board, t)
for netname, max_width in MAX_WIDTH.items():
    fields = rt.distance_fields(board, netname)
    total = widened = 0
    for t in board.GetTracks():
        if t.GetNetname() != netname or t.GetClass() != 'PCB_TRACK':
            continue
        total += 1
        a = (rt.mm(t.GetStart().x), rt.mm(t.GetStart().y))
        b = (rt.mm(t.GetEnd().x), rt.mm(t.GetEnd().y))
        field = fields[rt.LAYERS.index(t.GetLayer())]
        for width in STEPS:
            if width <= max_width and width > rt.mm(t.GetWidth()) + 1e-6 and fits(field, a, b, width):
                t.SetWidth(rt.iu(width))
                widened += 1
                break
    print(netname, 'segments', total, 'widened', widened)
pcbnew.SaveBoard(BOARD, board)
