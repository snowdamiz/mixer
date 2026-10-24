# Independent private Swift host-operation review

No blocking finding was found in the sealed imported-host development candidate.
The candidate is suitable for root integration and integrated-source regression
checks within the selected private contract. This review does not accept a
complete interpreter, public invocation, a release, or a GA gate.

The reviewed candidate is the 128-file source closure
`7ee6194584a5029ff2bbbcb94f8286295411cb3441a04db30c8fd4036d851329`,
archive SHA-256
`e9d134c69cb2a4566f32973a1f728104e263d85f5c8ea7257b775d4072d34645`,
producer seal SHA-256
`3ea5e287af6cf1b82ae16b5db09cb3de70053f4e44fa26d86b140fbc8e7ded09`.
The 127-file accepted growth baseline is
`a0bbe77aca3021e48f1fb76dc97cfbc0406c24e5ba7eacdd33d5dabe8f998d9b`.
Source content is the authority; the requested `11133e60` revision also contains
disjoint hosted work. The reviewer changed no live VM source, producer evidence,
tracker, Git state, or another lane's files.

The review follows binding product-plan section 10, the
[host contract](swift-host-dispatch-contract.md), its
[acceptance scope](swift-host-dispatch-contract-acceptance.md), and the prior
[layout provenance requirements](swift-host-dispatch-layout-replay.md).
The independently reconstructed snapshots, commands, source/binary identities,
failed review harness attempts, and audits are retained in the
[review packet](../verification/swift-host-operation-review/receipt.json).

The complete ten-file diff was reconstructed independently and matches the
sealed patch exactly. Production additions are the imported-host operation,
one pinned imported-Call step, original fixed-storage completion delegation,
and additive reservations. Other changes expose bounded test hooks or update
additive test formulas. Cargo inputs and the prior memory, bulk, and growth
operation sources remain exact. There is no added dependency, public execution
route, defined/indirect call implementation, call loop, host callback, owner,
reservation ticket, host frame, or import pin.

The actual phase checks precede host effects. The import comes only from the
sealed ordered descriptor table, and its complete signature is checked.
Parameter work precedes checked range subtraction, caller-frame/floor checks,
and the full ordered type scan. Signature, frame and cache views end before
borrowing the original argument and memory arenas for the actual dispatch.
`AccountedWasi::dispatch` supplies the sole executor host-entry debit and the
unchanged context supplies adapter metering. Typed adapter faults and exact
unsigned GuestExit codes latch before the postcheck. Successful errno alone
truncates arguments once, reconciles their original live count once, and pushes
through the existing metered value path using the unsigned `u16` conversion.
Rejected live removal retains sticky debt; later push failure preserves reached
host effects without refund or fabricated capacity.

The pinned step copies one instruction through the actual caller pin, ends
that view, installs the invocation cursor, and performs one fuel/instruction,
caller-work and checked-PC prefix. An occupied outcome preserves the existing
slot and prevents another fetch. Consuming a failed slot does not authorize
reentry into the terminal phase. The completion wrapper consumes the actual
fixed storage and delegates the existing completion rule. Its fixtures use
plain `prepare_frames`. A future dispatcher with growth context, replacement
storage or growth debt must continue to use `complete_growth`; this review
grants no combined growth/host completion shortcut.

Fresh independent Rust builds and retained exact executable runs passed:

| Independent run | Result |
| --- | ---: |
| Exact candidate, all features Debug, complete library suite | 265/265 |
| Same exact executable, focused H01–H16 | 16/16 |
| Release test-only overlay, five independent adversarial cases | 5/5 |
| Same Release overlay, H01–H16 regression | 16/16 |

These are 302 test executions with deliberate overlap. The five new cases
check parameter-work rejection before a missing argument range, retention of
locals and the operand prefix across a two-argument import, float mismatches
at every ordered ClockTimeGet parameter, committed stdout and memory output
after post-dispatch cancellation, and refusal to reenter after consuming a
failed outcome. The overlay changes only the test file; the exact candidate
and both overlay sources are archived separately. All runtime/compiler receipts
are from the macOS `aarch64-apple-darwin` host with Rust 1.99.0 (`b940084d7`),
LLVM 23.1.1 and Cargo 1.99.0 (`5f94df478`). These are not mobile receipts.

An independent audit checks all 1,671 producer-sealed files, 285 nested command
receipts, 91 retained artifacts and 36 source archives. It binds every binary
to its exact fresh Cargo JSON artifact and source closure, checks all compressed
streams and test lists, independently reconstructs the patch, and verifies
qualifying MIR/layout completion precedes final library execution. The complete
producer matrix supports exactly 1,014 library, 64 additional host-probe and
64 Frozen integration test executions. Its nine excluded failed commands
remain historical. Those totals were audited from their actual outputs; the
full matrix was not redundantly rerun by this reviewer.

Fresh independent production and unit MIR reproduces the 30 production and
32 unit selected compiler bodies byte for byte. The independent inventory
reconstructs 2,344 production, 2,488 additional unit and 44 fixed placements:
4,876 total. The four unit-return placements of the unit-only dispatch checkpoint
have zero size and empty intervals. All other zero-sized compiler fields also
supply no positive-byte credit. Each named field is checked inside its actual
Host class, so similarly named positions in prior classes supply no credit.

All sixteen exact retained layout executables were independently rerun from
retained byte-identical copies; every printed field, type, owner offset, class
and bound matches. Paired original owners and prior component totals agree.
All positive-sized intervals are aligned, disjoint and contained. Fresh
compiler expansion independently preserves all 39 Frozen methods. The fourteen
original containing declarations and four additional original WASI/control/cache
declarations agree. The accepted 4,800 memory, 4,324 bulk and 10,356 growth
positions remain exact, with ticket maximum 86, State 128 MiB and Combined
256 MiB. These are logical named-object reservations; physical stack,
optimizer temporaries, allocator overhead and RSS are outside this claim.

The reviewed reservation amounts are:

| Bound | Production bytes | Unit bytes |
| --- | ---: | ---: |
| Added permanent class | 113,760 | 113,760 |
| Added active class | 515,320 | 1,040,136 |
| Execution header | 2,188,352 | 3,326,128 |
| Frame envelope | 4,968,208 | 9,155,136 |

The original header and construction authorities admit these additions before
creating the corresponding objects. No prior class, peak, padding or same-sized
alias is subtracted. The three final deliberate borrow violations remain tied
to the final candidate plus their appended invalid source and fail with their
required E0499/E0502 diagnostics. Both final warnings-denied Clippy receipts
are source-bound. Tool versions match the independent builds.

Review harness failures are preserved and excluded from acceptance. One draft
test named a descriptor outside the supported 34-import vocabulary and failed
compilation. Audit iterations corrected historical artifact target fallback,
owner-name scope, compiler body ordering/promoted constants, literal spelling,
and command-prefix assumptions. A production MIR artifact selection assertion
was corrected to use the compiler's actual filename after its successful build.
These were reviewer harness errors; no candidate runtime test failed.

The existing G08 cursorless `remove_live` diagnostic remains an acknowledged,
separately selected limitation. Synthetic malformed-owner/counter/floor/debt
cases do not establish normal guest reachability. Allocation evidence remains
one warmed ArgsSizesGet interval on the measured thread. Actual macOS clock and
secure-random services execute, but deadline checks are cooperative; a finite
post-OS delay does not establish syscall preemption. Full Swift, ordinary
calls and the complete dispatcher, Ready/public routes, native joins, immutable
published separate-repository FieldLog, physical phones, signing, store,
customer, operational, release and GA acceptance remain pending.

The review packet records removal of its uniquely owned scratch after all
sources and executed binaries were retained, a targeted empty holder check,
and a device/inode recheck. No native/device instance was started, no other
project process/data was touched, and no process was terminated. Producer
cleanup is independently checked for consistency with its historical targeted
holder receipt and absent scratch; that historical holder state cannot be
re-observed after deletion. Verify the sealed review with
`python3 -B verification/swift-host-operation-review/verify.py`.
