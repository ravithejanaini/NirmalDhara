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

## AI tools used

Claude Code (Claude Opus 5.5) was used for research, design and code.
