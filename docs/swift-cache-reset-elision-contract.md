# Private Swift cache reset elimination

Root selects this additive amendment for a bounded implementation candidate.
It supersedes only the requirement in `swift-cache-stage-contract.md` to clear
and charge every scratch slot before each Swift scan/build pass. Historical
contracts, packets and legacy traces remain unchanged.

The source baseline is the 132-file VM closure
`f2682c6a2fd6f6e74bd00a2394ff32b704aa1e2ed3d2373ef95cdee29fa7eb2c`
at checkpoint `7744c1cc28b24a46f4339b25b38ce4d0cf76cbe8`. Root verified the
diagnosis seal `7c1cecccfb4143fb07a01e779439e8d171ba373092a1eddcd969490101b76cd8`,
17 packet members, ten input references and the live source closure before
selection. See `swift-cache-work-diagnosis.md` for the original observations.

Delete both redundant clearing loops, including their charges. Do not retain
uncharged clearing work. Keep the initialized, exactly reserved 512-element
arena, its constructor work, all three fixed buffers and conservative phase
accounting. Before each pass, check the exact arena length and call the ordinary
operation meter's explicit check at the existing reset boundary. Preserve
failure precedence, sticky terminal failure, cancellation and deadline checks.
Keep the existing internal boundary identities unless a necessary rename is
coordinated; names alone do not imply that slots are still cleared.

Both passes start at depth zero. Every activated slot must be completely written
before depth increases; all reads must be restricted to the initialized active
prefix. Stale inactive records may remain but must never affect decoding. Retain
both complete passes, all actual byte/local/instruction/target/patch charges,
descriptor checks, count/build agreement, allocation checks, admission and
publication checks. No shared decoder algorithm, frozen legacy wrapper, public
layout, revision, identity, dependency, cache policy or runtime limit changes.

The candidate is isolated until root acceptance. Ownership is private Swift
`cache.rs`, private test files and its candidate/evidence directory. Tests may
exercise the existing shared borrowed decoder through a test-only seam; shared
production decoder files stay unchanged. A new stored field, temporary inventory
or helper borrow that changes the phase accounting requires coordination before
implementation. No full-reactor retry is selected by this amendment.

Acceptance requires actual-owner dirty-scratch tests before both scan and build,
independently expected IR and targets for flat/sibling/nested/br_table shapes,
deep-to-shallow reuse and inclusive depth 512 with depth 513 validation rejection.
Malformed controls must fail without reading inactive records. Exercise every
shorter work budget and cancellation point on a finite representative body,
including both pass boundaries, with unchanged failure precedence and consuming
zero cleanup. Retain deadline, count/build mismatch, capacity and allocation
failure controls. Check monotonic LRU and identical victim/pin behavior for the
same successful access sequence; numeric timestamps may reflect less actual
work. Zero-allocation hits/releases, retained byte ledgers and frozen legacy
traces remain required. Record bounded commands, tools, exact source and outputs.

This selects implementation work, not full Swift parity, native/public/signed
use, published FieldLog dogfood qualification or any GA gate. All original
runtime budgets remain unchanged. The original failed target remains immutable.
