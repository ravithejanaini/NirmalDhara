"""scripts/gate_demo.py: counting what the change gate sends, and keeping the footage out of the repository."""

import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import gate_demo  # noqa: E402


def frames(folder, scenes):
    """Write frames: each scene is (count, base grey level), with a little sensor noise on every frame."""
    rng = np.random.default_rng(5)
    pattern = rng.integers(0, 60, size=(90, 160))
    n = 0
    for count, level in scenes:
        scene = np.roll(pattern, level, axis=1) + level
        for _ in range(count):
            noisy = np.clip(scene + rng.normal(0, 2, scene.shape), 0, 255).astype("uint8")
            Image.fromarray(noisy).convert("RGB").save(folder / f"{n:05d}.jpg", quality=92)
            n += 1


def test_a_still_scene_sends_its_first_frame_and_nothing_more(tmp_path):
    frames(tmp_path, [(40, 20)])
    counts = gate_demo.summary(gate_demo.run(tmp_path, fps=2))
    assert counts == {"seen": 40, "sent": 1, "saved": 1 - 1 / 40}


def test_each_new_scene_is_sent_once_it_has_settled(tmp_path):
    frames(tmp_path, [(20, 20), (20, 90), (20, 150)])
    results = gate_demo.run(tmp_path, fps=2)
    sent = [r[0] for r in results if r[2]]
    assert len(sent) == 3 and sent[0] == 0
    assert 20 < sent[1] <= 23 and 40 < sent[2] <= 43            # a frame or two after each cut, not on it


def test_the_strip_holds_one_thumbnail_per_frame_sent(tmp_path):
    source = tmp_path / "in"
    source.mkdir()
    frames(source, [(20, 20), (20, 90)])
    results = gate_demo.run(source, fps=2)
    target = gate_demo.strip(results, tmp_path / "out" / "strip.jpg")
    with Image.open(target) as sheet:
        assert sheet.size == (gate_demo.THUMB[0] * 2, gate_demo.THUMB[1])
    assert gate_demo.strip([r for r in results if not r[2]], tmp_path / "none.jpg") is None


def test_the_sentence_is_the_one_the_task_asks_for():
    assert gate_demo.sentence("x", {"seen": 186, "sent": 23, "saved": 1 - 23 / 186}) == \
        "`x`: of 186 frames, 23 were sent (88% never left the camera)."


def test_the_report_quotes_the_figures_with_their_limits_and_credits():
    report = (ROOT / "docs" / "gate-demo.md").read_text("utf-8")
    credits = (ROOT / "samples" / "footage" / "CREDITS.md").read_text("utf-8")
    for row in ("| 186 | 23 | 88% |", "| 280 | 51 | 82% |", "| 129 | 12 | 91% |"):
        assert row in report
    assert "understate" in report and "not CCTV" in credits
    for video in ("030j7lSZ3cY", "izJR0sCbfPg", "kS2ivWlwSyo"):
        assert f"https://www.youtube.com/watch?v={video}" in credits
    assert credits.count("CC BY") >= 4


def test_no_video_frame_or_strip_is_tracked_by_git():
    tracked = subprocess.run(["git", "ls-files", "samples/footage", "docs/gate-demo"], cwd=ROOT,
                             capture_output=True, text=True).stdout.split()
    assert [name for name in tracked if not name.endswith(".md")] == []
    ignore = (ROOT / ".gitignore").read_text("utf-8")
    for rule in ("samples/footage/*.mp4", "samples/footage/frames/", "docs/gate-demo/"):
        assert rule in ignore, rule
