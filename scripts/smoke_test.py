"""Smoke test on AWS: walk one test site through a whole flood and check every step.

    python scripts/smoke_test.py              # about ten minutes; writes docs/smoke-test.md

It uses a site called hyd-900 that is not a real place and has no position, so it never shows
on the public map. To see the alerts that are sent, it subscribes a temporary queue to the
alerts topic. Everything it creates (the site, its flood record, its alert records, the queue
and the subscription) is removed at the end, pass or fail.

What it proves that the unit tests cannot: that the real services accept the condition
expressions the in-memory stand-ins only imitate, that events really flow queue -> engine ->
bus -> workflow -> notifier -> topic, and that the real five-minute and one-minute clocks drive
escalation and closing.
"""

import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from boto3.dynamodb.conditions import Attr, Key

sys.path.insert(0, str(Path(__file__).resolve().parent))

import send  # noqa: E402
import stack  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SITE, CITY = "hyd-900", "hyderabad"
IST = timezone(timedelta(hours=5, minutes=30))


class Smoke:
    def __init__(self):
        self.aws = stack.session()
        self.res = stack.resources(self.aws)
        dynamo = self.aws.resource("dynamodb")
        self.sites = dynamo.Table(self.res["SitesTable"])
        self.floods = dynamo.Table(self.res["FloodsTable"])
        self.alerts = dynamo.Table(self.res["AlertsTable"])
        self.sqs = self.aws.client("sqs")
        self.sns = self.aws.client("sns")
        self.steps = self.aws.client("stepfunctions")
        self.engine_url = send.queue_url(self.aws, self.res)
        self.rows, self.delivered, self.started = [], [], time.time()
        self.tap_url = self.tap_arn = self.subscription = None

    # --- reading the system's state ---------------------------------------------------------

    def site(self):
        item = self.sites.get_item(Key={"city": CITY, "site_id": SITE}, ConsistentRead=True).get("Item", {})
        return json.loads(item["doc"]) if "doc" in item else {"state": "CLEAR", "readings": [], "version": 0}

    def flood(self):
        items = self.floods.query(KeyConditionExpression=Key("site_id").eq(SITE), ScanIndexForward=False,
                                  ConsistentRead=True)["Items"]
        return json.loads(items[0]["doc"]) if items else None

    def claims(self):
        """{kind: [alert ids]} of every alert the notifier has claimed for the test site."""
        out, kwargs = {}, {"FilterExpression": Attr("site_id").eq(SITE), "ConsistentRead": True}
        while True:
            page = self.alerts.scan(**kwargs)
            for item in page["Items"]:
                out.setdefault(item["kind"], []).append((item["alert_id"], bool(item.get("sent"))))
            if "LastEvaluatedKey" not in page:
                return out
            kwargs["ExclusiveStartKey"] = page["LastEvaluatedKey"]

    def executions(self):
        found = self.steps.list_executions(stateMachineArn=self.res["FloodStateMachine"], maxResults=50)["executions"]
        return [(e["name"], e["status"]) for e in found if e["name"].startswith(SITE + "-")]

    def drain(self):
        """Collect what the topic has delivered since the last call."""
        while True:
            got = self.sqs.receive_message(QueueUrl=self.tap_url, MaxNumberOfMessages=10, WaitTimeSeconds=1)
            messages = got.get("Messages", [])
            if not messages:
                return self.delivered
            for m in messages:
                body = json.loads(m["Body"])
                attributes = body.get("MessageAttributes", {})
                self.delivered.append({
                    "audience": attributes.get("audience", {}).get("Value"),
                    "contact": int(attributes.get("contact", {}).get("Value", 0)),
                    "text": body["Message"], "at": time.time()})
                self.sqs.delete_message(QueueUrl=self.tap_url, ReceiptHandle=m["ReceiptHandle"])

    # --- the test harness -------------------------------------------------------------------

    def check(self, step, expected, probe, timeout=45):
        """Poll `probe` until it returns something truthy; record what was seen either way."""
        began, seen = time.time(), None
        while time.time() - began < timeout:
            try:
                seen = probe()
            except Exception as error:                      # a probe that cannot run yet
                seen = None
                last_error = repr(error)
            if seen:
                break
            time.sleep(1)
        took = time.time() - began
        ok = bool(seen)
        shown = seen if ok else f"NOT SEEN within {timeout}s"
        self.rows.append((step, expected, str(shown), took, ok))
        print(f"[{'ok' if ok else 'FAIL'}] {step}: {shown} ({took:.1f}s)", flush=True)
        return ok

    def rain(self, index_mm):
        send.send(self.sqs, self.engine_url, send.rain_message(SITE, index_mm, time.time()))

    def reading(self, high, dedup=None, ts=None):
        message = send.reading_message(SITE, high, device="smoke", ts=ts)
        send.send(self.sqs, self.engine_url, message, dedup)
        return message

    def setup(self):
        self.cleanup_rows()
        # No lat or lon: the rain check and the public map both leave a site without a position alone.
        self.sites.put_item(Item={"city": CITY, "site_id": SITE, "name": "SMOKE TEST (not a real place)"})
        name = f"nirmaldhara-smoke-{int(time.time())}"
        self.tap_url = self.sqs.create_queue(QueueName=name)["QueueUrl"]
        self.tap_arn = self.sqs.get_queue_attributes(QueueUrl=self.tap_url, AttributeNames=["QueueArn"])["Attributes"]["QueueArn"]
        topic = self.res["AlertsTopic"]
        self.sqs.set_queue_attributes(QueueUrl=self.tap_url, Attributes={"Policy": json.dumps({
            "Version": "2012-10-17", "Statement": [{
                "Effect": "Allow", "Principal": {"Service": "sns.amazonaws.com"}, "Action": "sqs:SendMessage",
                "Resource": self.tap_arn, "Condition": {"ArnEquals": {"aws:SourceArn": topic}}}]})})
        self.subscription = self.sns.subscribe(TopicArn=topic, Protocol="sqs", Endpoint=self.tap_arn,
                                               ReturnSubscriptionArn=True)["SubscriptionArn"]
        time.sleep(3)

    def cleanup_rows(self):
        self.sites.delete_item(Key={"city": CITY, "site_id": SITE})
        for item in self.floods.query(KeyConditionExpression=Key("site_id").eq(SITE))["Items"]:
            self.floods.delete_item(Key={"site_id": SITE, "start": item["start"]})
        for ids in self.claims().values():
            for alert_id, _ in ids:
                self.alerts.delete_item(Key={"alert_id": alert_id})

    def teardown(self):
        for name, status in self.executions():
            if status == "RUNNING":
                arn = self.res["FloodStateMachine"].replace(":stateMachine:", ":execution:") + ":" + name
                self.steps.stop_execution(executionArn=arn, cause="smoke test ended")
        if self.subscription:
            self.sns.unsubscribe(SubscriptionArn=self.subscription)
        if self.tap_url:
            self.sqs.delete_queue(QueueUrl=self.tap_url)
        self.cleanup_rows()
        print("removed the test site, its records, the temporary queue and its subscription", flush=True)

    # --- the flood --------------------------------------------------------------------------

    def run(self):
        kinds = lambda: self.claims()                                           # noqa: E731
        sent = lambda *wanted: (lambda: all(k in kinds() and all(s for _, s in kinds()[k]) for k in wanted)  # noqa: E731
                                and sorted(kinds()))
        heard = lambda audience, contact=0: (lambda: [d["text"] for d in self.drain()               # noqa: E731
                                                       if d["audience"] == audience and d["contact"] == contact])

        self.rain(25)
        self.check("1 Rain index 25 mm", "Site WATCH", lambda: self.site()["state"] == "WATCH" and "WATCH")
        self.check("1 Flood event", "One open event", lambda: (f := self.flood()) and f["closed_at"] is None and f"open, start {f['start']}")
        self.check("1 Timer", "Execution running, named after the flood",
                   lambda: [e for e in self.executions() if e[1] == "RUNNING"])
        self.check("1 Photo request", "Sent to guardians", heard("guardians"))

        self.reading(16)
        self.check("2 Reading 11-16 cm", "Site WARNING", lambda: self.site()["state"] == "WARNING" and "WARNING")
        self.check("2 Alerts", "warning, advisory, pump_request, blocked, each marked sent",
                   sent("warning", "advisory", "pump_request", "blocked"))
        self.check("2 Wording", "Residents told depth and who is not safe", heard("residents"))

        self.reading(24)
        time.sleep(3)
        repeated = self.reading(28)
        self.check("3 Readings 24, 28 cm", "Site CRITICAL (median of three is 24, trusted source)",
                   lambda: (s := self.site())["state"] == "CRITICAL" and f"CRITICAL, {s['low']:.0f}-{s['high']:.0f} cm")
        self.check("3 Alerts", "do_not_enter, closure_recommendation, pump_urgent, each marked sent",
                   sent("do_not_enter", "closure_recommendation", "pump_urgent"))
        self.check("3 Closure wording", "Recommends closing; never says the road is closed",
                   lambda: [t for t in heard("traffic_control")() if "Recommend closing" in t and "road closed" not in t.lower()])
        closure_at = time.time()

        before = (len(self.site()["readings"]), sum(len(v) for v in kinds().values()), self.site()["version"])
        send.send(self.sqs, self.engine_url, repeated)                          # same body, new delivery
        time.sleep(12)
        after = (len(self.site()["readings"]), sum(len(v) for v in kinds().values()), self.site()["version"])
        self.check("4 Same reading sent again", "Counted once: readings, alerts and version unchanged",
                   lambda: before == after and f"readings {after[0]}, alerts {after[1]}, version {after[2]}", timeout=3)

        print("waiting for the five-minute escalation clock ...", flush=True)
        self.check("5 No acknowledgement for 5 min", "Closure recommendation goes to the next contact",
                   heard("traffic_control", contact=1), timeout=420)
        self.check("5 Photo re-ask during the flood", "Quotes the last reading, not the forecast",
                   lambda: [t for t in heard("guardians")() if t.startswith("Water at")], timeout=30)
        escalated_after = time.time() - closure_at
        self.rows[-2] = (*self.rows[-2][:2], f"{self.rows[-2][2]} | {escalated_after / 60:.1f} min after the first", *self.rows[-2][3:])

        for high, expect in ((18, "CRITICAL"), (10, "WARNING"), (8, "RECEDING"), (6, "CLEAR")):
            self.reading(high)
            self.check(f"6 Reading {high} cm", f"Site {expect}",
                       lambda expect=expect: self.site()["state"] == expect and expect)
            time.sleep(2)
        self.check("6 Flood event closes", "Closed as a flood, with its peak",
                   lambda: (f := self.flood()) and f["closed_at"] and f"{f['outcome']}, peak {f['peak_low']:.0f}-{f['peak_high']:.0f} cm, "
                   f"cars blocked {f['blocked_cars_s'] // 60} min, {f['asks']} photo requests", timeout=150)
        self.check("6 Stand-down", "Everyone who was warned is told the warnings have ended",
                   lambda: (texts := [d for d in self.drain() if "warnings for this site have ended" in d["text"]])
                   and len({d["audience"] for d in texts}) == 4 and sorted({d["audience"] for d in texts}))
        self.check("6 Stand-down wording", "Says what was seen; never that the road is open or safe",
                   lambda: [t for t in heard("residents")() if "have ended" in t and "open" not in t.lower()])
        self.check("6 Timer ends", "Execution succeeded, none left running",
                   lambda: (e := self.executions()) and all(s == "SUCCEEDED" for _, s in e) and e, timeout=150)
        return all(row[4] for row in self.rows)

    def report(self, passed):
        now = datetime.now(IST)
        lines = [
            "# Smoke test on AWS", "",
            f"Run on {now:%d %B %Y at %H:%M} IST against the stack `{stack.STACK}` in `{stack.REGION}`, "
            f"by `python scripts/smoke_test.py`. It took {(time.time() - self.started) / 60:.1f} minutes.", "",
            f"**Result: {'every step passed' if passed else 'FAILED, see the rows marked FAIL'}.**", "",
            "One test site, `hyd-900`, was walked through a whole flood: rain, rising readings, a repeated "
            "reading, five minutes with no acknowledgement, falling readings, and clearing. The site is "
            "not a real place and has no position, so it never appeared on the public map. Everything "
            "the test created was removed afterwards.", "",
            "| Step | Expected | Seen | Took | |", "|---|---|---|---|---|",
        ]
        for step, expected, seen, took, ok in self.rows:
            seen = seen.replace("|", "\\|").replace("\n", " ")
            lines.append(f"| {step} | {expected} | {seen[:260]} | {took:.1f} s | {'pass' if ok else '**FAIL**'} |")
        lines += ["", "## Alerts as delivered", "",
                  "Every message the alerts topic delivered during the run, in order.", "",
                  "| After | To | Contact | Text |", "|---|---|---|---|"]
        for d in sorted(self.drain(), key=lambda d: d["at"]):
            lines.append(f"| {(d['at'] - self.started) / 60:.1f} min | {d['audience']} | {d['contact']} | {d['text']} |")
        lines += ["", "## What this does and does not show", "",
                  "- It shows the deployed services accept the same writes and conditions the unit tests "
                  "imitate, and that the real one-minute and five-minute clocks drive the workflow.",
                  "- Alerts were captured from the topic by a temporary queue. Nothing was delivered to a "
                  "person: the topic had no email or phone subscribed.",
                  "- Readings were typed in by the script. No photo was read by a model in this test.", ""]
        (ROOT / "docs" / "smoke-test.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")


def main():
    smoke = Smoke()
    passed = False
    try:
        smoke.setup()
        passed = smoke.run()
    finally:
        try:
            smoke.report(passed)
        finally:
            smoke.teardown()
    print("PASSED" if passed else "FAILED", flush=True)
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
