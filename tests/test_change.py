import numpy as np
from PIL import Image

from nirmaldhara.change import ChangeGate

INTERVAL = 60  # seconds between frames


def scene(rng, noise=3.0, brightness=0.0, patch=0):
    """A fixed street-like gradient with sensor noise and an optional dark patch."""
    base = np.tile(np.linspace(80, 160, 320, dtype=np.float32), (240, 1))
    frame = base + brightness + rng.normal(0, noise, base.shape)
    if patch:
        frame[100:100 + patch, 100:100 + patch] = 30
    return Image.fromarray(np.clip(frame, 0, 255).astype(np.uint8))


def sent_count(frames):
    gate = ChangeGate()
    return sum(gate.should_send(f, i * INTERVAL) for i, f in enumerate(frames))


def test_still_scene_sends_only_keepalives():
    rng = np.random.default_rng(0)
    frames = [scene(rng) for _ in range(120)]
    # 120 frames over two hours: the first frame plus one keep-alive every 5 minutes.
    assert sent_count(frames) == 24


def test_brightness_drift_alone_does_not_trigger():
    rng = np.random.default_rng(1)
    frames = [scene(rng, brightness=i * 0.5) for i in range(60)]
    assert sent_count(frames) == 12


def test_object_that_stays_is_sent_on_its_second_frame():
    rng = np.random.default_rng(2)
    gate = ChangeGate()
    # Frames 10 seconds apart, so no keep-alive falls inside the test.
    for i in range(20):
        gate.should_send(scene(rng), i * 10)
    assert not gate.should_send(scene(rng, patch=40), 200)
    assert gate.should_send(scene(rng, patch=40), 210)


def test_object_that_passes_is_not_sent():
    rng = np.random.default_rng(4)
    gate = ChangeGate()
    for i in range(20):
        gate.should_send(scene(rng), i * 10)
    assert not gate.should_send(scene(rng, patch=40), 200)
    assert not gate.should_send(scene(rng), 210)
    assert not gate.should_send(scene(rng), 220)


def test_slow_build_up_is_caught():
    rng = np.random.default_rng(3)
    gate = ChangeGate()
    for i in range(20):
        gate.should_send(scene(rng), i * 10)
    # A patch growing 2 pixels a frame: each step is small, the total is not.
    sent_at = [p for i, p in enumerate(range(2, 60, 2))
               if gate.should_send(scene(rng, patch=p), 200 + i * 10)]
    assert sent_at and sent_at[0] <= 30
