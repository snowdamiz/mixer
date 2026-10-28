# Hosted identity startup correction independent review

Recommend root acceptance of the cumulative configured-startup development slice.
No unresolved product finding remains for the reviewed candidate. IR-F01 is fixed
by strict whole-string matching in the two Manifest endpoint expressions. This
review does not apply the patch or close a GA gate.

The corrected source digest is
`bfa2dcc1467f524a68fec298bdd098625f450b68ab2bd68b99f2a73d435772c3`.
The cumulative twelve-file patch is
`b8e19489a86e4bfe621dc478070f48c4aebad58dc98d950599020eecad0add49`;
the correction against the frozen startup candidate is
`1b5fee53a73ddcafb3122c2bad874985a191a67c472b12210cd12b217b1439d1`.
The selected correction receipt is
`e90dc6714ecf1b9fd34786384cce3db0e8ed61af780ee1ebb2a82370e7db25ed`.

Independent reconstruction from accepted hosted base `b0629cf5` plus the
cumulative patch matches all 69 corrected manifest/archive entries. Applying the
original frozen startup patch and then the correction delta produces the same
bytes. All 92 correction, 197 original implementation and 80 original review
output bindings match, as do their bound documentation and contract. All ten
original startup overlay files retain their frozen hashes. The correction
contains exactly two production anchor replacements (`^`/`$` to `\A`/`\z`) and
one new test file. All 914 dependency files retain digest
`99bc0e5256ca834e5cd24bfcd3a1f5b158d5479af5677cccbe998ee005628452`.
Dependency pins, existing startup/owner/transport code, routes and migrations
retain their earlier bytes.

Fresh independent execution on macOS/Elixir 1.20.4/OTP 29 passed:

| Check | Result |
| --- | --- |
| Earlier independent adversarial tests | 9 passed, including formerly failing IR02 |
| Earlier minimal direct Manifest/StartupConfig LF regressions | 4 passed |
| Correction endpoint tests and startup constructor tests | 14 passed |
| New independent endpoint boundary tests | 4 passed |

The four new cases exhaust ASCII bytes in an interior hostname/path position,
check every terminal ASCII control and Unicode newline/separator samples, reject
LF at intermediate hostname-label ends, and reject LF still within maximum byte
bounds alongside valid controls. Both Manifest and JSON StartupConfig are
exercised. These checks establish configuration rejection, not a malformed
endpoint transport exploit. The earlier review's failures and the producer's
identical-test baseline (10/14 passed, four LF rejection failures) remain frozen
in their original packets.

One initial reviewer test expected a dot inside a hostname to reject; a dot
validly separates labels. Its original source and 3/4 failure output are retained.
Only that reviewer expectation changed before the four-test passing replay.
An initial internal collector comparison also expected seven unused protocol
fixtures in the host collector; the collector correctly binds all hosted source
and its two consumed v3 fixtures. The final check verifies its exact 62 inputs
and archive, plus all 974 Linux source/dependency entries. Neither reviewer
mistake required a candidate change.

Cumulative configuration/wiring review confirms explicit disabled/configured
roles, closed duplicate-aware JSON, fixed known string-to-atom clauses, fixed
bounded errors and redacted Inspect, canonical configured resolver addresses,
one runtime OTP CA fetch, DER normalization solely for identity, and preservation
of the database's original CA list. Installed OTP source/BEAM hashes still match
the recorded CA evidence. `Application.start/2` requires the explicit validated
setting; the fixed production owner precedes Endpoint. No environment field can
select a fixture/module, disable TLS, inject a snapshot or enable discovery.

Normal runtime and release evidence is explicitly reused, not newly executed by
this correction reviewer. The unchanged startup wiring already has the earlier
independent actual Application/Endpoint/PostgreSQL lifecycle and isolated
production DNS/HTTPS public-adapter review: macOS 85 passed with two Linux-only
skips, Linux 87 passed. The corrected producer freshly ran macOS 93 passed with
the same two explicit skips and Linux 95 passed without skips. This review
verified their nested source/archive/output bindings, command exit codes, actual
metrics and cleanup rather than accepting the summary alone. The corrected
producer's packaged release builds, rejects missing required settings with exit
1, and excludes all four checked test-only exports.

The corrected bound metrics show actual configured application/endpoint startup,
zero initial snapshots/attempts/flights and zero startup fetches, owner crash
replacement and empty restart. The network-none Linux namespace shows cold
synthetic signed-token admission through production DNS port 53 and verified
HTTPS port 443, old-lease rejection after restart, renewed cold admission,
cancelled inflight shutdown and all three fixture connections closed. There is
no changed lifecycle/network implementation or new concern requiring another
full matrix; fresh focused review covers the production correction.

`verification/hosted-identity-startup-correction-review/receipt.json` binds this
document, exact review inputs, command/tool logs, both reviewer source versions,
source reconstruction, evidence assessment and cleanup. Only this document and
that directory are owned. Unique source scratch was removed after an open-handle
check. This review created no database, container or native instance and changed
no live product source, tracker, frozen packet, credential or unrelated process.

These are development receipts. Synthetic PostgreSQL uses loopback without TLS;
production database TLS has configuration evidence only. Synthetic CA/DNS/TLS
and signed tokens qualify no real identity provider. Authenticated HTTP,
membership, permissions, provider selection/discovery, durable identity registry,
Neon/Cloudflare operation, separately published FieldLog packages, native/physical
phones, production/customer operations and GA acceptance remain outside scope.
Physical phones remain disconnected and deferred. Root integration/commit/push
is separate from this acceptance recommendation.
