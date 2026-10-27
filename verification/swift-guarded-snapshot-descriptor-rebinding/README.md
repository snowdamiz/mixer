# Exact private source145 / host11 descriptor preparation

This compact candidate rebinds the private loader's selected distribution count
from **144 to 145**, with the **same eleven host support members**. It preserves
every other loader byte, including the complete manifest/command/environment/
compiler commitments, header and digest checks, File/session/executable checks,
budgets, original typed failures, private carrier, capability ownership and
source equality. No arbitrary caller count or new authority API is introduced.

The candidate source tree is
`450b6d9b3a05d160e19fa888b68173286b8f6af20ecc7216fdf86283f09b308a`.
The unchanged host support tree is
`027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2`.
`source-manifest.json` and `host-support-manifest.json` contain every selected
path, byte extent and SHA256. The existing frozen Path-component ordering is
preserved when hashing the canonical sorted-key JSON member roster.

The exact source recipe is the root-selected constants-only funding source144
`7e3e861ca65d8c6359623443d6a7810b878c1029494a0ae557307d35ed43484b`
from producer225 seal
`e006b90b8c9e351e0d4dd504c6de309e2c7970b628fe9fc4f788cb30e77bedf7`,
plus three retained overlay paths:

- `retained_profile_loader_v1.rs`: the single literal `144 -> 145` edit.
- `cache/initial_profile_v1.rs`: only the private, unused emission module
  declaration, preserving the actual funding/phase implementation.
- `cache/initial_profile_v1/emission_bound_v1.rs`: the exact accepted unused
  853-byte helper, SHA256
  `ef14f2fe335eb822141ae802f822ddf41a3ba81729d2e5b436d3940cf1946c8a`.

`source-delta.patch` closes all differences; 142 existing source members remain
identical. `prepare.py` reconstructs this exact scope from the frozen inputs and
verifies their complete 225- and 58-member seals. The eleven support files,
original loader contract and historical loader runner are verified as selected
members of the accepted frozen loader packet. This does not claim a new complete
1,050-member loader replay. The historical host support runner is retained as
support identity and is not executed or silently adapted. `input-custody.json`
records the exact distinction.

The new preparation/compile runner, controls, compiler, Python and four SDK
declarations occupy separate orchestration/tool manifest fields. They are never
counted among host11. Each build first reconstructs and verifies the entire
source145 roster, verifies the exact support11 roster, and derives all five
existing `option_env!` values freshly from the actual complete preimages:

| Compile key | Exact preimage |
| --- | --- |
| `MIXER_LOADER_MANIFEST_SHA256` | Canonical complete distribution/support/orchestration/tool manifest |
| `MIXER_LOADER_COMMAND_SHA256` | Counted actual compiler argv bytes |
| `MIXER_LOADER_COMPILE_ENV_SHA256` | Counted sorted clean compiler environment, excluding the five injection keys |
| `MIXER_LOADER_COMPILER_SHA256` | Actual compiler executable bytes |
| `MIXER_LOADER_COMPILER_VERSION_SHA256` | Exact fresh `rustc -vV` output |

The actual positive compile environment contains PATH, TMPDIR and
CARGO_MANIFEST_DIR plus those five derived keys. Intentional negative harness
builds change only the manifest key's presence/encoding/value, with both intended
and actual injected values recorded. `preimages/` preserves the complete manifest,
argv, environment, compiler version and MIXLBD01 record for all twelve compiles.
Each record uses the literal source145/host11 contract and the freshly measured
actual output digest/extent. Metadata records refer to compiler metadata, not an
executable that could satisfy real loader ingress. Pure harness records refer
only to that separately identified harness executable.

Fresh Rust **1.99.0 / aarch64-apple-darwin** evidence consists of **22 final
commands**: compiler version, Git context, four real-candidate metadata builds,
eight standalone pure descriptor builds and eight bounded pure executions.
Debug and optimized production and cfg(test) metadata compilation pass. No Mixer
executable is dispatched. In each mode, 41 pure controls pass and the missing,
malformed and stale compiled-identity harness variants refuse as specified.
The 82 positive-context controls include old/foreign cardinalities, header,
section and list boundaries, manifest digest drift, a same145/host11 altered
valid-JSON source hash with a recomputed header, changed argv/environment/version
commitments and compiler identity. Matching counts alone never accepts those
changes. `verify.py` freshly passes 61 evidence/custody groups.

`host/descriptor.rs` copies the actual candidate parser, compile identity/digest
block and platform CommonCrypto wrapper verbatim. `extraction.json` identifies
each fragment. Only the unrelated validator-error name is stubbed in this
standalone scaffold. There is **no type-layout claim** from it; full candidate
metadata compilation uses the actual types. Two explicit pure controls show that
this extracted boundary alone does not authenticate the actual executable digest
or extent; the unchanged real loader performs those later checks, as well as the
source, session, process, budget, File and validator checks. Genuine loader entry
is unrun and unqualified here. The existing trusted-launcher/quiescent-local-host
scope is unchanged; count/hash rebinding does not confer package, signature or
release authority.

Two preparation failures are retained. The first compared lexical string order
with the frozen Path-component ordering and refused before source or compiler
work; its exact prior script and transcribed exception summary are preserved.
The first pure scaffold compile then rejected copied `pub(super)` declarations
at crate root. Its actual compiler outputs, commands, preimages, previous runner,
scaffold and controls are retained under `attempt-history/pure-scaffold-v1`.
The correction only encloses the verbatim snippets in a private harness module.
The fresh final run is separate. The failed source scratch was inventoried,
proved reconstructible from the retained frozen inputs, and removed after all
recorded owned child groups were absent. Final compiler metadata and standalone
binaries were measured then removed; all final owned groups were terminally
waited and absent, and final owned scratch was removed. No global process
inventory or unrelated process operation occurred.

`WorkAuditPending`, conservative Construction cleanup, all fixed memory/work
budgets and fixture grants remain byte-for-byte unchanged. The helper is unused;
no evaluator or writer delegation is wired. The phase-retention amendment is
absent. Any future phase-retention/delegation/source composition needs a new exact
manifest and fresh compile keys, with its full storage/work/lifetime review.
Source/storage/work/host pre-ingress obligations, real caller qualification,
operational writer admission and genuine writer execution remain pending. Native,
device, simulator/emulator, UI and capture checks stay paused and unrun. Canonical
integration, publication, immutable separate-repository FieldLog packages,
OTA/store/customer/operations and every GA gate remain pending.

`prepare.py` and `run.py` write evidence and refuse a sealed packet. Run them only
in a new unfrozen copy. `python3 verification/swift-guarded-snapshot-descriptor-rebinding/verify.py`
is read-only and may be rerun against the frozen packet. No canonical, Git or root
metadata files are edited by this lane.
