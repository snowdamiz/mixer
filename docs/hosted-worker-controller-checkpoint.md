# Worker controller implementation review checkpoint

The first per-operation Cloudflare Worker/SQLite controller is implemented but
**rejected for development acceptance**. Its 28 original local workerd test groups
pass. Independent review adds eight groups: five pass and three fail, identifying
two correctness defects. Production clock, provider and object verification remain
unavailable; no controller or worker is deployed.

The final claim callback can grant after a higher authority epoch/owner or revision
commits during its durability wait. Separately, successful effect/claim samples do
not advance durable clock history, allowing a later backward clock movement to
escape quarantine. The original failing cases, intermediate attempts and source
are preserved in the [independent report](hosted-worker-controller-implementation-independent-review.md).

Root verifies 60 current/archived producer inputs, 1,180 installed dependency files,
29 Jason files, 54 artifacts, four runtime inputs and 17 command-output pairs.
It separately verifies 48 review artifacts, command records and 12 archived fixture
files. The review records 128 cleanup actions, 124 distinct removed storage paths,
removed scratch and no remaining owned workerd process. These are Mac host runtime
tests, not deployed Cloudflare or native-device receipts.

The [producer binding](../verification/hosted-worker-controller-root-review/producer-binding.json)
and [independent decision](../verification/hosted-worker-controller-root-review/independent-decision.json)
record exact source and output hashes. All 58 locked development dependencies have
license, purpose, version, URL and integrity metadata; install scripts were disabled.
There are no production package dependencies.

A separate V2 candidate is assigned. It must fence the final grant against its exact
consumed authority and identity, permanently retain consumption after a lost grant,
and persist exact accepted intervals plus a nondecreasing historical lower bound.
Actual qualified samples drive authorization; a historical floor cannot replace or
clamp the clock. A schema-1 row cannot recover forgotten history: migration must
preserve its identity, claims and tombstones while quarantining it. Fresh independent
runtime review is required before integration.

The independent pending-operation registry, missed-wake recovery, nonrollbackable
restore authority, real ingress/clock/provider qualification, private source and
result authority, worker isolation, signing, deployment and GA remain pending.
The separately interrupted outbound transport review is not resumed by this work.
