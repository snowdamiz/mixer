# Hosted key-owner independent review

Recommendation: **accept the frozen component for subsequent integration**, under
the explicit [unknown-kid scope clarification](../verification/hosted-key-owner-root-review/unknown-kid-scope-clarification.json).
No unresolved implementation finding remains from this review. Root acceptance
is a separate decision. Application startup, HTTP authentication, authoritative
database authorization, provider qualification, deployment operations and GA
remain pending.

The [independent receipt](../verification/hosted-key-owner-independent-review/receipt.json)
binds the exact producer receipt
`a9a6f27494a4b6af7452f0300f7b62f5942af69c0f73e128462a065f28986286`,
all 205 producer file bindings, and source tree
`a6e39fe48602d9044a43d4f3e617292fe19418856006f713d914487945577aee`.
The review copied the source into an isolated scratch directory and independently
hashed 914 dependency source files. The selected configuration/lock/license
bindings and installed Mint 1.11.0 parser/license hashes matched root selection.
The six previously accepted pure verifier modules and their test remained
unchanged. No product source, dependency, producer packet or tracker was edited.

The reviewer read all twelve new modules and the accepted verifier boundary,
including profile/endpoint validation, manifest history, admission, owner state,
adapter retry, DNS/address classification, paired-clock freshness, wire guard,
Mint/TLS integration, bounded TCP callback and worker/watchdog supervision.
Production has no implicit provider, mutable application-environment trust,
global SSL mutation, record-layout inspection or configurable fixture bypass.
The actual public raw-port controller is checked at registration and transfer;
the flight remains occupied through worker, raw-port and registered controller
DOWN. Infinite graceful child shutdown is intentional and has a narrower
guarantee than container termination or a forced process kill.

Independent execution passed:

| Environment | Executed evidence |
| --- | --- |
| macOS, Elixir 1.20.4 / OTP 29.1.1 / ssl 11.7.7 | Frozen 45-test identity baseline; 12 additional adversarial tests; production compilation and fixture-export/module exclusion |
| Disposable Linux aarch64 container, same Elixir/OTP/ssl | 58 tests: frozen 46-test baseline including actual production DNS/rebinding plus the same 12 independent cases; production release build and fixture exclusion |

Linux used the pinned image in the receipt, `--network none`, and `NET_ADMIN`
solely to assign 8.8.8.8 inside its own namespace. The production resolver,
classifier and TLS transport authenticated the pinned public tuple after the DNS
stub changed subsequent answers to loopback. The separate forbidden sink saw
zero connections. The release was built without starting the hosted application.

The additional finite cases in
[adversarial_test.exs](../verification/hosted-key-owner-independent-review/adversarial_test.exs)
cover endpoint aliases/textual IPs and path escapes; exact one-retry behavior;
real owner generation, forged-permit, disable and version fences; atomic rejected
replacement after tombstone expiry and a clock epoch fault; unknown-key pressure
and negative controls; exactly eight versus nine CNAME hops and mixed address
families; malformed chunk-extension/trailer rejection through both the wire
guard and Mint; non-ASCII whitespace rejection and valid ASCII OWS; conservative
freshness; raw-port registration/activation/buffer options; all split points of
one complete HTTP response; and graceful supervisor stop with an owned TLS
controller deliberately held for more than 5,100 ms after its raw port and worker
were down. The latter completed only after controller DOWN, confirming the
cleanup fence beyond the ordinary five-second child shutdown interval.

One contract wording conflict was found and resolved explicitly by root without
changing the frozen implementation. A protected header with an absent valid kid
can cause bounded state/refresh work within the already configured binding even
when its payload asserts a foreign issuer. Its result remains unauthenticated.
The independent test observes one eligible flight, at most 128 FIFO negatives,
non-renewing repeated hits, no additional state for an invalid header, known-key
foreign claims or an unknown configured binding, and negative clearing on
successful snapshot replacement. This is a refresh-pressure availability limit,
not evidence that unauthenticated claims establish trustworthy refresh intent.
Future bounded HTTP admission and deployment-wide provider quotas remain needed.

The first scratch setup attempt failed because the collector initially included
generated dependency `_build` metadata in its source hash set while excluding
that directory from the copy. Its scratch was removed and the collector was
corrected. The first independent test run passed 9 of 11 cases; two harness
expectations were corrected: the TLS fixture has no public `date/0`, and valid
Expires may supply freshness when only s-maxage is present. The retained logs
identify those failures; they were not product defects. The following 11-case
run passed, and the final 12-case run and Linux replay passed. No test failures
were suppressed or converted into product passes.

Resource receipts are sampled process/binary/parser/mailbox observations and
driver-buffer checks. They do not establish universal RSS, kernel-buffer,
native-crypto allocation, memory or real-time bounds. Large close-delimited
bodies retain the documented one-byte-read/deadline compatibility limit. Clock
and cooldown transition tests change private timing state, while socket, DNS,
TLS, timeout and cleanup tests exercise actual platform behavior. Identity
history is limited to sixteen IDs for one owner lifetime; durable historical
identity/version enforcement across restart remains future provisioning/DB work.

Only owned test scratch/builds and containers were removed. Fixture key
directories and owned sockets/processes were cleaned up. No native, physical
phone, external provider, customer messaging, production publication, migration
or credential operation occurred.
