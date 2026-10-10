"""Rewrite the test inventory in DESIGN.md section 18 from what pytest collects.

    python scripts/update_design_tests.py          # rewrites the block between the markers
    python scripts/update_design_tests.py --check  # exits 1 if the block is out of date

The counts come from `pytest --collect-only`, never from a person, so they cannot drift.
Each test file needs a one-line description below: tests/test_design_doc.py fails if a file has
none, so a new test file cannot be added without saying what it covers.
"""

import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "DESIGN.md"
START, END = "<!-- tests:start -->", "<!-- tests:end -->"

DESCRIPTIONS = {
    "test_accessibility.py": "Page order, type floor, touch targets, the pinned Close button, reduced motion, names on controls",
    "test_alerts.py": "Who is alerted, the repeat rule, wording, the stand-down, no sentence with two \"and\"s",
    "test_architecture.py": "The picture shows only what the template deploys and leaves out no function",
    "test_claims.py": "Every test, smoke-test row, resource, file and phrase cited in docs/claims.md exists",
    "test_camera_simulation.py": "The simulated cameras: both depth methods are exact on a level view, only three marks survive a steep one, and the result is labelled simulated",
    "test_change.py": "Camera frame gate",
    "test_contrast.py": "Every colour pairing in use meets its contrast minimum",
    "test_core.py": "Bands, passability, prediction",
    "test_data_js.py": "The page's file reading, diffing, stale notice and polling, run with Node",
    "test_deploy_web.py": "Which files are uploaded and with what headers; the map file can never be overwritten",
    "test_design.py": "Geohash, volume curve, map file, and the properties listed below",
    "test_design_doc.py": "This document: every source file is in section 1 and the test inventory is current",
    "test_engine.py": "Engine against an in-memory table and bus: order, outbox recovery, repeated messages, lost races",
    "test_evaluation.py": "The evaluation and photo scripts on drawn scenes with a stand-in reader; a dangerous miss is counted",
    "test_flood.py": "Reactor, tick and notifier together against in-memory services: every row of 8.5, failed send",
    "test_gauge.py": "The learnt gauge on a made wall: a day it never saw read to within the gap between the days it did, a floor or ceiling past what it learnt, unmoved by brighter or dimmer light, no step inside a day, and unreadable when no level explains the picture",
    "test_gate_demo.py": "The change gate demonstration counts what is sent, and no footage, frame or strip is tracked by git",
    "test_glyph.py": "The depth glyph's rules: level, colour, rings, staleness, spoken label, run with Node",
    "test_guide.py": "Summary line, welcome and the key's examples, run with Node",
    "test_history.py": "What counts as a flood, ranking, and the history writer",
    "test_intake.py": "Photo checks, crop, blur, signed links",
    "test_map_style.py": "The map style uses only token colours and none of the flood palette",
    "test_multi_reference.py": "How several strips in one view are joined on the real flood: each strip's record from days left out, the middle of three, the mean of two, and the report says which camera was run once",
    "test_multiview.py": "Several objects and several cameras on made scenes: marks of known height, length and width fix the camera, a waterline on a post is a height at any angle, two cameras give a floating thing's speed, and one wild reading in three cannot move the answer",
    "test_multiview_simulation.py": "The simulation of several marks, objects and cameras measures what its report says, and the report is labelled simulated",
    "test_offline.py": "The offline worker keeps and marks what it should, the manifest and icons are installable, a kept map file shows as a refresh that did not happen",
    "test_offenders.py": "The repeat-floods page ranks as the Python does, on random cities, run with Node",
    "test_publisher.py": "Map file: every site, skipped when unchanged, losing a race, 500 sites",
    "test_rain.py": "Request building, parsing, grid grouping",
    "test_reader.py": "Request shape, refusal, throttling, server error, no connection, configuration error",
    "test_rehearsal.py": "The local video rehearsal shows the real replay's moments and reaches only this machine; the pre-flight only reads",
    "test_replay.py": "Replay schedule and what reset clears and leaves",
    "test_learn_river_cameras.py": "How the learnt gauge is judged on the real flood: never on a day it learnt from, levels, floors and no-answers counted apart, and the report says which cameras were run once",
    "test_river_camera.py": "How the real-flood test is scored: a one-way curve from row to level, errors only on days it did not see, and the pictures credited and kept out of the repository",
    "test_rules_match.py": "The browser's passability rules equal bands.py on 400 cases",
    "test_scenario.py": "The evening scenario against the real state and workflow code",
    "test_section.py": "The cross-section drawing: scale, limits, colour, run with Node",
    "test_seed.py": "Seeding refuses unsourced sites, touches only registry fields, changes nothing twice",
    "test_serve_web.py": "The development stand-in for the map file",
    "test_sheet.py": "The site sheet's words against the Python rules, run with Node",
    "test_site.py": "The interim site host: what it serves, and the paths and methods it refuses",
    "test_state.py": "Transitions, trust, jump hold, fusion, a repeated reading",
    "test_video_script.py": "The video script: length, the spoken disclosures, cut points the replay really produces, real commands",
    "test_waterline.py": "The waterline detector on rendered scenes: found within 3 cm by day and night, dry reported dry, a shadow and a parked vehicle not taken for water, a changed view refused, and the tracker holds through a blind reading",
    "test_workflow.py": "Plan rules, photo re-asks, escalation, blocked time, closing, stand-down, alert ids",
}


def collected():
    out = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider", "tests"],
                         cwd=ROOT, capture_output=True, text=True, encoding="utf-8").stdout
    return Counter(m.group(1) for m in re.finditer(r"^tests[/\\](\w+\.py)::", out, re.M))


def inventory(counts=None):
    counts = collected() if counts is None else counts
    missing = sorted(set(counts) - set(DESCRIPTIONS))
    if missing:
        raise SystemExit(f"add a description to scripts/update_design_tests.py for: {missing}")
    rows = [f"| `{name}` | {counts[name]} | {DESCRIPTIONS[name]} |" for name in sorted(counts)]
    return "\n".join(["| File | Tests | Covers |", "|---|---|---|", *rows,
                      f"| **Total** | **{sum(counts.values())}** | Collected by `pytest --collect-only` |"])


def current_block(text):
    return text.split(START, 1)[1].split(END, 1)[0].strip()


def main():
    text = DOC.read_text(encoding="utf-8")
    fresh = inventory()
    if "--check" in sys.argv:
        return 0 if current_block(text) == fresh else 1
    head, rest = text.split(START, 1)
    tail = rest.split(END, 1)[1]
    DOC.write_text(f"{head}{START}\n{fresh}\n{END}{tail}", encoding="utf-8", newline="\n")
    print(f"section 18 now lists {sum(collected().values())} tests")
    return 0


if __name__ == "__main__":
    sys.exit(main())
