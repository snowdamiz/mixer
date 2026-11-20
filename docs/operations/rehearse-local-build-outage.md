# Rehearse a local build API outage

Use the combined outage drill to test alert delivery, acknowledgment, and
recovery while the signed release origin serves its existing offer. The
fixture runs Phoenix and the release origin against separate disposable
PostgreSQL clusters.

## Run the drill

Use Python 3.12 or newer, PostgreSQL 17, Elixir 1.20.4 on OTP 29, and Go 1.26
or newer. The fixture retrieves dependencies from its locked manifests.
From the repository root, choose a new receipt path.

```sh
mkdir -p verification/local
python3 -B tests/integration/l07-combined-outage/run.py \
  --rehearse-alert --receipt verification/local/local-build-outage.json
```

The tool prints `LOCAL_TEST_ALERT` with code `build_checkout_unavailable`
and HTTP status 503. The ordinary build request has failed before `BEGIN`.
The checkout observer confirms the failure and the release probe confirms
the signed offer and artifact match their baseline SHA-256 digests.

## Verify acknowledgment and recovery

1. Check `local_alert.acknowledged` in the receipt. The runner writes an
   acknowledgment to the private alert directory while the checkout is
   still held. The fixture releases the checkout after it sees the marker.
2. Check `observed.exact_key_retry_status` and
   `observed.retry_replay_status`. The same session and idempotency key
   receive 201 after recovery, then 200 on replay. The database must have
   one Oban job per accepted build.
3. Check `observed.signed_release` and `release_publication.audit_unchanged`.
   Require the same signed offer and artifact before, during, and after the
   refusal. Compare the audit result before and after the drill.
4. Close the drill only when `local_alert.resolved` is true and
   `cleanup` confirms termination, reusable ports, and scratch removal.
   Keep the compact receipt as the rehearsal record.

If acknowledgment or recovery fails, keep the first failure and use its
checkout, job, and release observations to find the affected boundary.
If cleanup identifies a held process or directory, preserve that exact
resource. Escalation for a live incident, production delivery, and customer
communication have separate procedures and qualification.

## Rehearse worker loss during concurrent requests

Prepare a dedicated daemon and an approved Pair25 operator file. Verify the
Swift image with `docker image inspect --platform linux/arm64` on that daemon.
The `Descriptor.digest` field must match the pinned manifest. Docker Engine
29 with the containerd image store reports the descriptor.
[Prepare the Pair25 stage](../../tests/integration/managed-android-local-linux-pair25/MANAGED-LAYOUT.md)

Use the lock-verified Hex cache, a short private scratch parent, and a new
receipt path. Run from the repository root.

```sh
HEX_HOME="$hex_cache" python3 -Bu tests/integration/l07-combined-outage/run.py \
	--checkout-burst --pair25-scratch-parent "$scratch_parent" \
	--operator "$operator_json" --receipt verification/local/pair25-outage-burst.json
```

Check that `pair25.combinedOutage` reports four pre-BEGIN 503 responses with
both signed reads completed while all four responses were pending. Confirm
that the original session and key return 200 after the worker reopens. The
receipt must show one native completion, one capacity release, no
cancellation, unchanged release audit bytes, tenant refusals, and closure of
the fixture. Retire the dedicated daemon and verify port reuse before
removing the stage.
