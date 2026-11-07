# Callback storage review interrupted

Independent review of the frozen Unit A packet is incomplete. The review was
interrupted by an automated safety check before any PostgreSQL runtime, callback
replay or independent functional control executed. This document grants no
acceptance and promotes no GA gate.

The received handoff SHA-256 is
`0a5c39cf33240c0be778f9fb654a9adf0d8d4a1150d5176ce1d9fbae5480b70a`.
Read-only verification matched its seven named members, twelve preserved receipt
hashes and 10,035 archived output bindings. The selected producer attempt is
`20261025T213600.582572Z-58a09c`, receipt SHA-256
`acd5263411b48b4c8813f30ee45fa8e01332362625e1bd2450dcc3f0475bd58f`,
with 67 archived source members, 528 dependency binary members and 433 dependency
source members. These are producer evidence bindings, not an independent runtime
pass. The producer source tree digest is
`5391c2df8d188af6b6e38fd89e055718f6f2a91f00369cc85207a0a9c8f08d3f`.

Both reviewer attempts passed actual projectless Mix formatting of the selected
Store, CallbackDraft and callback fixtures. Both then failed the selected
warnings-as-errors compilation before database creation. The first attempted to
compile directly from the frozen source archive, whose dependency sources live
in a separate archive. It could not resolve Oban's pinned migration source. The
second assembled the archived source and dependency bytes in an owned unified
workspace; it could not resolve the additional compile-time resource
`hosted/lib/mixer_hosted/authorization/postgres/session.ex`. The received accepted
relation manifest binds that resource to SHA-256
`8ae27291a2e0777dfde6f995cf8c1a64c6ac8e2e7b0e7660afdb7cac76382727`,
but the selected producer archive does not include its bytes. This resource was
not added, changed or executed during this review. Both raw compilation failures
and complete input/dependency snapshots remain preserved.

A source-reading concern about malformed callback structs missing `lease` was
reported for coordination, but no reproduction ran and no finding is accepted
from it. Prepared reviewer control files were never executed. Product code,
producer packet and root delivery metadata were not edited by this lane.

The following remain pending: successful isolated source-closure compilation,
PostgreSQL 16 replay of all 35 callback, 30 preauthentication and 30 begin methods,
independent functional review, and a bounded acceptance verdict. Unit B,
ClaimOwner/facade/provider/HTTP/Application/Neon/TLS/authenticated readiness,
physical devices and GA acceptance also remain unqualified. Native runtimes,
UI, capture and phones stayed paused.

`verification/hosted-browser-callback-storage-review/interrupted-cleanup.json`
records exact saved identities and cleanup checks. Both owned scratch paths are
absent. No container creation command ran; exact-name Docker inspections confirm
both planned container names are absent. All spawned compile/version commands
were reaped. No PG server or long-lived BEAM resource was started, and cleanup
removed no foreign resource. The first cleanup diagnostic parser expected an
uppercase message; its result is retained separately, with the exact lowercase
Docker bytes used by the final cleanup record.
