"""docs/architecture.svg may show only what template.yaml deploys, and must leave nothing out."""

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import make_architecture as arch  # noqa: E402

TEMPLATE = (ROOT / "template.yaml").read_text("utf-8")


def template_resources():
    """{logical id: type} for the template's resources, read without a YAML parser's tag handling."""
    section = TEMPLATE.split("\nResources:\n", 1)[1].split("\nOutputs:\n", 1)[0]
    return dict(re.findall(r"^  (\w+):\n    Type: ([\w:]+)", section, re.M))


RESOURCES = template_resources()


def test_the_template_was_read():
    assert len(RESOURCES) > 25 and RESOURCES["Bus"] == "AWS::Events::EventBus"


def test_every_resource_a_solid_box_names_exists_in_the_template():
    for key, node in arch.NODES.items():
        for resource in node[7]:
            assert resource in RESOURCES, f"{key}: {resource} is not in template.yaml"


def test_a_box_is_solid_exactly_when_it_stands_for_deployed_resources():
    for key, node in arch.NODES.items():
        assert (node[6] == "deployed") == bool(node[7]), key


def test_every_function_in_the_template_is_in_the_picture_once():
    functions = {r for r, t in RESOURCES.items() if t == "AWS::Serverless::Function"}
    shown = [r for n in arch.NODES.values() for r in n[7] if r in functions]
    assert sorted(shown) == sorted(functions)


def test_every_table_queue_topic_bucket_and_machine_is_shown_except_plumbing():
    plumbing = {"WorkflowDeadLetters"}                      # failure queues are drawn as part of what they guard
    kinds = ("AWS::DynamoDB::Table", "AWS::SQS::Queue", "AWS::SNS::Topic", "AWS::S3::Bucket",
             "AWS::StepFunctions::StateMachine", "AWS::Serverless::StateMachine", "AWS::Events::EventBus")
    wanted = {r for r, t in RESOURCES.items() if t in kinds} - plumbing
    shown = {r for n in arch.NODES.values() for r in n[7]}
    assert wanted <= shown, sorted(wanted - shown)


def test_the_cloudfront_resources_are_drawn_dashed_because_they_are_off():
    assert "EnableCloudFront" in TEMPLATE and 'Default: "false"' in TEMPLATE
    assert arch.NODES["cf"][6] == "designed" and not arch.NODES["cf"][7]


def test_every_arrow_joins_two_real_boxes_and_starts_and_ends_at_their_edges():
    def touches(point, node):
        x, y, w, h = node[:4]
        px, py = point
        on_x = (abs(px - x) < 2 or abs(px - (x + w)) < 2) and y - 2 <= py <= y + h + 2
        on_y = (abs(py - y) < 2 or abs(py - (y + h)) < 2) and x - 2 <= px <= x + w + 2
        return on_x or on_y

    for a, b, _, _, points in arch.EDGES:
        assert a in arch.NODES and b in arch.NODES
        assert touches(points[0], arch.NODES[a]), (a, b, "start")
        assert touches(points[-1], arch.NODES[b]), (a, b, "end")


def test_nothing_overlaps_and_everything_fits_in_the_drawing():
    boxes = list(arch.NODES.items())
    for key, (x, y, w, h, *_rest) in boxes:
        assert 0 <= x and x + w <= arch.W and 0 <= y and y + h <= arch.H - 40, key
    for i, (ka, (xa, ya, wa, ha, *_)) in enumerate(boxes):
        for kb, (xb, yb, wb, hb, *_) in boxes[i + 1:]:
            apart = xa + wa <= xb or xb + wb <= xa or ya + ha <= yb or yb + hb <= ya
            assert apart, f"{ka} overlaps {kb}"


def test_the_written_file_is_current_and_text_is_at_least_fourteen_pixels():
    written = (ROOT / "docs" / "architecture.svg").read_text("utf-8")
    assert written == arch.svg(), "run python scripts/make_architecture.py"
    assert all(int(s) >= 14 for s in re.findall(r'font-size="(\d+)"', written))
    assert "<title" in written and "<desc" in written


def test_a_dashed_box_never_carries_the_solid_style():
    svg = arch.svg()
    for key, node in arch.NODES.items():
        block = re.search(rf'<g id="node-{key}">(.*?)</g>', svg, re.S).group(1)
        assert ("stroke-dasharray" in block) == (node[6] == "designed"), key
