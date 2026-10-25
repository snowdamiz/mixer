# Independent review of the frozen external-worker client

The reviewed v1 candidate is **not accepted for integration**. Independent real
TLS tests reproduced replacement-role admission while an old flight remained
live, and observed an additional outbound User-Agent header outside the original
seven-header contract. No producer or live hosted source was changed by this
review. Root is coordinating a new candidate; the findings below remain bound
to v1.

The reviewed source digest is
`9d561357f923df55ef5ec7f55d321d6f973dc6f22e2d9f2af35d9907541b8499`
(86 inputs), archive SHA-256
`4d231490a8fefca6be3cd1e6a263c95374fc50782a0cb93b8bc0cef2598bac56`,
source revision `44048403df8c5571d29b9558474edfaa8265787f`.
The review extracted that immutable archive into its own directory, checked
every archived input against the producer map, compiled only the four candidate
modules and six safe context modules, and used only the archived Mint/Jason/HPAX
dependency BEAMs. It asserted both a compiled-module allowlist and zero loaded
Authority/Catalog modules. The frozen hosted authority/catalog lane was not read,
imported, loaded or executed.

## Blocking lifecycle finding: RoleGuard loss reopens capacity

`WorkerTransport.start_component/2` treats an absent registered RoleGuard as
permission to start. RoleGuard is an unlinked GenServer, and the owner does not
monitor it or retain a durable admission quarantine when it disappears.

The independent control establishes one authenticated request against a real
synthetic TLS server, suspends its Flight, kills that role's RoleGuard and owner,
and starts a replacement component in the same BEAM execution domain. The new
component admits sixteen authenticated requests while the old worker, raw TCP
port and SSL connection process remain alive. The fixture observes **seventeen
simultaneous TLS handlers**. This defeats the candidate's sixteen-owner bound
across this failure/restart sequence.

This is controlled internal BEAM fault/suspension injection, not a demonstrated
remote-controller or customer-input exploit. Pausing the Flight intentionally
prevents it from consuming the owner/guard DOWN signals; it exposes whether
replacement admission depends on observed retirement or merely registered-name
absence. Owner death **alone** correctly leaves RoleGuard closed and blocks
replacement until the old Flight retires. The unexpected Flight-death quarantine
in the producer suite also passes. Neither control addresses loss of the guard
itself.

Before integration, guard loss must fail closed across component restart until
all previously owned resources are observed gone or the entire execution domain
has been disposed. An absent process name is not that observation. The review
does not prescribe a production supervision design or claim an OS resource cap.

Evidence is
`verification/hosted-worker-transport-independent-review/guard-loss-reproduction.json`
and the test `RoleGuard loss permits replacement role while paused old SSL flight
remains live` in `independent_test.exs`. The test resumes the old Flight, observes
its worker and SSL handler dead and raw port closed, retires every replacement
flight, and observes the fixture's active-handler set empty before completion.

## Outbound-header contract finding

The original contract requires exactly Host, Content-Type, Accept,
Accept-Encoding, Connection, Content-Length and Authorization. The pinned Mint
1.11.0 adds `user-agent: mint/1.11.0` through `add_default_headers/2`; the candidate
does not provide its own value. Independent decrypted server-side request bytes
therefore contain eight headers. The original seven-versus-eight assertion
fails in retained `attempt-2.independent-tests.stdout`.

Exact requests for query, ensure_started and stop are retained as
`authenticated-request-*.http`. These files contain only the explicit synthetic
fixture bearer credential and synthetic job data. The Host includes the
fixture's ephemeral loopback port; this is a test-only destination difference,
not a production port finding. TLS still authenticates `worker.fixture.invalid`.

Root selected an explicit bounded `user-agent: mixer-worker/1` as an additive
eight-header contract amendment for the next candidate. That decision does not
repair or accept these frozen v1 bytes. The next candidate needs an actual
emitted-byte equality check against the amended contract.

## Normal Flight termination: no early reuse reproduced

The reviewer separately suspended the real registered SSL connection process and
issued `GenServer.stop(flight, :normal)` from another task. The stop remained
blocked at 100 ms. After the test resumed the SSL handler, stop completed; the
worker and handler were dead and raw port closed immediately after stop. The
role accepted normal retirement without quarantine. This control **did not**
reproduce premature permit reuse through ordinary normal system termination.

Source inspection still shows that RoleGuard classifies Flight DOWN `:normal`
as retirement, rather than receiving a separate cleanup attestation; ordinary
`finish/1` observes worker/raw/connection DOWN, whereas external system stop
runs `terminate/2`. This is a proof limitation for untested interleavings, not a
third reproduced defect. `normal-flight-stop.json` records the distinct result.
The suspended handler was resumed and all owned resources retired. An earlier
unbounded test-harness wait hit its outer deadline; its owned command group was
disposed and the retained attempt explains the corrected bounded control.

## Executed controls and scope

The producer suite independently replays as 25 tests, zero failures/skips/
exclusions. Thirteen additional independent tests pass as **finding and
regression controls**: some intentionally assert the observed defects. Passing
these controls is not candidate acceptance.

The independent controls cover fixed request path/auth separation and fresh
nonces; every response binding field and nested owner/expiry/ref mismatch;
HTTP version/status/header syntax, canonical length, duplicate case-insensitive
fields, count/line/aggregate bounds and unsupported framing; the exact 32,768-byte
JSON limit; duplicate and escaped-equivalent members, depth/token/string limits,
exponent type mismatch and invalid UTF-8; byte-fragmented valid responses,
truncated headers/body, pipelined responses and delayed extra bytes after the
declared body; and one absolute deadline across delayed headers, body and EOF.
The progressive 1,800 + 1,800 + 1,800 ms control returned uncertain at about
5,000 ms. Producer replay also covers complete-response/no-EOF and one-byte/final
body-byte barriers, confirming the withheld-final-byte fix under these controls.

Process controls cover registration of the raw port, SSL handler and SSL socket
before authenticated send; caller loss during handshake and after authentication;
worker death while its Flight is suspended, retaining its permit until resumed
cleanup; owner loss with the surviving guard; normal Flight stop; and guard loss
with replacement admission. Decimal and configuration controls include int64
boundaries, wrong numeric/string types, leading signs/zeros, invalid tokens,
endpoint/resolver constraints, CA-size/count bounds and startup revalidation.

The exact command is:

```text
python3 verification/hosted-worker-transport-independent-review/run.py
```

The packet records actual Elixir/OTP/OpenSSL versions, commands, output hashes,
source binding and compiled BEAM hashes. The final run removes extracted inputs
and compiled output; each owned command group is disposed. Executable assertions
verify synthetic-key directory removal, Flight/resource retirement and fixture
handler cleanup. No cloud/provider/database, hosted application startup, native
instance, phone, UI, Git operation or production credential was used.

This is an isolated macOS library review with synthetic loopback TLS. It does not
qualify production DNS/egress, Linux hard memory/CPU/task/FD/native-TLS resource
isolation, crash/core-dump or retention controls, real controller persistence,
provider execution, tenant/source/artifact/result authority, signing, native
dogfood, hosted release/CI or any GA gate. Those dependencies remain pending.
