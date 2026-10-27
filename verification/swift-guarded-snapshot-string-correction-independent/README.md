Independent review of the frozen source146 string correction

Decision: return correction candidate
4d2dcab90e7c9cfd7074a67fe8eac0d6807b6ed3704b74afe430ebc624b07994
for further correction. This packet accepts no L_str, complete typed source
closure, whole-host budget, P0 caller, policy, account, product execution, OTA
or GA authority. Root owns selection and delivery.

findings.json and correction-contract.json specify four related defects:

- Authored resolution returns owner/method basename matches after exact-module
  lookup fails. An end-to-end mutation of the full retained MIR changes only
  f0730's control::Fault::new target to foreign::Fault::new; analyze accepts it
  as authored f0982. Unknown std namespace, custom trait on Fault and foreign
  Policy targets also bypass the exact external catalog.
- Closed-trait substitution accepts Foreign receivers for SharedControlV1 and
  experimental MeterControl through unanchored trait/member matching.
- Actual selected f0907 dispatch_v1 and f1405 write_body have truncated callback
  parameter types and corrupted return types in graph.json. The balanced
  independent parser finds six field discrepancies across these two bodies.
  Nine headers in the complete 2,009-body pool are affected; seven are unselected.
  header-discrepancies.json contains the complete exact roster. This inherited
  error is also in the prior independent fixed point. Explicit typed temporary
  locals preserve current simple-local call argument/result signatures, so the
  audit found no downstream simple-local external signature discrepancy.
- Authored resolution checks neither arity nor compatible argument/result
  types. A synthetic control binds Fault::new with one u32 argument and an
  Option<SwiftRunFailure> result. This is a malformed parser/checker input,
  not compiled product evidence or a runtime exploit.

The final independent suite has 17 methods: 10 fail-closed expectations fail,
7 controls pass. The exact external catalog rejects unknown external targets
and changed external signatures; unknown nested carrier producers, function
items, indirect calls, selected inline assembly and changed standard Option
predicate signatures are refused. Full identity and authored type checks must
also hold before a call is accepted as authored. Existing source/compiler pins
remain useful custody but cannot repair those reusable checker claims.

The correction's original 14 tests and 16 correction tests pass. Direct
read-only catalog reproduction, derivation, binder and custody checks also
pass. They fail to expose the new findings. All failed runs in this packet
remain failures: the first adverse run had six failures plus an empty-literal
pool test-harness error; a seed literal removed that error and exposed the
missing authored type check. The independent parser's first strict comparison
failed on f0907; subsequent audit records every discrepancy rather than
calling the malformed types equal. Later adverse suites add both actual
headers and the full end-to-end header regression. Script snapshots preserve
every executed revision. A read-only report replay initially noticed new
verification receipt rows; the stable report now excludes its own read-only
verification runs from its receipt roster, and retains that failed replay.
Preparation reading included one unrecorded
StopIteration from a wrong source-path lookup; this was exploratory, never a
qualifying test or passing receipt.

Custody independently rehashes all members and complete membership of the
358-member correction, 108-member old independent packet and 114-member
original producer. All 541 correction input bindings, source146 and host11,
root release/return pins and retained 76,655,228-byte MIR match. Both old
producer failures 006/007, independent adverse006, and the nine new producer
preparation/trace failures remain unchanged and failed.

audit.py imports no producer analysis. It independently parses every compiled
body, balanced header, all local declarations including nested arrays, every
selected typed statement, primitive string assignment and compiler origin.
It cross-checks selection/edges against the old immutable independent fixed
point; it does not claim a freshly implemented complete Rust MIR resolver.
The 525 body hashes and all 1,908 edges match that independent inventory,
including all original 1,879 edges, 28 named callback edges at 22 sites and
f1605 to f1697. Duplicate Runtime/Stop constructors and both exact standard
Option predicates remain retained. All 80 primitive string assignments are
present: 24 literals, 54 reference/field transfers and two policy returns.
f0279::_35 line256 and f1035::_29 line203 preserve tuple fields. All nine
direct string ports have incoming calls; the correction retains 257 direct
and nested carrier ports. Type-header errors are recorded separately.

source-semantic-review.json binds actual source excerpts, critical complete
MIR bodies, direct incoming ports and raw byte operations. The private fixture
contains paths, byte claims and scalar budgets. The selected loader proof
reaches the leaf unmodified, fresh cancellation/control starts with no failure
or cleanup latch, and the validator constructs Policy::swift. Frozen(&Limits)
contains scalar/profile limits; it is a control dependency, not an arbitrary
string field. Policy substitution stays excluded. Failure constructors,
Reader/Meter/BodyState errors, raw Swift failure mapping, latches, cleanup,
aggregate wrappers, return/error/retirement and Drop preserve supplied
references or drop them. Added configuration callbacks copy numeric fields;
Runtime/Stop constructors move existing carriers. Exact standard container,
residual/branch, scalar and callback semantics conserve references. A finite
catalog or graph hash alone is not the semantic proof.

The independently decoded pool contains 3,189 cooked string occurrences /
1,397 unique values, maximum 92 UTF-8 bytes, and 1,958 allocation occurrences /
1,464 unique IDs, maximum 5,080 bytes, with zero unresolved allocation IDs.
This conservative allocation envelope covers compiled aggregates, promotions
and option_env origins for the exact source route. It cannot bound arbitrary
public SwiftRunFailure.code or lower Reader/Meter/Fault/cleanup inputs.
Alternate callers need a new complete provenance graph; static lifetime,
pointer width and claimed lengths supply no bound. Path/OsStr and native
io::Error backing remain separate opaque allowances. The source reasoning
supports the conditional origin envelope for review, but unresolved type and
identity defects prevent acceptance of the complete typed source proof.

Only this directory was written. Every qualifying command uses run.py here,
which snapshots the scripts, records exact argv/tool executable digest,
source/host tree identity, output, exit status, and frozen inventories before
and after. Children have a 55-second bound; owned process-group termination
and waiting apply only on timeout. No timeout occurred. No compiler, product
runtime, native simulator/emulator, phone, UI automation, capture, Git action,
process inventory or active sibling lane was used. All owned children were
waited. No native instance was created; other processes/data were preserved.
Native checks and complete compiler/binary/runtime correspondence remain
pending. Future outer candidate 27deef is not automatically covered.

After sealing, this checker and the audit/custody checks are read-only:

    python3 -B verification/swift-guarded-snapshot-string-correction-independent/check.py
    python3 -B verification/swift-guarded-snapshot-string-correction-independent/audit.py --check
    python3 -B verification/swift-guarded-snapshot-string-correction-independent/custody.py --check

Do not run the frozen recorder, freeze preparation, or a producer writer.
Adversarial tests deliberately remain red until a separate corrected packet
is released. A new independent review must test the new frozen candidate.
