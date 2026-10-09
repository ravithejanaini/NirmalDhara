"""DESIGN.md describes the code as it is: every source file is in section 1, and the test
inventory in section 18 is what pytest collects. To fix a failure here:

    python scripts/update_design_tests.py
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import update_design_tests as inventory  # noqa: E402

DOC = (ROOT / "DESIGN.md").read_text("utf-8")


def section(number):
    start = DOC.index(f"\n## {number}. ")
    end = DOC.index("\n## ", start + 1)
    return DOC[start:end]


def test_every_source_file_appears_in_section_one():
    one = section(1)
    missing = []
    for path in sorted((ROOT / "src").rglob("*.py")):
        if "egg-info" in str(path) or path.name == "__init__.py":
            continue
        relative = path.relative_to(ROOT / "src").as_posix()
        if relative not in one:
            missing.append(relative)
    assert missing == [], f"not in DESIGN.md section 1: {missing}"


def test_every_page_script_and_state_machine_file_is_named_somewhere_in_the_document():
    missing = []
    for pattern in ("web/*.js", "scripts/*.py", "statemachine/*.json"):
        for path in sorted(ROOT.glob(pattern)):
            if path.name not in DOC:
                missing.append(f"{path.parent.name}/{path.name}")
    assert missing == [], f"not mentioned in DESIGN.md: {missing}"


def test_section_one_does_not_call_deployed_things_planned():
    one = section(1)
    for stale in ("not deployed", "handler planned", "written, parses"):
        assert stale not in one, stale


def test_every_test_file_has_a_description():
    counts = inventory.collected()
    assert set(counts) <= set(inventory.DESCRIPTIONS), sorted(set(counts) - set(inventory.DESCRIPTIONS))
    assert set(inventory.DESCRIPTIONS) <= set(counts) | {"test_design_doc.py"}, "a description for a file that is gone"


def test_the_test_inventory_in_section_eighteen_is_what_pytest_collects():
    assert inventory.current_block(DOC) == inventory.inventory(), "run python scripts/update_design_tests.py"


def test_no_test_count_is_written_into_the_prose():
    """A number typed into a sentence goes stale. The inventory block is the only place counts live."""
    prose = DOC.replace(inventory.current_block(DOC), "")
    assert not re.search(r"\b\d{2,3} tests\b", prose), re.findall(r".{30}\b\d{2,3} tests\b", prose)
