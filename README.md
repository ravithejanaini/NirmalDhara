# NirmalDhara

"Clean flow": one camera network for flood safety and drain-waste tracking.
Built for Environmental Hacks (Heat and Water track), 8–11 October 2026.

- **Public safety:** reads floodwater depth from ordinary photos and tells each type of
  vehicle whether it can pass, and how long until it cannot.
- **Environment:** tracks the waste and plastic that block drains, and tells the responsible
  department what will happen if it stays and which inlet to clear first.

The full design is in [METHOD.md](METHOD.md).

## Status

Working now: depth bands, per-vehicle passability, rise-rate prediction, and a photo reader
that calls a Claude model on Amazon Bedrock. The photo reader has not yet been run against
real images.

## Run

```bash
python -m pip install -r requirements-dev.txt
python -m pytest
python -m nirmaldhara check --low 15 --high 25 --confidence 0.8
```

Reading a photo needs AWS credentials with access to a Claude model in Amazon Bedrock:

```bash
AWS_REGION=ap-south-1 python -m nirmaldhara read samples/photo.jpg
```

`NIRMALDHARA_MODEL` overrides the model. The default, `in.anthropic.claude-opus-5`, is the
in-country inference profile: requests are routed only between the Mumbai and Hyderabad
regions.

## Deploy

Needs the AWS SAM CLI and credentials allowed to create the stack.

```bash
sam validate --lint
sam build
sam deploy --stack-name nirmaldhara --region ap-south-1 --resolve-s3 --capabilities CAPABILITY_IAM --no-confirm-changeset
```

Deployed on 9 October 2026 to ap-south-1 (Mumbai): five functions, three tables, three queues,
one topic, one event bus with two rules, one state machine, three alarms and a 15-minute
schedule. The resource names are in `data/stack-outputs.json`.

The site is served over HTTPS from the stack's `SiteUrl` output
(`aws cloudformation describe-stacks --stack-name nirmaldhara --query "Stacks[0].Outputs"`).
Upload the pages with `python scripts/deploy_web.py --apply`. CloudFront is written but off
until AWS verifies the account; see DESIGN.md.

## Layout

| Folder or file | Holds |
|---|---|
| `src/nirmaldhara/`, `src/handlers/` | The logic and the AWS functions; `src/` is all that is packaged for Lambda |
| `statemachine/`, `template.yaml` | The flood timer loop and the deployment template |
| `tests/` | The automated tests |
| `scripts/` | Seeding, sending and replaying scripts |
| `data/` | Site list, scenarios, sample map file |
| `web/` | The resident map and other pages |
| `samples/` | Labelled flood and drain photos |
| `docs/` | Smoke-test record, video script, diagrams |
| `layers/vision/` | Requirements for the photo functions (numpy, pillow, anthropic), built as a layer |
| `METHOD.md`, `ARCHITECTURE.md`, `DESIGN.md`, `TASKS.md` | Method, high-level design, low-level design, task plan |

## AI tools used

Claude Code (Claude Opus 5.5) was used for research, design and code.
