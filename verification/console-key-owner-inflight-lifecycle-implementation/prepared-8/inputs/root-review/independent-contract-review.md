# Independent inflight lifecycle contract review

Recommend the narrow dependent source slice: a test-build-only common
KeyOwnerSupervisor fixture constructor and the two new KOL08-GRACEFUL/KOL09-KILL
methods. No blocking source-contract finding remains. The packet grants no host
or TLS execution and implements no constructor. A fresh exact implementation,
runner and source/tool/artifact plan still need review and root release.

Producer freeze:
dcf68267fbfe7d495f0cf92de97e2a46f140d1c9bd8f5a353bebacadf66ce276.
Independent preaccess seal, created before producer access:
5eefedd3a222e31c5d580e48bfd22e41de6422ef185744e1cf7ae4f722956d4f.
The audit verifies all 39 members and 30 source inputs against their pins,
upstream manifests and current origins, including copied upstream freeze.json
files. All 24 preaccess members remain unchanged.

The contract addresses the independent controls. TLSFixture's response-ready
barrier occurs after successful handshake, parsed HTTP request and recorded
SNI/protocol; this is stronger than the RawFixture handshake stalls in K07g/K07h.
No response body, completed JWKS fetch, snapshot or authenticated identity is
claimed. The actual flight/worker/controller/raw-port and two queued callers
must be observed before the trigger, with 750 ms remaining on the unchanged
original deadline. The direct real checkout caller distinguishes an explicit
waiter reply from public safe_call fallback and ConfiguredVerifier's potentially
blocking after-release call. The held controller and exact resource monitors
support the parent-stop and replacement barrier without treating unrelated
message arrival order as a causal total order.

The absent DynamicSupervisor terminate_child exit and replacement-before-old-
resource-DOWN remain source-derived adverse possibilities, not observed facts.
The producer correctly allows FetchFlight to enter its own termination on OTP
parent death while its controller remains suspended. This refines the preaccess
hypothesis: the generic EXIT catch-all concerns nonparent linked exits; it must
not be interpreted as proof that OTP parent exit is swallowed. A callback fault
or early replacement still fails the clean KOL09 resource gate even if public
denial and eventual cleanup work. Original KOL08 owner crash remains pending.

Carry these root-coordinated requirements into the implementation and exact plan:

- Reuse the existing seven ordinary KOL01-KOL07 regressions alongside the two new
  methods because common supervisor child construction changes. This means nine
  executed methods and two new methods. The immutable proposal's fixed count of
  two describes its original new-case-only proposal; the future exact terminal
  roster/count must incorporate this explicit root amendment.
- Derive fixture owner construction from the ordinary KeyOwner.child_spec and
  shared topology, changing only the selected test start MFA. Preserve identity,
  infinite shutdown, derived worker name, order, strategy and restart limits.
  Guard both the fixture constructor and fixture tuple init dispatch under the
  test build. Guarding only start_fixture leaves production init/1 callable as a
  bypass. Preserve ordinary rejection of fixture options and all production
  DNS/global-address and TLS verification source. Do not add a production fixture
  flag or mutate running owner state.
- Interpret warning rules narrowly and explicitly: compiler diagnostics must be
  empty; intentional exact-worker kill may generate expected OTP supervisor
  reports, which must be retained and classified by actual source/cause. A
  terminate callback exception is a gate failure. Do not use a broad textual
  warning/error suppression rule or count an expected-defect witness as a clean
  resource pass.
- Capture server handler/socket/controller and listener/acceptor identities
  before TLSFixture removes them from bookkeeping. Its terminate callback does
  not await all DOWN, so stop returning is insufficient cleanup proof. Preserve
  barrier stage, original deadline, exact callback reason and unfinished resource
  identities on assertion/timeout. Resume/release exact suspended/barrier PIDs in
  after and retain recovery separately from the ordering result.

The earlier seven socket-free cases are already accepted by the root receipt
bound in the independent preaccess inputs. The producer's historical report that
their terminal review was pending describes its knowledge at preparation; it
does not reopen that accepted boundary or qualify these new TLS cases.

No producer Python was executed/imported, no product source was edited, and no
compiler, formatter, runtime, fixture, version process, global inventory, native,
UI, capture or phone action occurred in this review. Production builds/exports,
actual TLS lifecycle outcomes, original owner-crash adaptation, app/provider/
HTTP/browser/session integration, operations, custody and every GA gate remain
unverified by this source-contract review.
