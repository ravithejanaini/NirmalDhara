"""Write data/rule-cases.json: the answers of src/nirmaldhara/bands.py for 400 inputs.

web/rules-check.html runs the same inputs through web/rules.js and compares. Run this again
after any change to bands.py:

    python scripts/make_rule_cases.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from nirmaldhara.bands import band_for, passability  # noqa: E402

CONFIDENCES = (0.3, 0.59, 0.6, 0.9)
EDGE_DEPTHS = (0, 5, 11, 11.9, 12, 14.9, 15, 15.1, 19.9, 20, 20.1, 29.9, 30, 30.1,
               40, 49.9, 50, 50.1, 60, 100)


def cases():
    out = []
    # Every 2 cm from 0 to 78, still and moving water, four confidences: 320 cases.
    for depth in range(0, 80, 2):
        for confidence in CONFIDENCES:
            for moving in (False, True):
                out.append((max(0, depth - 6), depth, confidence, moving))
    # Depths on and either side of every limit, a range 6 cm wide below each: 80 cases.
    for high in EDGE_DEPTHS:
        for confidence in CONFIDENCES:
            out.append((max(0, high - 6), high, confidence, False))
    return [{"low": low, "high": high, "confidence": confidence, "moving": moving,
             "band": band_for(high), "answers": passability(low, high, confidence, moving)}
            for low, high, confidence, moving in out]


def build():
    return {"source": "src/nirmaldhara/bands.py", "cases": cases()}


if __name__ == "__main__":
    out = Path(__file__).resolve().parents[1] / "data" / "rule-cases.json"
    document = build()
    out.write_text(json.dumps(document, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"wrote {out} with {len(document['cases'])} cases")
