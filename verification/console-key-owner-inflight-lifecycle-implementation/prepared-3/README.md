# Candidate 3: narrow charlist correction, runtime unexecuted

The sole canonical source change after candidate 2 replaces
'jwks.fixture.invalid' with ~c"jwks.fixture.invalid" at new inflight test line 312.
Both spellings denote the same charlist. The preserved beforeimage, exact
one-literal diff and correction receipt prove all other source bytes unchanged.
No product cleanup behavior, assertion, case count or policy is changed.

Root's retained candidate-2 run compiled 19 ordinary identity modules in each
fresh production/test VM with zero warnings and passed all production exclusion
booleans. Test-module compilation then reported one deprecation and stopped
before ExUnit.run. No methods or TLS fixtures ran. Its actual audit records one
completed /usr/bin/openssl version invocation, yielding LibreSSL 3.3.6; there were
no certificate-generation commands. Both retained VM children were reaped,
their groups absent, scratch removed and input pins stable.

That actual audit also records wrapper process group 58589, distinct from test
VM group 58517. The current source's assumption that System.cmd children inherit
the retained VM group is therefore unsupported by the observation. Its existing
OpenSSL validator would reject this later, and VM-group-only failure cleanup is
not independent proof of those wrapper/native groups' absence. This is an
explicit pre-release review blocker, not a clean descendant-ownership result.
No speculative group/cleanup change is mixed into this narrow candidate.

prepared-3 preserves candidate-2's failed receipt, output, raw OpenSSL starts and
completion records, release, full source/plan snapshots and the exact correction.
Its runtime-only runner changes only prepared-3/candidate-3 path bindings from
candidate 2. All 17 artifact schemas, nine-method roster, zero-warning policy,
strict output membership and 40/46/52/55-second bounds remain unchanged. The
unchanged seven ordinary tests come from frozen inputs; active key_owner_test.exs
is excluded. No runtime release is granted by this packet.

Offline read-only check:

    python3 -B verification/console-key-owner-inflight-lifecycle-implementation/verify-v3.py

The previous exact formatter pass is historical. The future runtime's read-only
five-file equality check must assess the new literal; no new formatter has run.
Candidate-3 production/test compilation and all nine methods remain pending,
including completed-TLS/pending-JWKS shutdown and the required KOL09 adverse or
clean witness. Original KOL08 ordinary owner crash, production network/provider/
application/HTTP/session/custody/operations/GA remain pending. Native/UI/capture/
emulators/phones remain paused. No central metadata, commit or push is included.
