# Fresh Swift host-contract layout replay

The private imported-host contract now has a fresh compiler-layout replay with
source and executable provenance. This evidence still concerns uncalled methods
and metadata printing only. No host import, interpreter loop, full Swift
payload, Ready/public invocation or runtime accounting integration executes or
passes here. The proposed amounts remain against the pre-growth source and
require rebasing and remeasurement after accepted growth integration.

Read the [frozen contract](swift-host-dispatch-contract.md),
[replay receipt](../verification/swift-host-dispatch-layout-replay/receipt.json)
and [offline verifier](../verification/swift-host-dispatch-layout-replay/verify.py).
The original contract packet is preserved byte for byte across 256 saved files,
including its command receipts. Its shared-target metadata outputs remain
historical proposed numeric values. Final-source layout acceptance uses this
fresh replay's compiled artifacts and exact-binary output.

## Source and executable binding

Each original final metadata archive is reconstructed into a new owned source
directory and every archived file is checked. The metadata closures each have
126 files: the original 125 VM inputs plus the metadata-only binary source.

| Reconstructed source | Full canonical source closure |
| --- | --- |
| Baseline metadata | `0a98a2f54f3934c23b9780a1f084db572e2bbc3fe2de91b107ba69be1aea9984` |
| Candidate metadata | `39f353864fbaddfd8721a60285206204ae935639cbfc28f767bcfdf30568f26d` |

Sixteen contexts cover baseline/candidate × Swift/all features × Debug/Release
× production/unit. Every context starts with a distinct empty Cargo target
whose path includes the complete source digest, feature, profile and context.
Targets are never shared across source variants or contexts. The selected
Cargo compiler artifact reports `fresh: false` in all sixteen builds.

Each context retains the complete Cargo JSON build output and selected artifact
JSON, exact executable path, executable size/SHA-256 and a compressed copy of
the exact executable. The metadata binary is run directly from that selected
path; Cargo does not choose an executable during measurement. Hashes are
recorded before/after execution. Unit artifacts also retain their full actual
`--list` output, parsed test names and executable hashes around listing.

All eight unit artifacts list the intended exact layout test once. Swift-only
artifacts list 201 tests; all-feature artifacts list 230. Each unit measurement
runs that exact named layout test with one test thread and reports one pass.
No other listed test runs. Baseline/candidate full lists match for each feature
and profile. Production contexts execute only the metadata printing binary.

All 44 commands—sixteen builds, sixteen exact executions, eight test listings
and four tool-version reads—check every source file and full closure both
before and after execution. The command receipts bind exact argv, environment,
source manifests and stdout/stderr. The final seal binds those command receipts;
only the exact top-level replay receipt excludes itself from its own binding map.

## Observed layouts and scope

Every fresh type, owner offset, positive field offset/size/alignment and total
matches the frozen proposal exactly. Baseline/candidate original owner shapes
and offsets match. Every candidate positive position occupies its own aligned
interval inside its measured containing class. All 4,768 positions are retained,
including 2,324 production, 2,400 additional unit and 44 fixed placements.

| Proposed additive bound against the pre-growth baseline | Production bytes | Unit bytes |
| --- | ---: | ---: |
| New permanent class | 113,760 | 113,760 |
| New active class | 457,016 | 914,312 |
| Proposed execution header | 1,871,976 | 2,766,656 |
| Proposed frame operation envelope | 3,935,984 | 7,213,744 |

Existing memory/bulk totals and original owner layouts agree in each fresh
pair. Ticket maximum remains 86, State remains 134,217,728 bytes and Combined
remains 268,435,456 bytes. These are logical named-object reservations, with no
physical stack, optimizer temporary, allocator overhead or RSS claim.

An initial runner-only attempt assumed the unit Cargo target kind would be
`lib`; this package declares `rlib/staticlib/cdylib`. Its compiler build passed,
but artifact selection stopped before unit execution. That attempt is retained
under `historical-attempt-1` and supplies no final acceptance evidence. All
qualifying contexts were then rebuilt in a new scratch with new empty targets
using the actual `mixer_vm` test artifact from `src/lib.rs`. The metadata source
did not change between those attempts.

The replay retires both uniquely owned scratch directories after checking for
open holders and preserving sources, exact binaries, logs and test lists.
No processes are terminated and no native/device instance, live VM source,
tracker or Git state is changed by this lane. Runtime groups H01–H16 remain
pending; the replay resolves only the layout provenance uncertainty.
