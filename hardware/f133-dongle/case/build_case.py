"""Build the two-part snap-fit case for the f133-dongle board.

Run with:  freecadcmd build_case.py   (after export_board_model.py)
Writes f133-dongle-case.FCStd plus STEP and STL files next to this script and
prints a fit report (interference volumes and clearances).

Case frame (mm): x = KiCad x - board left, y = board bottom - KiCad y, z = 0 at
the bottom face of the PCB. The USB-C receptacle opens towards -x.
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

# USB-C receptacle, HRO TYPE-C-31-M-12 (KiCad footprint origin = body centre)
USBC_X, USBC_Y = BOARD["usb_connector"]["x"], BOARD["usb_connector"]["y"]
USBC_LENGTH, USBC_WIDTH, USBC_HEIGHT = 7.3, 8.94, 3.26
USBC_MOUTH_X = USBC_X - USBC_LENGTH / 2
USBC_TOP_Z = PCB_THICKNESS + USBC_HEIGHT
USBC_LEG_DEPTH = 0.8               # shell legs below the PCB
USBC_LEG_OFFSETS = (-1.05, 3.13)   # leg rows, measured from the body centre towards the rear

# Mating USB-C cable plug, for the fit check (USB Type-C spec maximum overmold)
CABLE_OVERMOLD = (12.35, 6.5)
CABLE_TIP = (8.25, 2.4, 6.65)      # width, height, insertion length

# Shell
BOARD_GAP = 0.3
WALL = 1.6
FLOOR = 1.2
LID = 1.2
FLOOR_Z = -1.5
CEILING_Z = USBC_TOP_Z + 0.15
CONNECTOR_SLOT_GAP = 0.2

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
OUTER_X0 = USBC_MOUTH_X            # receptacle mouth flush with the front face, so any cable fits
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
    half_slot = USBC_WIDTH / 2 + CONNECTOR_SLOT_GAP
    tray = tray.cut(box(OUTER_X0 - 1, 0, USBC_Y - half_slot, USBC_Y + half_slot,
                        PCB_THICKNESS - CONNECTOR_SLOT_GAP, CEILING_Z))
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
    """PCB with every component as a datasheet-height block, plus the USB-C receptacle."""
    pcb = rounded_box(0, PCB_LENGTH, 0, PCB_WIDTH, 0, PCB_THICKNESS, PCB_CORNER_RADIUS)
    for x, y in MOUNT_HOLES:
        pcb = pcb.cut(cylinder_z(x, y, MOUNT_HOLE_DIAMETER / 2, -1, 3))
    top = PCB_THICKNESS
    parts = [box(c["x0"], c["x1"], c["y0"], c["y1"], top, top + c["height"]) for c in BOARD["components"]]
    half = USBC_WIDTH / 2
    shell = box(USBC_MOUTH_X, USBC_MOUTH_X + USBC_LENGTH, USBC_Y - half, USBC_Y + half, top, USBC_TOP_Z)
    tip_w, tip_h, tip_len = CABLE_TIP
    axis_z = top + USBC_HEIGHT / 2
    shell = shell.cut(box(USBC_MOUTH_X - 1, USBC_MOUTH_X + tip_len + 0.2, USBC_Y - tip_w / 2 - 0.05,
                          USBC_Y + tip_w / 2 + 0.05, axis_z - tip_h / 2 - 0.08, axis_z + tip_h / 2 + 0.08))
    parts.append(shell)
    for offset in USBC_LEG_OFFSETS:
        for side in (-1, 1):
            parts.append(box(USBC_X + offset - 0.5, USBC_X + offset + 0.5, USBC_Y + side * 4.32 - 0.15,
                             USBC_Y + side * 4.32 + 0.15, -USBC_LEG_DEPTH, top))
    return pcb, Part.makeCompound(parts)


def build_cable_plug():
    """A USB-C cable plug with the largest overmold the spec allows, fully inserted."""
    body_w, body_h = CABLE_OVERMOLD
    tip_w, tip_h, tip_len = CABLE_TIP
    axis_z = PCB_THICKNESS + USBC_HEIGHT / 2
    body = box(USBC_MOUTH_X - 22, USBC_MOUTH_X, USBC_Y - body_w / 2, USBC_Y + body_w / 2,
               axis_z - body_h / 2, axis_z + body_h / 2)
    return body.fuse(box(USBC_MOUTH_X, USBC_MOUTH_X + tip_len, USBC_Y - tip_w / 2, USBC_Y + tip_w / 2,
                         axis_z - tip_h / 2, axis_z + tip_h / 2))


def report_fit(tray, lid, pcb, parts, cable):
    case = tray.fuse(lid)
    board = pcb.fuse(parts)
    print("interference mm3: tray/board %.3f  lid/board %.3f  tray/lid %.3f  cable/case %.3f  cable/board %.3f"
          % (tray.common(board).Volume, lid.common(board).Volume, tray.common(lid).Volume,
             cable.common(case).Volume, cable.common(board).Volume))
    tallest = max(c["height"] for c in BOARD["components"])
    on_top = [s for s in parts.Solids if s.BoundBox.ZMin >= PCB_THICKNESS - 1e-6]
    print("clearance mm: lid to parts %.2f  tray walls to PCB edge %.2f  ceiling above tallest chip %.2f"
          % (lid.distToShape(Part.makeCompound(on_top))[0], BOARD_GAP, CEILING_Z - PCB_THICKNESS - tallest))
    print("usb-c mm: receptacle mouth to case front %.2f (flush)  front wall %.2f  cable overmold %.1f x %.1f on a %.1f x %.1f front"
          % (USBC_MOUTH_X - OUTER_X0, INNER_X0 - OUTER_X0, CABLE_OVERMOLD[0], CABLE_OVERMOLD[1],
             OUTER_Y1 - OUTER_Y0, OUTER_Z1 - OUTER_Z0))


def main():
    doc = App.newDocument("f133_dongle_case")
    pcb, parts = build_board()
    shapes = {"Tray": build_tray(), "Lid": build_lid(), "Pcb": pcb, "Components": parts,
              "UsbCable": build_cable_plug()}
    for name, shape in shapes.items():
        doc.addObject("Part::Feature", name).Shape = shape
        bounds = shape.BoundBox
        print("%-11s valid=%s solids=%d volume=%.0f mm3  %.1f x %.1f x %.1f"
              % (name, shape.isValid(), len(shape.Solids), shape.Volume,
                 bounds.XLength, bounds.YLength, bounds.ZLength))
    doc.recompute()
    report_fit(shapes["Tray"], shapes["Lid"], pcb, parts, shapes["UsbCable"])
    doc.saveAs(os.path.join(OUT_DIR, "f133-dongle-case.FCStd"))
    for name, filename in (("Tray", "f133-dongle-case-tray"), ("Lid", "f133-dongle-case-lid")):
        shapes[name].exportStep(os.path.join(OUT_DIR, filename + ".step"))
        Mesh.export([doc.getObject(name)], os.path.join(OUT_DIR, filename + ".stl"))


main()
