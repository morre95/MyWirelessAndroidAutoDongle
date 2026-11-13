"""Remove tracks/vias from the board file text (the pcbnew API segfaults on Remove).

Usage: ripup.py board.kicad_pcb spec-json
spec is a list of [net, x0, y0, x1, y1]: every segment/via of `net` lying fully
inside the box is removed.
"""
import json
import re
import sys

path = sys.argv[1]
specs = json.loads(sys.argv[2])
text = open(path).read()
num = r'(-?[\d.]+)'
seg = re.compile(r'\t\(segment\n\t\t\(start %s %s\)\n\t\t\(end %s %s\)\n(?:\t\t\([^\n]*\n)*?\t\t\(net "([^"]+)"\)\n'
                 r'(?:\t\t\([^\n]*\n)*?\t\)\n' % (num, num, num, num))
via = re.compile(r'\t\(via\n\t\t\(at %s %s\)\n(?:\t\t\([^\n]*\n)*?\t\t\(net "([^"]+)"\)\n(?:\t\t\([^\n]*\n)*?\t\)\n'
                 % (num, num))
removed = 0


def inside(net, pts):
    return any(net == n and all(x0 <= x <= x1 and y0 <= y <= y1 for x, y in pts) for n, x0, y0, x1, y1 in specs)


def drop_segment(m):
    global removed
    x1, y1, x2, y2 = map(float, m.groups()[:4])
    if inside(m.group(5), [(x1, y1), (x2, y2)]):
        removed += 1
        return ''
    return m.group(0)


def drop_via(m):
    global removed
    if inside(m.group(3), [(float(m.group(1)), float(m.group(2)))]):
        removed += 1
        return ''
    return m.group(0)


text = via.sub(drop_via, seg.sub(drop_segment, text))
open(path, 'w').write(text)
print('removed', removed)
