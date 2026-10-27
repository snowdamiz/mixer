# String provenance correction candidate

This separate packet addresses R1–R5 from the frozen independent return. It is
an offline source146 candidate for root release and fresh independent review.
It selects no L_str, complete host budget, P0 caller, operational account, OTA
authority or GA gate. Source146 and host11 remain unchanged. The future outer
candidate beginning `27deef` requires a separate rebind and review.

The original producer seal is
`b228f62a0751e6d1b45e27edabe500cc5e52449db1d33ee59abca0f695b6fa2f`
(114 members, 6,305,257 bytes). The original independent seal is
`741e104537fc3ddc57fc499a764cca9fedaa2b42d2fe109eeb590504b01241d9`
(108 members, 6,581,268 bytes). Both complete packets are rehashed, membership
checked, and unchanged. The binding correction contract is
`b699930771cb7980b1ced76867c4d8a9760014be80c7fa63e4057145e6883341`.

## Corrections and evidence

| Requirement | Correction |
| --- | --- |
| R1 | Every MIR local scope is parsed, with complete array types through internal semicolons. All 80 direct str assignments are retained, including f0279::_35 line 256 and f1035::_29 line 203. |
| R2 | Typed named function items are expanded before external classification. Duplicate enum-constructor bodies remain distinct. The graph has 525 bodies and 1,908 authored/closure/named edges: all original 1,879 edges, 28 named edges at 22 sites, and f1605→f1697. |
| R3 | Basename, std/core prefix, reference/generic receiver and comparison-method waivers are removed. A closed catalog binds 1,127 full external target identities and 1,130 exact argument/result signatures. Unknown targets, changed typed signatures, unknown function items and indirect calls refuse. |
| R4 | The source/MIR induction candidate retains all typed statements, all 2,009 compiled-body hashes, direct and nested ports with incoming typed operands, source carrier declarations and owner spans, failure latches, policy control dependence, callback bodies, returns/errors, retirement and Drop evidence. |
| R5 | Original failed producer attempts 006/007 and independent adverse attempt 006 are copied exactly under history/, still failed. New failed preparation/trace attempts remain in commands/. The unchanged 14 old methods and 16 correction methods pass, including the six originally failing expectations and end-to-end unknown nested-carrier controls. |

The named authored sites comprise 15 AccountedWasi::usage sites, one
snapshot_configuration_v2 site, three Runtime sites and three Stop sites. The
three Runtime and three Stop sites each resolve both retained compiler bodies.
Two standard Option predicate callbacks are separately retained with their
exact receiver and function-item parameter/result types; they are not counted
as authored graph edges. The ordinary external frontier has 3,209 call sites.

`external-contracts.json` is a deliberately finite interface catalog, not a
general standard library classifier and not a graph-hash waiver. Each entry
binds the complete namespace/receiver/trait/member identity and exact typed
argument/result combinations. Its byte pin is custody of those contracts.
`prepare_contracts.py --check` reproduces it from the pinned independent
frontier and newly parsed compiler-local types. Unknown instantiations require
new interface review. Existing conservation classifications are retained as
source146 candidate contracts for the fresh independent reviewer; they do not
grant support to another graph. Authored definitions resolve before the
external catalog. Unselected MIR inline-assembly operand forms can be lexed,
but selected inline assembly is explicitly refused.

`carrier-induction.json` supplies the complete compiler origin census, a
conservative source-declaration carrier index and the incoming/return/field
trace. All typed statements remain in `graph.json`, so the filtered carrier
index is not used to exclude instructions by spelling. It deliberately
overcovers declarations with shared names and includes Policy as a control
dependency. In source146, Policy::Frozen(&Limits) contains scalar/profile limits
rather than a direct arbitrary string field. The policy substitution remains
excluded: the selected validator must construct Policy::swift, and the other
policy_identity branch panics. The original source-review text is retained
unchanged as historical evidence.

The origin pool has 1,958 allocation occurrences, 1,464 unique allocation IDs,
zero unresolved allocation references, 3,189 cooked str literal occurrences and
1,397 unique literals. Maximum literal UTF-8 extent is 92; maximum allocation
extent is 5,080. That 5,080 envelope remains a conditional candidate. It does
not bound arbitrary public SwiftRunFailure.code or lower Reader/Meter/Fault/
cleanup inputs. Static lifetime and pointer width supply no byte ceiling.

The exact caller contract still requires the unmodified loader-produced
selected proof, fresh control with no incoming failure or cleanup latch, exact
selected callbacks/specializations, no policy substitution and no intervening
mutation. Path/OsStr native backing and io::Error backing remain separate opaque
allowances. No syntax scan alone, source envelope, passing checker, or candidate
seal authorizes release.

## Reproduction

Before freezing, `run.py` records bounded pure Python children, source script
snapshots, data digests before/after, Python version/executable digest, argv,
source146 revision, output, exit status and waited-child state. It uses
`PYTHONDONTWRITEBYTECODE=1` and `-B`. Initial interactive reading and source edits
are preparation, not qualifying receipts. Failed attempts are retained.

The final sealed `qualifying_receipts` point to passing executions of:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B verification/swift-guarded-snapshot-string-provenance-correction/run.py test_provenance.py
PYTHONDONTWRITEBYTECODE=1 python3 -B verification/swift-guarded-snapshot-string-provenance-correction/run.py test_correction.py
PYTHONDONTWRITEBYTECODE=1 python3 -B verification/swift-guarded-snapshot-string-provenance-correction/run.py prepare_contracts.py --check
PYTHONDONTWRITEBYTECODE=1 python3 -B verification/swift-guarded-snapshot-string-provenance-correction/run.py derive.py --check
PYTHONDONTWRITEBYTECODE=1 python3 -B verification/swift-guarded-snapshot-string-provenance-correction/run.py check.py
PYTHONDONTWRITEBYTECODE=1 python3 -B verification/swift-guarded-snapshot-string-provenance-correction/run.py custody.py --check
```

The recorder refuses to write after the packet is sealed. Reviewers can run the
same checker scripts directly with `-B` and the shown read-only arguments,
without `run.py`, and record their results in their own review directory.
`derive.py` without `--check`, custody.py without `--check`, prepare_contracts.py
without `--check`, and freeze.py are preparation writers and must not be run
against a frozen packet. No frozen one-shot producer helper is imported.

No compiler, product runtime, native simulator/emulator, phone, UI, capture,
Git operation, global process inventory, or active outer/native-work directory
was used. These remain explicitly pending where required. All owned pure host
children were waited. No native test instance or capture process was started;
other projects' processes and data were preserved.
