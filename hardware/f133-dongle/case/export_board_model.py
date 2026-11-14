"""Extract the mechanical facts the case needs from the KiCad board.

Run with:  python3 export_board_model.py   (needs KiCad's pcbnew module)
Writes board.json next to this script; build_case.py reads it.

Coordinates are converted to the case frame (mm): x = KiCad x - board left,
y = board bottom - KiCad y, so the USB plug points towards -x and y is up.
"""
import json
import os

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD_PATH = os.path.join(HERE, "..", "f133-dongle.kicad_pcb")

# Maximum body height above the board per footprint, from the part datasheets.
BODY_HEIGHT = {
    "C_0402_1005Metric": 0.55,
    "R_0402_1005Metric": 0.40,
    "C_0603_1608Metric": 0.90,
    "C_0805_2012Metric": 1.35,
    "L_0805_2012Metric": 1.35,
    "L_1008_2520Metric": 1.20,
    "LED_0603_1608Metric": 0.70,
    "SOT-23-5": 1.45,
    "SOT-23-6": 1.45,
    "Crystal_SMD_3215-2Pin_3.2x1.5mm": 0.90,
    "Crystal_SMD_3225-4Pin_3.2x2.5mm": 0.80,
    "LGA-8_8x6mm_P1.27mm_SD_NAND": 0.90,
    "AMPAK_AP62xx_12x12mm": 1.60,
    "eLQFP-128_14x14mm_P0.4mm_EP5.72mm": 1.60,
}
COURTYARD_MARGIN = 0.25  # KiCad courtyards sit this far outside the body/pads

mm = pcbnew.ToMM


def main():
    board = pcbnew.LoadBoard(BOARD_PATH)
    outline = [d for d in board.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts]
    xs = [mm(p.x) for d in outline for p in (d.GetStart(), d.GetEnd())]
    ys = [mm(p.y) for d in outline for p in (d.GetStart(), d.GetEnd())]
    left, right, top, bottom = min(xs), max(xs), min(ys), max(ys)

    def local(x, y):
        return round(x - left, 3), round(bottom - y, 3)

    model = {
        "length": round(right - left, 3),
        "width": round(bottom - top, 3),
        "thickness": mm(board.GetDesignSettings().GetBoardThickness()),
        "mount_holes": [], "test_pads": [], "components": [],
    }
    for fp in sorted(board.GetFootprints(), key=lambda f: f.GetReference()):
        ref = fp.GetReference()
        name = fp.GetFPID().GetLibItemName().wx_str()
        x, y = local(mm(fp.GetPosition().x), mm(fp.GetPosition().y))
        if name.startswith("MountingHole"):
            pad = next(iter(fp.Pads()))
            model["mount_holes"].append({"ref": ref, "x": x, "y": y, "diameter": mm(pad.GetDrillSize().x)})
        elif name.startswith("TestPoint"):
            model["test_pads"].append({"ref": ref, "net": fp.GetValue(), "x": x, "y": y})
        elif ref == "D1":
            model["led"] = {"x": x, "y": y}
        if name in BODY_HEIGHT:
            yard = fp.GetCourtyard(pcbnew.F_CrtYd).BBox()
            x0, y1 = local(mm(yard.GetLeft()) + COURTYARD_MARGIN, mm(yard.GetTop()) + COURTYARD_MARGIN)
            x1, y0 = local(mm(yard.GetRight()) - COURTYARD_MARGIN, mm(yard.GetBottom()) - COURTYARD_MARGIN)
            model["components"].append({"ref": ref, "x0": x0, "x1": x1, "y0": y0, "y1": y1,
                                        "height": BODY_HEIGHT[name]})
    plug = board.FindFootprintByReference("J1")
    model["plug_center_y"] = local(0, mm(plug.GetPosition().y))[1]
    antenna = board.FindFootprintByReference("AE1").GetCourtyard(pcbnew.F_CrtYd).BBox()
    model["antenna_x0"] = local(mm(antenna.GetLeft()), 0)[0]
    with open(os.path.join(HERE, "board.json"), "w") as out:
        json.dump(model, out, indent=1)
        out.write("\n")
    print("board %.2f x %.2f, %d holes, %d components, tallest %.2f mm"
          % (model["length"], model["width"], len(model["mount_holes"]), len(model["components"]),
             max(c["height"] for c in model["components"])))


main()
