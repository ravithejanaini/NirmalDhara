"""A rehearsal of the submission: check everything the form will need, and change nothing.

    python scripts/preflight.py                         # every check
    python scripts/preflight.py --video https://youtu.be/…   # also checks the video link
    python scripts/preflight.py --skip-tests            # faster: do not run the test suite

It reads the repository, GitHub, the live site and the AWS stack. It never writes, sends,
uploads or submits. Each line is one of:

    ok    as it should be
    TODO  something only you can do, or that is not done yet
    FAIL  something is wrong and should be fixed before submitting
"""

import argparse
import gzip
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

REPO = "https://github.com/ravithejanaini/NirmalDhara"
EVENT_START, EVENT_END = date(2026, 10, 8), date(2026, 10, 11)
SECRET = re.compile(r"AKIA[0-9A-Z]{16}|sk-ant-[A-Za-z0-9_-]{20,}|aws_secret_access_key\s*=\s*\S{20,}")
RESULTS = []


def say(level, what, detail=""):
    RESULTS.append(level)
    print(f"  {level:<4}  {what}" + (f": {detail}" if detail else ""))


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8").stdout.strip()


def fetch(url, timeout=25):
    request = urllib.request.Request(url, headers={"User-Agent": "nirmaldhara-preflight"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, b""
    except Exception as error:                               # no network, DNS, timeout
        return None, str(error).encode()


def check_repository():
    print("Repository")
    dirty = git("status", "--porcelain")
    say("ok" if not dirty else "FAIL", "Nothing uncommitted", "" if not dirty else f"{len(dirty.splitlines())} files changed")
    git("fetch", "--quiet", "origin")
    ahead = git("rev-list", "--count", "origin/main..HEAD")
    say("ok" if ahead == "0" else "FAIL", "Everything is pushed", "" if ahead == "0" else f"{ahead} commits not on GitHub")
    status, _ = fetch(REPO)
    say("ok" if status == 200 else "FAIL", "The repository is public", "" if status == 200 else f"GitHub answered {status} without signing in")
    dates = [datetime.fromisoformat(d).date() for d in git("log", "--format=%aI").splitlines()]
    inside = all(EVENT_START <= d <= EVENT_END for d in dates)
    say("ok" if inside else "FAIL", f"All {len(dates)} commits are dated inside the event (8 to 11 Oct)",
        f"first {min(dates)}, last {max(dates)}")
    say("ok" if (ROOT / "LICENSE").exists() else "FAIL", "A licence file")
    readme = (ROOT / "README.md").read_text("utf-8")
    for heading in ("## Try it", "## Run the tests", "## What is built", "## Limits", "## AI tools used"):
        say("ok" if heading in readme else "FAIL", f"README has \"{heading[3:]}\"")
    hits = [line for line in git("grep", "-nIE", SECRET.pattern).splitlines() if line]
    history = SECRET.search(git("log", "-p", "--all")) is not None
    say("ok" if not hits and not history else "FAIL", "No key or secret in the files or the history",
        "" if not hits and not history else "found one: rotate it before anything else")


def check_tests(skip):
    print("Tests")
    if skip:
        return say("TODO", "Run the tests", "skipped with --skip-tests")
    out = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"], cwd=ROOT,
                         capture_output=True, text=True, encoding="utf-8").stdout.strip().splitlines()[-1]
    say("ok" if " passed" in out and "failed" not in out and "error" not in out else "FAIL", "The whole suite passes", out)


def check_site():
    print("Live site")
    import stack
    try:
        aws = stack.session()
        outputs, resources = stack.outputs(aws), stack.resources(aws)
    except Exception as error:
        return say("FAIL", "The AWS stack can be read", str(error)[:120])
    status_text = aws.client("cloudformation").describe_stacks(StackName=stack.STACK)["Stacks"][0]["StackStatus"]
    say("ok" if status_text.endswith("COMPLETE") and "ROLLBACK" not in status_text else "FAIL", "The stack is healthy", status_text)
    url = outputs["SiteUrl"].rstrip("/")
    readme = (ROOT / "README.md").read_text("utf-8")
    say("ok" if url in readme else "FAIL", "The README gives the live address", url)
    status, _ = fetch(url + "/")
    say("ok" if status == 200 else "FAIL", "The map page loads", f"HTTP {status}")
    status, _ = fetch(url + "/offenders.html")
    say("ok" if status == 200 else "FAIL", "The repeat floods page loads", f"HTTP {status}")
    status, raw = fetch(url + "/data/hyderabad.json")
    if status != 200:
        say("FAIL", "The map file loads", f"HTTP {status}")
    else:
        doc = json.loads(gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw)
        states = sorted({row[4] for row in doc["sites"]})
        age = int(datetime.now(timezone.utc).timestamp()) - doc["generated_at"]
        say("ok" if len(doc["sites"]) == 9 else "FAIL", "The map file has the nine sites", f"{len(doc['sites'])} sites")
        say("ok" if age < 20 * 60 else "FAIL", "The map file is being kept current", f"written {age // 60} min ago")
        say("ok" if states == ["CLEAR"] else "TODO", "The public map is not left showing a replay",
            "all clear" if states == ["CLEAR"] else f"states now {states}: run scripts/reset.py --go --forget-floods when you have finished recording")
    running = aws.client("stepfunctions").list_executions(stateMachineArn=resources["FloodStateMachine"], statusFilter="RUNNING")["executions"]
    say("ok" if not running else "TODO", "No flood timer left running", "" if not running else f"{len(running)} running")
    sqs = aws.client("sqs")
    for name in ("EngineDeadLetters", "WorkflowDeadLetters"):
        queue = sqs.get_queue_url(QueueName=resources[name].split("/")[-1])["QueueUrl"]
        waiting = int(sqs.get_queue_attributes(QueueUrl=queue, AttributeNames=["ApproximateNumberOfMessages"])["Attributes"]["ApproximateNumberOfMessages"])
        say("ok" if waiting == 0 else "FAIL", f"Nothing in the failure queue {name}", "" if waiting == 0 else f"{waiting} messages")
    alarms = aws.client("cloudwatch").describe_alarms(StateValue="ALARM")["MetricAlarms"]
    mine = [a["AlarmName"] for a in alarms if stack.STACK in a["AlarmName"]]
    say("ok" if not mine else "FAIL", "No alarm is ringing", ", ".join(mine))
    subscribers = [s for s in aws.client("sns").list_subscriptions_by_topic(TopicArn=resources["AlertsTopic"])["Subscriptions"]
                   if s["SubscriptionArn"].startswith("arn:")]
    say("ok" if subscribers else "TODO", "Someone is subscribed to the alerts", "" if subscribers else
        "nobody yet (task INF-07). Optional: the video can show the test record instead of an inbox")
    return aws


def check_video(url):
    print("Video and writeup")
    script = (ROOT / "docs" / "video-script.md").read_text("utf-8")
    words = sum(len(line[2:].split()) for line in script.splitlines() if line.startswith("> "))
    say("ok", "The video script is written", f"{words} words of narration, about {words * 60 // 150 // 60}:{words * 60 // 150 % 60:02d} of speech")
    if not url:
        say("TODO", "Record the video and upload it", "then run again with --video <link>")
    else:
        status, _ = fetch(url)
        known = re.match(r"https://(www\.)?(youtube\.com|youtu\.be)/", url) is not None
        say("ok" if status == 200 else "FAIL", "The video link opens without signing in", f"HTTP {status}")
        say("ok" if known else "TODO", "The link is a YouTube link", "" if known else "check what the form accepts")
        say("TODO", "Watch it once signed out: under 3:00, the replay caption shows, the map credit is readable")
    writeup = (ROOT / "docs" / "submission-writeup.md").read_text("utf-8")
    long_words = len(writeup.split("## Long version")[1].split("## Short version")[0].split())
    short_words = len(writeup.split("## Short version")[1].split())
    say("ok", "The writeup is written, in two lengths", f"{long_words} and {short_words} words")
    say("ok" if (ROOT / "docs" / "claims.md").exists() else "FAIL", "Every claim is listed with its support")
    say("TODO", "Confirm the form's closing time and its length limits", "the event page gives neither (task SUB-08)")


def check_account(aws):
    print("After you submit")
    if aws is None:
        return
    try:
        identity = aws.client("sts").get_caller_identity()["Arn"].split("/")[-1]
        iam = aws.client("iam")
        policies = [p["PolicyName"] for p in iam.list_attached_user_policies(UserName=identity)["AttachedPolicies"]]
        keys = iam.list_access_keys(UserName=identity)["AccessKeyMetadata"]
        mfa = iam.list_mfa_devices(UserName=identity)["MFADevices"]
    except Exception as error:
        return say("TODO", "Review the IAM user", str(error)[:100])
    admin = "AdministratorAccess" in policies
    say("TODO" if admin else "ok", f"Remove AdministratorAccess from {identity}", "still attached; leave it until you have submitted" if admin else "already removed")
    for key in keys:
        days = (datetime.now(timezone.utc) - key["CreateDate"]).days
        say("TODO", "Rotate the access key on this machine", f"created {days} day(s) ago, {key['Status'].lower()}")
    say("ok" if mfa else "TODO", "The IAM user has MFA on its console login", "" if mfa else "not set")
    say("TODO", "Decide whether to keep the stack", "deleting it stops all cost: sam delete --stack-name nirmaldhara --region ap-south-1")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--video", help="the uploaded video's link")
    parser.add_argument("--skip-tests", action="store_true")
    args = parser.parse_args()
    check_repository()
    check_tests(args.skip_tests)
    aws = check_site()
    check_video(args.video)
    check_account(aws)
    fails, todos = RESULTS.count("FAIL"), RESULTS.count("TODO")
    print(f"\n{RESULTS.count('ok')} ok, {todos} to do, {fails} wrong.")
    print("Not ready: fix what is marked FAIL." if fails else
          "Nothing is wrong. What is left is marked TODO." if todos else "Ready to submit.")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
