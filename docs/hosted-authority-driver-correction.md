# Current-authority driver correctness candidate

The isolated correction makes two implementation changes selected in the
[root direction](hosted-authority-driver-correction-direction.md): strict original
context comparison and a fixed exception message. The complete implementation
delta is [retained](../verification/hosted-authority-driver-correction/implementation.patch).
No SQL, transport structure, lock order, clock, privilege or dependency changes.

The corrected candidate passes the original **56 actual-driver cases**, with a
fresh unchanged **128-case schema replay**, and **17 additional regression groups**
against the real fixed Repo/Postgrex connection. All eight integer-to-equal-float
context copies now reject before effects; the fixture records zero committed
effects. Correct original contexts continue through the original positive cases.
The normal revoked-family denial formats correctly, and fourteen reason shapes
return the same bounded `authority driver rejected` message while retaining the
original structured internal reason. Existing raw-credential omission checks pass.

The extra suite is a separately labeled correction of the earlier review oracle.
Its unchanged historical reproduction remains in the interrupted review packet.
Root verifies 4,025 raw source, dependency and output bindings for that packet in
`verification/hosted-authority-schema-root-review/driver-review-interruption.json`.
The earlier review stopped after an automated safety flag before final acceptance;
its two reproduced correctness findings are preserved without claiming a completed
independent review. No changed authority value was demonstrated by the equal-value
type substitutions.

Both correction runs retain exact input/source manifests, all commands and output,
the accepted dependency archive, original SQL and cleanup. Both disposable
PostgreSQL clusters and their scratch were removed. The first run executes the
unchanged schema suite; the second explicitly reuses that successful observation.
These are local host fixtures, with no live source, production deployment,
authenticated HTTP, native or physical-device action.

The [receipt](../verification/hosted-authority-driver-correction/receipt.json) and
[read-only checker](../verification/hosted-authority-driver-correction/check.py)
bind this frozen candidate. Independent acceptance and live integration remain
pending, as do combined domain persistence, migration/catalog startup, providers,
cloud operations and all GA gates.
