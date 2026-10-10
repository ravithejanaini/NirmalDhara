"""docs/claims.md: every piece of support it names exists.

This cannot judge whether a test really proves the claim beside it: that is a person's reading. It
stops the list from citing a test that was renamed, a smoke-test row that is gone, or a phrase that
is no longer in the design document.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLAIMS = (ROOT / "docs" / "claims.md").read_text("utf-8")
ROWS = [line for line in CLAIMS.splitlines() if re.match(r"^\| \d+ \|", line)]


def test_there_are_forty_three_numbered_claims_each_with_support():
    numbers = [int(re.match(r"^\| (\d+) \|", row).group(1)) for row in ROWS]
    assert numbers == list(range(1, 44))
    for row in ROWS:
        assert re.search(r"`(tests/|smoke: |template: |file: |design: )", row), row[:60]


def test_every_test_it_cites_exists():
    cited = re.findall(r"`(tests/\w+\.py)::(\w+)`", CLAIMS)
    assert len(cited) >= 25
    for path, name in cited:
        source = (ROOT / path).read_text("utf-8")
        assert re.search(rf"^def {name}\(", source, re.M), f"{path} has no {name}"


def test_every_smoke_test_row_it_cites_is_in_the_record_and_passed():
    record = (ROOT / "docs" / "smoke-test.md").read_text("utf-8")
    cited = re.findall(r"`smoke: ([^`]+)`", CLAIMS)
    assert cited
    for step in cited:
        row = next((line for line in record.splitlines() if line.startswith(f"| {step} |")), None)
        assert row is not None, f"no smoke-test row '{step}'"
        assert row.rstrip().endswith("| pass |"), step
    assert "**Result: every step passed.**" in record


def test_every_resource_file_and_phrase_it_cites_exists():
    template = (ROOT / "template.yaml").read_text("utf-8")
    design = (ROOT / "DESIGN.md").read_text("utf-8")
    for resource in re.findall(r"`template: (\w+)`", CLAIMS):
        assert re.search(rf"^  {resource}:$", template, re.M), resource
    for path in re.findall(r"`file: ([^`]+)`", CLAIMS):
        assert (ROOT / path).exists(), path
    phrases = re.findall(r'`design: "([^"]+)"`', CLAIMS)
    assert len(phrases) >= 6
    for phrase in phrases:
        assert phrase in design, f'DESIGN.md does not say "{phrase}"'


def test_the_numbers_it_states_are_the_real_ones():
    import json
    sites = json.loads((ROOT / "data" / "hyderabad_sites.json").read_text("utf-8"))["sites"]
    assert len(sites) == 9 and all(site["source"].startswith("http") for site in sites)
    template = (ROOT / "template.yaml").read_text("utf-8")
    section = template.split("\nResources:\n", 1)[1].split("\nOutputs:\n", 1)[0]
    kinds = re.findall(r"^  \w+:\n    Type: ([\w:]+)", section, re.M)
    assert kinds.count("AWS::Serverless::Function") == 8
    assert kinds.count("AWS::DynamoDB::Table") == 3 and kinds.count("AWS::SQS::Queue") == 4
    assert "rate(15 minutes)" in template


def test_the_three_documents_do_not_say_what_was_reworded_away():
    readme = (ROOT / "README.md").read_text("utf-8")
    writeup = (ROOT / "docs" / "submission-writeup.md").read_text("utf-8")
    script = (ROOT / "docs" / "video-script.md").read_text("utf-8")
    narration = " ".join(line[2:] for line in script.splitlines() if line.startswith("> "))
    for text in (readme, writeup, narration):
        lowered = text.lower()
        assert "never lost" not in lowered
        assert "right now it shows" not in lowered
        assert "reviewed, run and tested by me" not in lowered
        assert not re.search(r"\b\d{3} (tests )?pass", lowered)
    assert "guardians" not in narration.lower()


def test_the_writeup_says_what_is_not_proven_and_names_only_services_that_are_deployed():
    writeup = (ROOT / "docs" / "submission-writeup.md").read_text("utf-8")
    long_version = writeup.split("## Long version")[1].split("## Short version")[0]
    assert "has not read a real photo" in long_version and "designed and not built" in long_version
    assert "No person is subscribed" in long_version
    aws = long_version.split("**AWS.**")[1].split("**AI tools.**")[0]
    for absent in ("CloudFront", "Rekognition", "IoT", "Cognito", "API Gateway"):
        assert absent not in aws, f"{absent} is not deployed"
    assert "Bedrock" not in aws                              # named only as the intended reader, under AI tools
    words = len(long_version.split())
    assert 250 <= words <= 380, words
