"""Build the two-part snap-fit case for the f133-dongle board.

Run with:  freecadcmd build_case.py
Writes f133-dongle-case.FCStd plus STEP and STL files next to this script.

Local coordinates (mm): x = KiCad x - 100, y = 124 - KiCad y, z = 0 at the
bottom face of the PCB. The USB plug points towards -x.
"""
import os

import FreeCAD as App
import Mesh
import Part
from FreeCAD import Vector as V

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

# Board (from f133-dongle.kicad_pcb)
PCB_LENGTH, PCB_WIDTH, PCB_THICKNESS, PCB_CORNER_RADIUS = 80.5, 24.0, 1.6, 1.5
MOUNT_HOLES = [(4.5, 21.45), (4.5, 2.55), (72.45, 15.5)]  # H1, H2, H3
MOUNT_HOLE_DIAMETER = 2.2
LED_POSITION = (71.9, 22.1)  # D1

# USB-A plug, CNC Tech 1001-011-01101 (drawing 2015-09-09)
PLUG_TIP_X, PLUG_REAR_X = -14.7, 4.1
PLUG_WIDTH, PLUG_HEIGHT = 12.05, 4.5
PLUG_TOP_Z = PCB_THICKNESS + 3.25  # shell top is 3.25 above the PCB top face
PLUG_EXPOSED_LENGTH = 12.0

# Shell
BOARD_GAP = 0.3
WALL = 1.6
FLOOR = 1.2
LID = 1.2
FLOOR_Z = -1.5  # plug posts reach 1.25 below the PCB
CEILING_Z = PLUG_TOP_Z + 0.15
PLUG_SLOT_GAP = 0.2

LIP_THICKNESS, LIP_DEPTH, LIP_GAP = 1.2, 1.7, 0.1
SNAP_X_RANGE = (25.0, 55.0)
SNAP_Z = CEILING_Z - 1.0
SNAP_RIDGE_RADIUS, SNAP_GROOVE_RADIUS = 0.4, 0.45

POST_RADIUS, PIN_RADIUS = 1.6, 0.95
PIN_TIP_Z = -0.9
BOSS_RADIUS, SOCKET_RADIUS = 2.0, 1.25
LED_HOLE_RADIUS = 0.75

INNER_X0, INNER_X1 = -BOARD_GAP, PCB_LENGTH + BOARD_GAP
INNER_Y0, INNER_Y1 = -BOARD_GAP, PCB_WIDTH + BOARD_GAP
OUTER_X0 = PLUG_TIP_X + PLUG_EXPOSED_LENGTH
OUTER_X1 = INNER_X1 + WALL
OUTER_Y0, OUTER_Y1 = INNER_Y0 - WALL, INNER_Y1 + WALL
OUTER_Z0, OUTER_Z1 = FLOOR_Z - FLOOR, CEILING_Z + LID
INNER_CORNER_RADIUS = PCB_CORNER_RADIUS + BOARD_GAP
OUTER_CORNER_RADIUS = INNER_CORNER_RADIUS + WALL
PCB_MID_Y = PCB_WIDTH / 2


def box(x0, x1, y0, y1, z0, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def rounded_box(x0, x1, y0, y1, z0, z1, radius):
    solid = box(x0, x1, y0, y1, z0, z1)
    vertical = [e for e in solid.Edges
                if abs(e.Vertexes[0].Z - e.Vertexes[1].Z) > 1e-6]
    return solid.makeFillet(radius, vertical)


def cylinder_z(x, y, radius, z0, z1):
    return Part.makeCylinder(radius, z1 - z0, V(x, y, z0))


def cylinder_x(x0, x1, y, z, radius):
    return Part.makeCylinder(radius, x1 - x0, V(x0, y, z), V(1, 0, 0))


def build_tray():
    tray = rounded_box(OUTER_X0, OUTER_X1, OUTER_Y0, OUTER_Y1,
                       OUTER_Z0, CEILING_Z, OUTER_CORNER_RADIUS)
    tray = tray.cut(rounded_box(INNER_X0, INNER_X1, INNER_Y0, INNER_Y1,
                                FLOOR_Z, CEILING_Z, INNER_CORNER_RADIUS))
    half_slot = PLUG_WIDTH / 2 + PLUG_SLOT_GAP
    tray = tray.cut(box(OUTER_X0 - 1, 0, PCB_MID_Y - half_slot,
                        PCB_MID_Y + half_slot,
                        PLUG_TOP_Z - PLUG_HEIGHT - PLUG_SLOT_GAP, CEILING_Z))
    for x, y in MOUNT_HOLES:
        tray = tray.fuse(cylinder_z(x, y, BOSS_RADIUS, FLOOR_Z, 0))
        tray = tray.cut(cylinder_z(x, y, SOCKET_RADIUS, FLOOR_Z, 0))
    for wall_y in (INNER_Y0, INNER_Y1):
        tray = tray.cut(cylinder_x(*SNAP_X_RANGE, wall_y, SNAP_Z,
                                   SNAP_GROOVE_RADIUS))
    # Fingernail notch at the rear for prying the lid off
    tray = tray.cut(box(OUTER_X1 - 0.8, OUTER_X1 + 1, PCB_MID_Y - 4,
                        PCB_MID_Y + 4, CEILING_Z - 0.8, CEILING_Z))
    return tray.removeSplitter()


def build_lid():
    lid = rounded_box(OUTER_X0, OUTER_X1, OUTER_Y0, OUTER_Y1,
                      CEILING_Z, OUTER_Z1, OUTER_CORNER_RADIUS)
    lip_z0 = CEILING_Z - LIP_DEPTH
    lip_y0, lip_y1 = INNER_Y0 + LIP_GAP, INNER_Y1 - LIP_GAP
    lip_x1 = INNER_X1 - LIP_GAP
    lid = lid.fuse([
        box(3, 77.5, lip_y0, lip_y0 + LIP_THICKNESS, lip_z0, CEILING_Z),
        box(3, 77.5, lip_y1 - LIP_THICKNESS, lip_y1, lip_z0, CEILING_Z),
        box(lip_x1 - LIP_THICKNESS, lip_x1, 3, PCB_WIDTH - 3, lip_z0,
            CEILING_Z),
        cylinder_x(*SNAP_X_RANGE, lip_y0 + LIP_GAP, SNAP_Z,
                   SNAP_RIDGE_RADIUS).cut(
            box(0, PCB_LENGTH, lip_y0, lip_y1, lip_z0, CEILING_Z)),
        cylinder_x(*SNAP_X_RANGE, lip_y1 - LIP_GAP, SNAP_Z,
                   SNAP_RIDGE_RADIUS).cut(
            box(0, PCB_LENGTH, lip_y0, lip_y1, lip_z0, CEILING_Z)),
    ])
    shoulder_z = PCB_THICKNESS + 0.05
    for x, y in MOUNT_HOLES:
        lid = lid.fuse(cylinder_z(x, y, POST_RADIUS, shoulder_z, CEILING_Z))
        lid = lid.fuse(cylinder_z(x, y, PIN_RADIUS, PIN_TIP_Z, shoulder_z))
    lid = lid.cut(cylinder_z(*LED_POSITION, LED_HOLE_RADIUS,
                             CEILING_Z - 1, OUTER_Z1 + 1))
    return lid.removeSplitter()


def build_board_reference():
    """PCB with the plug and the two largest parts, for fit checking only."""
    pcb = rounded_box(0, PCB_LENGTH, 0, PCB_WIDTH, 0, PCB_THICKNESS,
                      PCB_CORNER_RADIUS)
    for x, y in MOUNT_HOLES:
        pcb = pcb.cut(cylinder_z(x, y, MOUNT_HOLE_DIAMETER / 2, -1, 3))
    top = PCB_THICKNESS
    parts = [
        box(PLUG_TIP_X, PLUG_REAR_X, PCB_MID_Y - PLUG_WIDTH / 2,
            PCB_MID_Y + PLUG_WIDTH / 2, PLUG_TOP_Z - PLUG_HEIGHT,
            PLUG_TOP_Z).cut(box(0, 10, 0, PCB_WIDTH, -1, top)),
        box(1.35, 4.85, 5.35, 7.25, -1.25, 0),      # plug shield tab
        box(1.35, 4.85, 16.75, 18.65, -1.25, 0),    # plug shield tab
        box(25, 41, 4, 20, top, top + 1.6),         # U1 F133 incl. leads
        box(57.5, 69.5, 1.4, 13.4, top, top + 1.5),  # U6 AP6212
        box(8, 22, 0.5, 23.5, top, top + 1.45),     # regulators, inductors
        box(41.5, 73.5, 13.5, 23.3, top, top + 1.0).cut(
            cylinder_z(*MOUNT_HOLES[2], 2.0, 0, 5)),  # SD NAND, crystals
    ]
    return pcb.fuse(parts)


def main():
    doc = App.newDocument("f133_dongle_case")
    shapes = {"Tray": build_tray(), "Lid": build_lid(),
              "BoardReference": build_board_reference()}
    for name, shape in shapes.items():
        doc.addObject("Part::Feature", name).Shape = shape
        box_ = shape.BoundBox
        print("%-14s valid=%s solids=%d volume=%.0f mm3  %.1f x %.1f x %.1f"
              % (name, shape.isValid(), len(shape.Solids), shape.Volume,
                 box_.XLength, box_.YLength, box_.ZLength))
    doc.recompute()
    board = shapes["BoardReference"]
    print("interference tray/board %.3f mm3, lid/board %.3f mm3, "
          "tray/lid %.3f mm3"
          % (shapes["Tray"].common(board).Volume,
             shapes["Lid"].common(board).Volume,
             shapes["Tray"].common(shapes["Lid"]).Volume))
    doc.saveAs(os.path.join(OUT_DIR, "f133-dongle-case.FCStd"))
    for name, filename in (("Tray", "f133-dongle-case-tray"),
                           ("Lid", "f133-dongle-case-lid")):
        shapes[name].exportStep(os.path.join(OUT_DIR, filename + ".step"))
        Mesh.export([doc.getObject(name)],
                    os.path.join(OUT_DIR, filename + ".stl"))


main()
