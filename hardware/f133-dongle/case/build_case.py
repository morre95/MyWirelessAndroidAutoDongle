"""Build the two-part snap-fit case for the f133-dongle board.

Run with:  freecadcmd build_case.py   (after export_board_model.py)
Writes f133-dongle-case.FCStd plus STEP and STL files next to this script and
prints a fit report (interference volumes and clearances).

Case frame (mm): x = KiCad x - board left, y = board bottom - KiCad y, z = 0 at
the bottom face of the PCB. The USB plug points towards -x.
"""
import json
import os

import FreeCAD as App
import Mesh
import Part
from FreeCAD import Vector as V

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(OUT_DIR, "board.json")) as board_file:
    BOARD = json.load(board_file)

PCB_LENGTH, PCB_WIDTH, PCB_THICKNESS = BOARD["length"], BOARD["width"], BOARD["thickness"]
PCB_CORNER_RADIUS = 1.5
MOUNT_HOLES = [(h["x"], h["y"]) for h in BOARD["mount_holes"]]
MOUNT_HOLE_DIAMETER = BOARD["mount_holes"][0]["diameter"]
PLUG_Y = BOARD["plug_center_y"]

# USB-A plug, CNC Tech 1001-011-01101 (drawing 2015-09-09)
PLUG_TIP_X, PLUG_REAR_X = -14.7, 4.1
PLUG_WIDTH, PLUG_HEIGHT = 12.05, 4.5
PLUG_TOP_Z = PCB_THICKNESS + 3.25  # shell top is 3.25 above the PCB top face
PLUG_POST_DEPTH = 1.25             # shield tabs and posts below the PCB
PLUG_EXPOSED_LENGTH = 12.0         # standard USB-A plug length in front of the overmold

# Mating USB-A receptacle (extension cable or car socket), for the fit check
RECEPTACLE_DEPTH = 10.3
RECEPTACLE_OPENING = (12.5, 5.12)
RECEPTACLE_BODY = (16.0, 8.0)

# Shell
BOARD_GAP = 0.3
WALL = 1.6
FLOOR = 1.2
LID = 1.2
FLOOR_Z = -1.5
CEILING_Z = PLUG_TOP_Z + 0.15
PLUG_SLOT_GAP = 0.2

LIP_THICKNESS, LIP_DEPTH, LIP_GAP = 0.8, 2.0, 0.2
LIP_X_RANGE = (3.0, 73.0)          # stops short of the antenna keepout
SNAP_ENGAGEMENT = 0.35
SNAP_X_RANGE = (20.0, 60.0)
SNAP_Z = CEILING_Z - 1.3
SNAP_RIDGE_RADIUS = LIP_GAP + SNAP_ENGAGEMENT
SNAP_GROOVE_RADIUS = SNAP_RIDGE_RADIUS + 0.1

POST_RADIUS, PIN_RADIUS = 1.6, 0.95
PIN_TIP_Z = -0.9
BOSS_RADIUS, SOCKET_RADIUS = 2.0, 1.25
LED_HOLE_RADIUS = 0.75
TEST_PAD_HOLE_RADIUS = 1.1

VENT_SLOT_WIDTH, VENT_SLOT_PITCH = 1.2, 2.8
VENTS = {"U1": (5, 12.0), "U6": (3, 8.0)}  # slots per group, slot length

INNER_X0, INNER_X1 = -BOARD_GAP, PCB_LENGTH + BOARD_GAP
INNER_Y0, INNER_Y1 = -BOARD_GAP, PCB_WIDTH + BOARD_GAP
OUTER_X0 = PLUG_TIP_X + PLUG_EXPOSED_LENGTH
OUTER_X1 = INNER_X1 + WALL
OUTER_Y0, OUTER_Y1 = INNER_Y0 - WALL, INNER_Y1 + WALL
OUTER_Z0, OUTER_Z1 = FLOOR_Z - FLOOR, CEILING_Z + LID
INNER_CORNER_RADIUS = PCB_CORNER_RADIUS + BOARD_GAP
OUTER_CORNER_RADIUS = INNER_CORNER_RADIUS + WALL


def box(x0, x1, y0, y1, z0, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def rounded_box(x0, x1, y0, y1, z0, z1, radius):
    solid = box(x0, x1, y0, y1, z0, z1)
    vertical = [e for e in solid.Edges if abs(e.Vertexes[0].Z - e.Vertexes[1].Z) > 1e-6]
    return solid.makeFillet(radius, vertical)


def cylinder_z(x, y, radius, z0, z1):
    return Part.makeCylinder(radius, z1 - z0, V(x, y, z0))


def cylinder_x(x0, x1, y, z, radius):
    return Part.makeCylinder(radius, x1 - x0, V(x0, y, z), V(1, 0, 0))


def vent_slots(z0, z1):
    """Round-ended slots above/below the two warm parts, long axis along y."""
    slots = []
    for part in BOARD["components"]:
        if part["ref"] not in VENTS:
            continue
        count, length = VENTS[part["ref"]]
        center_x, center_y = (part["x0"] + part["x1"]) / 2, (part["y0"] + part["y1"]) / 2
        straight = length - VENT_SLOT_WIDTH
        for i in range(count):
            x = center_x + (i - (count - 1) / 2) * VENT_SLOT_PITCH
            slot = box(x - VENT_SLOT_WIDTH / 2, x + VENT_SLOT_WIDTH / 2,
                       center_y - straight / 2, center_y + straight / 2, z0, z1)
            for end_y in (center_y - straight / 2, center_y + straight / 2):
                slot = slot.fuse(cylinder_z(x, end_y, VENT_SLOT_WIDTH / 2, z0, z1))
            slots.append(slot)
    return slots


def build_tray():
    tray = rounded_box(OUTER_X0, OUTER_X1, OUTER_Y0, OUTER_Y1, OUTER_Z0, CEILING_Z, OUTER_CORNER_RADIUS)
    tray = tray.cut(rounded_box(INNER_X0, INNER_X1, INNER_Y0, INNER_Y1, FLOOR_Z, CEILING_Z,
                                INNER_CORNER_RADIUS))
    half_slot = PLUG_WIDTH / 2 + PLUG_SLOT_GAP
    tray = tray.cut(box(OUTER_X0 - 1, 0, PLUG_Y - half_slot, PLUG_Y + half_slot,
                        PLUG_TOP_Z - PLUG_HEIGHT - PLUG_SLOT_GAP, CEILING_Z))
    for x, y in MOUNT_HOLES:
        tray = tray.fuse(cylinder_z(x, y, BOSS_RADIUS, FLOOR_Z, 0))
        tray = tray.cut(cylinder_z(x, y, SOCKET_RADIUS, FLOOR_Z, 0))
    for wall_y, lip_face_y in ((INNER_Y0, INNER_Y0 + LIP_GAP), (INNER_Y1, INNER_Y1 - LIP_GAP)):
        tray = tray.cut(cylinder_x(*SNAP_X_RANGE, lip_face_y, SNAP_Z, SNAP_GROOVE_RADIUS))
    for pad in BOARD["test_pads"]:
        tray = tray.cut(cylinder_z(pad["x"], pad["y"], TEST_PAD_HOLE_RADIUS, OUTER_Z0 - 1, FLOOR_Z + 1))
    tray = tray.cut(vent_slots(OUTER_Z0 - 1, FLOOR_Z + 0.01))
    # Fingernail notch at the rear for prying the lid off
    tray = tray.cut(box(OUTER_X1 - 0.8, OUTER_X1 + 1, PCB_WIDTH / 2 - 4, PCB_WIDTH / 2 + 4,
                        CEILING_Z - 0.8, CEILING_Z))
    return tray.removeSplitter()


def build_lid():
    lid = rounded_box(OUTER_X0, OUTER_X1, OUTER_Y0, OUTER_Y1, CEILING_Z, OUTER_Z1, OUTER_CORNER_RADIUS)
    lip_z0 = CEILING_Z - LIP_DEPTH
    lip_y0, lip_y1 = INNER_Y0 + LIP_GAP, INNER_Y1 - LIP_GAP
    inside_lips = box(0, PCB_LENGTH, lip_y0, lip_y1, lip_z0 - 1, CEILING_Z)
    lid = lid.fuse([
        box(*LIP_X_RANGE, lip_y0, lip_y0 + LIP_THICKNESS, lip_z0, CEILING_Z),
        box(*LIP_X_RANGE, lip_y1 - LIP_THICKNESS, lip_y1, lip_z0, CEILING_Z),
        cylinder_x(*SNAP_X_RANGE, lip_y0, SNAP_Z, SNAP_RIDGE_RADIUS).cut(inside_lips),
        cylinder_x(*SNAP_X_RANGE, lip_y1, SNAP_Z, SNAP_RIDGE_RADIUS).cut(inside_lips),
    ])
    shoulder_z = PCB_THICKNESS + 0.05
    for x, y in MOUNT_HOLES:
        lid = lid.fuse(cylinder_z(x, y, POST_RADIUS, shoulder_z, CEILING_Z))
        lid = lid.fuse(cylinder_z(x, y, PIN_RADIUS, PIN_TIP_Z, shoulder_z))
    lid = lid.cut(cylinder_z(BOARD["led"]["x"], BOARD["led"]["y"], LED_HOLE_RADIUS,
                             CEILING_Z - 1, OUTER_Z1 + 1))
    lid = lid.cut(vent_slots(CEILING_Z - 0.01, OUTER_Z1 + 1))
    return lid.removeSplitter()


def build_board():
    """PCB with every component as a datasheet-height block, plus the USB plug."""
    pcb = rounded_box(0, PCB_LENGTH, 0, PCB_WIDTH, 0, PCB_THICKNESS, PCB_CORNER_RADIUS)
    for x, y in MOUNT_HOLES:
        pcb = pcb.cut(cylinder_z(x, y, MOUNT_HOLE_DIAMETER / 2, -1, 3))
    top = PCB_THICKNESS
    parts = [box(c["x0"], c["x1"], c["y0"], c["y1"], top, top + c["height"]) for c in BOARD["components"]]
    half = PLUG_WIDTH / 2
    plug = box(PLUG_TIP_X, PLUG_REAR_X, PLUG_Y - half, PLUG_Y + half, PLUG_TOP_Z - PLUG_HEIGHT, PLUG_TOP_Z)
    plug = plug.cut(box(0, 10, 0, PCB_WIDTH, -1, top))
    plug = plug.cut(box(PLUG_TIP_X - 1, PLUG_TIP_X + 8, PLUG_Y - half + 0.3, PLUG_Y + half - 0.3,
                        PLUG_TOP_Z - PLUG_HEIGHT + 0.3, PLUG_TOP_Z - 2.2))  # contact cavity
    parts.append(plug)
    for tab_y in (PLUG_Y - 5.7, PLUG_Y + 5.7):  # shield tabs through the board
        parts.append(box(2.1, 4.1, tab_y - 0.15, tab_y + 0.15, -PLUG_POST_DEPTH, 0))
    for post_y in (PLUG_Y - 2.3, PLUG_Y + 2.3):  # plastic locating posts
        parts.append(cylinder_z(3.1, post_y, 0.5, -PLUG_POST_DEPTH, 0))
    return pcb, Part.makeCompound(parts)


def build_receptacle():
    """A mating USB-A socket pushed fully onto the plug."""
    mouth_x = PLUG_TIP_X + RECEPTACLE_DEPTH
    body_w, body_h = RECEPTACLE_BODY
    open_w, open_h = RECEPTACLE_OPENING
    plug_z = PLUG_TOP_Z - PLUG_HEIGHT / 2
    body = box(mouth_x - 30, mouth_x, PLUG_Y - body_w / 2, PLUG_Y + body_w / 2,
               plug_z - body_h / 2, plug_z + body_h / 2)
    return body.cut(box(PLUG_TIP_X - 0.3, mouth_x + 1, PLUG_Y - open_w / 2, PLUG_Y + open_w / 2,
                        plug_z - open_h / 2, plug_z + open_h / 2))


def report_fit(tray, lid, pcb, parts, receptacle):
    case = tray.fuse(lid)
    board = pcb.fuse(parts)
    print("interference mm3: tray/board %.3f  lid/board %.3f  tray/lid %.3f  socket/case %.3f  socket/board %.3f"
          % (tray.common(board).Volume, lid.common(board).Volume, tray.common(lid).Volume,
             receptacle.common(case).Volume, receptacle.common(board).Volume))
    tallest = max(c["height"] for c in BOARD["components"])
    print("clearance mm: lid to components %.2f  tray walls to PCB edge %.2f  ceiling above tallest part %.2f"
          % (lid.distToShape(Part.makeCompound([s for s in parts.Solids if s.BoundBox.ZMin >= PCB_THICKNESS - 1e-6
                                                and s.BoundBox.XMin > PLUG_REAR_X]))[0],
             BOARD_GAP, CEILING_Z - PCB_THICKNESS - tallest))
    print("usb mm: plug exposed %.2f (standard 12.0)  socket mouth to case front %.2f  case front %.1f x %.1f"
          % (OUTER_X0 - PLUG_TIP_X, OUTER_X0 - (PLUG_TIP_X + RECEPTACLE_DEPTH),
             OUTER_Y1 - OUTER_Y0, OUTER_Z1 - OUTER_Z0))


def main():
    doc = App.newDocument("f133_dongle_case")
    pcb, parts = build_board()
    shapes = {"Tray": build_tray(), "Lid": build_lid(), "Pcb": pcb, "Components": parts,
              "UsbSocket": build_receptacle()}
    for name, shape in shapes.items():
        doc.addObject("Part::Feature", name).Shape = shape
        bounds = shape.BoundBox
        print("%-11s valid=%s solids=%d volume=%.0f mm3  %.1f x %.1f x %.1f"
              % (name, shape.isValid(), len(shape.Solids), shape.Volume,
                 bounds.XLength, bounds.YLength, bounds.ZLength))
    doc.recompute()
    report_fit(shapes["Tray"], shapes["Lid"], pcb, parts, shapes["UsbSocket"])
    doc.saveAs(os.path.join(OUT_DIR, "f133-dongle-case.FCStd"))
    for name, filename in (("Tray", "f133-dongle-case-tray"), ("Lid", "f133-dongle-case-lid")):
        shapes[name].exportStep(os.path.join(OUT_DIR, filename + ".step"))
        Mesh.export([doc.getObject(name)], os.path.join(OUT_DIR, filename + ".stl"))


main()
