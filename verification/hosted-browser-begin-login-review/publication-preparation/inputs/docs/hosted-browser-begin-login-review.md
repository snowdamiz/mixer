# Fixed begin-login independent review

Contract review accepts the bounded fixed preauthentication begin-login contract
in `docs/hosted-browser-begin-login.md` for implementation. This is a contract
finding only. Product implementation and selected PostgreSQL 16 independent
execution remain pending. No Application startup, provider exchange, active
session, HTTP route, authentication readiness or GA acceptance follows.

The review read the current preauthentication owner, Store and private drafts,
the accepted Protocol/Vault/StoredSnapshot contracts, and only the relevant fixed
load/begin/snapshot lifecycle SQL. Ordinary load retains its rejection of all
projected attempts. The separate discover_begin operation can admit authenticated,
structurally exact current pending attempts for replacement, including an expired
attempt while its preauth browser remains live. The fixed load helper hides
claimed/terminal rows; the component cannot claim it observes those states.
Unchanged begin SQL supersedes pending/claimed rows under its existing locks.

The one retained caller permit and original five-second deadline span two
separate catalog-checked transactions and all cryptography. Parsed raw cookie
must match the supplied canonical cookie before discovery; Origin and recovered
synchronizer CSRF must pass after confirmed discovery and before mutation. State,
nonce, verifier, the bounded exact fixed URL and both fresh envelopes are prepared
before mutation. Full produced browser/attempt/context/cipher equality precedes
COMMIT; confirmed COMMIT plus final owner/PID/configuration/generation/caller/time
and exclusive expiry continuity precede release of the private authorization.
Unknown COMMIT or response loss yields no URL or automatic retry.

A concrete concurrent-state caveat is required: claim/provider rejection can
advance audit_sequence without revision between discovery and begin. Revision
CAS alone therefore does not prove source continuity. Exact full browser output
comparison must reject and roll back a resulting audit_sequence mismatch even
when the SQL helper accepted the revision. This selected race needs executable
independent evidence alongside two-begin CAS coverage.

The shared publication helper also needs a caller-local check after successful
finish acknowledgement. The authoritative finish validates and releases the
permit atomically; its fallback release is not another authority check. A caller
scheduled after the deadline/expiry must withhold a committed value. The reviewed
bounded direction retains finish's sampled wall time privately, checks retained
owner PID/current generation and storage phase under the original deadline, then
samples local monotonic/wall/exclusive expiry before returning. Bootstrap/load
must share that correction, including valid nil-load success. This narrows the
check-to-return interval; it cannot make delivery to an external recipient atomic.
The existing private finish reply changes from :ok to a private wall-time receipt;
old immutable fixtures retain their original historical contract and new owned
fixtures must explicitly target the new private shape.

Further required implementation controls include authenticating the source CSRF
and session envelope, authenticating any projected old verifier without reusing
it, exact provider/configuration/deadline binding, all new pending claim/completion
nulls, entry-to-current created time bounds, nonce/state digest equality and
independent URL reconstruction. These are implementation review obligations,
not evidence already collected.

The independent runner will use only the selected source closure and pinned
existing BEAM dependencies, actual default KeyOwner and one owned random-port
loopback PostgreSQL 16 Linux fixture with synthetic restricted roles. Its manual
ssl:false RuntimeConfig does not qualify production constructor/TLS/5432 admission,
Neon, external custody or startup binding. Every attempt must bind commands,
versions, source/dependency/output hashes and cleanup. Frozen hosted inspector,
authority-driver and rejected Worker V2 sources remain excluded; no broad hosted
harness, native/UI/capture/device or unrelated-process discovery is authorized.
The full owner/lifecycle/relation matrices and active verifier/provider/HTTP,
FieldLog/customer/operational/GA gates remain pending.
