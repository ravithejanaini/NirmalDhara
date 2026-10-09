# Submission writeup

Text for the submission form. Two lengths are given because the form's limits are not confirmed
(task SUB-08): use the long one if it fits, the short one if not. Every statement here is listed
with its evidence in [claims.md](claims.md).

- Repository: https://github.com/ravithejanaini/NirmalDhara
- Live site: https://s76zfmc6n5xd65b32tzf46dw3m0kvvik.lambda-url.ap-south-1.on.aws/
- Track: Heat and Water
- Team: rudhra (solo)

## Long version (about 330 words)

**Problem.** Every monsoon the same underpasses and low roads in Hyderabad flood. People drive
into water they cannot judge, and the city has no simple record of which places fail most, so
repairs to drains and pumps are not aimed where flooding recurs.

**What NirmalDhara does.** It watches nine places that published reports say flood. Every 15
minutes it reads the rain forecast and opens a watch where heavy rain is coming, before any water.
As depth readings arrive it keeps each place's state and answers one question per vehicle: bikes,
autos, cars, SUVs and people on foot each get "passable with care", "not safe" or "unsure". Depth
is always a range; the top of the range decides, and a doubtful reading is never "passable". A
flood workflow sends each alert once, escalates a closure recommendation after five minutes
without acknowledgement, and tells everyone it warned when the flood ends. A public map shows each
place as a road cross-section that fills with water. Every closed flood is kept, and a page ranks
places by how long they blocked the road, which is the environmental use: it points repair work
at the drains that keep failing.

**AWS.** Deployed in Mumbai (ap-south-1) with AWS SAM, serverless throughout: Lambda (8
functions), DynamoDB (3 tables), SQS (a FIFO queue that keeps each place's readings in order, and failure queues),
EventBridge (event bus, rules, 30-day archive) and EventBridge Scheduler, Step Functions (the
flood timer), S3 (public files), SNS (alerts) and CloudWatch alarms.

**AI tools.** Claude Code wrote the code and documents under my direction, with Claude Opus 5.5
for design, the alert workflow and the interface, and Claude Sonnet 5.5 for well-specified
routine tasks. A Claude model on Amazon Bedrock is the intended photo reader.

**What is not proven.** The photo reader has not read a real photo: AWS has not verified the
account for model access, so there is no accuracy figure, and the depths in the demonstration come
from a scripted replay. No person is subscribed to the alerts yet. Tracking the waste that blocks
drain inlets, and the camera network, are designed and not built. The README lists every limit.

## Short version (about 75 words)

NirmalDhara watches nine known waterlogging points in Hyderabad. It opens a watch from the rain
forecast, turns depth readings into a per-vehicle "can I get through?" answer, sends each alert
once, and records every flood so places can be ranked by how long they block the road. It runs
serverless on AWS in Mumbai. Not yet proven: the photo reader has not read a real photo, and
drain-waste tracking is designed, not built. Built with Claude Code.
