"""Route individual connections with clearance checking.

Usage: finish.py board.kicad_pcb jobs-json
Each job is [net, start, target, track width, via diameter] where
  start  is "REF.PAD" or an [x, y] point on F.Cu that already belongs to the net,
  target is null (stitch to the plane with a via), [x, y] (an existing via,
         reachable on either layer) or [x, y, "F"] (an F.Cu-only pad).
"""
import json
import sys
import pcbnew
import rt

BOARD = sys.argv[1]
JOBS = json.loads(sys.argv[2])

for netname, start, target, width, via_d in JOBS:
    board = pcbnew.LoadBoard(BOARD)
    net = board.FindNet(netname)
    if isinstance(start, str):
        ref, padnum = start.split('.')
        pad = next(p for p in board.FindFootprintByReference(ref).Pads() if p.GetNumber() == padnum)
        assert pad.GetNetname() == netname, (start, pad.GetNetname())
        start_xy = (rt.mm(pad.GetPosition().x), rt.mm(pad.GetPosition().y))
    else:
        start_xy = tuple(start)
    fields = rt.distance_fields(board, netname)
    ok = [rt.track_ok(fields, 0, width / 2), rt.track_ok(fields, 3, width / 2)]
    vok = rt.via_ok(fields, via_d / 2)
    sx, sy = rt.cell(*start_xy)
    ok[0][sy, sx] = True
    goal = end_xy = None
    if target:
        end_xy = tuple(target[:2])
        goal = rt.cell(*end_xy)
        ok[0][goal[1], goal[0]] = True
        ok[1][goal[1], goal[0]] = len(target) == 2
    path = rt.astar(ok, vok, (0, sx, sy), goal)
    if not path:
        print('FAILED', netname, start)
        continue
    rt.emit(board, net, path, width, start_xy, end_xy, via_d)
    pcbnew.SaveBoard(BOARD, board)
    vias = sum(1 for a, b in zip(path, path[1:]) if a[0] != b[0])
    print('routed', netname, start, 'cells', len(path), 'vias', vias)
