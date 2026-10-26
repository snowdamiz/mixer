"""Reviewer-owned custody/excerpt consistency controls; no Rust execution."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PRE = HERE.parent / 'preaccess'
SNAP = HERE / 'candidate-snapshot'
LIB = SNAP / 'verification/swift-cache-state-implementation/source/library'
HASH = 'd0e2ec2998f70958e10a7dbf33742917ced66cd4559bafb88bcabe8b221a54db'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def span(name, start, end):
    lines = (LIB / name).read_bytes().splitlines(keepends=True)
    raw = b''.join(lines[start - 1:end])
    return {'file': name, 'source_sha256': sha((LIB / name).read_bytes()),
            'first_line': start, 'last_line': end, 'excerpt_sha256': sha(raw),
            'excerpt_utf8': raw.decode()}


def main():
    assert sha((LIB / 'cache_state.rs').read_bytes()) == HASH
    manifest = json.loads((HERE / 'candidate-snapshot-manifest.json').read_bytes())
    for member in manifest['members']:
        raw = (SNAP / member['path']).read_bytes()
        assert len(raw) == member['bytes'] and sha(raw) == member['sha256']
    prefixes = []
    for old_name, name, digest in [
        ('13-analyzer.rs', 'analyzer.rs', '1ef11e06678642231f783fea0e5fe376e8b1912730a6fb696a653ab04cb2043b'),
        ('14-envelope.rs', 'envelope.rs', '2cd286a387ce336a18ea2872974e371ca4e772e2fd801f2186a3f62ce639bfef')]:
        old = (PRE / 'inputs/verification/swift-semantic-adapter-prerequisite/inputs' / old_name).read_bytes()
        current = (LIB / name).read_bytes()
        assert sha(old) == digest and current.startswith(old)
        prefixes.append({'name': name, 'old_sha256': digest, 'old_bytes': len(old),
                         'current_sha256': sha(current), 'unchanged_prefix': True,
                         'additive_suffix_utf8': current[len(old):].decode()})
    prerequisite = PRE / 'inputs/verification/swift-semantic-adapter-prerequisite'
    seam_table = json.loads((prerequisite / 'source-seams.json').read_bytes())
    seams = []
    source_identities = {}
    for s in seam_table['seams']:
        raw = (prerequisite / s['snapshot']).read_bytes()
        assert sha(raw) == s['source_sha256']
        excerpt = b''.join(raw.splitlines(keepends=True)[s['first_line'] - 1:s['last_line']])
        assert sha(excerpt) == s['excerpt_sha256']
        assert excerpt.decode() == s['excerpt_utf8']
        source_identities[s['snapshot']] = s['source_sha256']
        seams.append({k: s[k] for k in ('name', 'snapshot', 'source_sha256', 'first_line', 'last_line', 'excerpt_sha256', 'authority')})
    ranges = [
        ('cache_state.rs', 104, 173), ('cache_state.rs', 195, 231),
        ('cache_state.rs', 241, 282), ('cache_state.rs', 301, 355),
        ('cache_state.rs', 357, 446), ('cache_state.rs', 447, 508),
        ('cache_state.rs', 509, 563), ('cache_state.rs', 564, 613),
        ('cache_state.rs', 614, 699), ('cache_state.rs', 700, 766),
        ('cache_state.rs', 770, 792), ('cache_state.rs', 896, 1066),
        ('cache_state.rs', 1067, 1245), ('cache_state.rs', 1246, 1396),
        ('envelope.rs', 127, 225), ('analyzer.rs', 103, 156),
        ('analyzer.rs', 250, 339), ('analyzer.rs', 340, 380)]
    write('source-audit-independent.json', {
        'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'python': sys.version,
        'script_sha256': sha(Path(__file__).read_bytes()),
        'snapshot_member_count': len(manifest['members']),
        'snapshot_bytes': sum(m['bytes'] for m in manifest['members']),
        'unchanged_prefixes': prefixes, 'historical_source_identities': source_identities,
        'source_seams': seams, 'candidate_excerpts': [span(*r) for r in ranges],
        'live_VM_relation': 'unavailable; historical copied sources read as data only',
        'scope': 'hash/excerpt/prefix consistency only; manual source reasoning is separately recorded',
        'candidate_Rust_executions': 0, 'product_tests': 0})

    observations = {
        'P01': ('custody-verified-access-order-deviation', 'Root admission and all 454 hashes verified by unchanged runner before compilation. Exact three Rust copies were staged before first source read; the separate full 454-member snapshot followed the first header/index read. The snapshot manifest records that order; it is not rewritten as a strict full-snapshot-before-read pass.'),
        'P02': ('source-supported', 'All named historical source seam excerpts and four full source hashes independently reverified. Plan identity, resident eviction/publication and optional failure cursor rules are relations to these copied sources only; current live VM parity is unavailable.'),
        'P03': ('source-supported-scoped-execution', 'Both old library prefixes are byte-identical; additions only reexport/load the new module or cfg-disabled tests. The new safe public signature takes four mutable Files. Public basics retain inherited diagnostics/report. Both old API runtime regression suites were not executed by this lane.'),
        'P04': ('source-supported', 'cache_walk 1127-1176 performs actual read, record_fields, coordinate and old envelope debit/reply audit before constructing same-iteration private Loan; borrowed record/config, arena/Candidate exclusively borrowed, SemanticReply carries no references. Fifteen attributed public API compile controls pass their expected dispositions.'),
        'P05': ('source-supported-matrix-unrun', 'Unchanged profile/full_identity/record_fields validate the closed 16-word kinds, profile identities, widths/sentinels and immutable fields; semantic checks add actual row joins. Context/header/footer checks remain inherited. All-word and transition fixture execution remains unrun; source support is not full matrix credit.'),
        'P06': ('source-supported', 'Arena::new initializes all64 resident/token rows and512 plan sentinels; selected limits come from actual fixture_context. Nonce1 and control cells are initialized before walking. Semantic probes use selected rows; writes touch only one validated resident/pin/plan delta and named scalar cells. No second growing invariant map exists.'),
        'P07': ('source-supported-matrix-unrun', 'Actual full_identity gates ordinary body-bearing public records; AcquireBegin alone permits an undefined function. semantic 460-471 checks nonceMAX, actual first-free pin, and exact hit/miss requested resident. Successful publication advances nonce, so current nonce stays remembered during an active operation. Boundary controls beyond basics are unrun.'),
        'P08': ('source-supported-matrix-unrun', 'semantic 472-508 computes function&511 and actual empty/conflict/match from the prior cell. Matching offset/length/type must agree. Only PlanEnd empty/conflict stages/publishes40 bytes; PlanBegin and match retain the row. MissReady joins known bytes and updates requested_bytes. Full conflict mutation coverage remains unrun.'),
        'P09': ('source-supported-matrix-unrun', 'Actual resident bytes use checked_add before any arena mutation; MissReady positive/entry/base/capacity constraints are inherited and rechecked, exact known plan bytes required. Headroom subtraction follows proved base+request<=capacity. Overflow refusal is source-supported; adversarial private sum controls are unrun.'),
        'P10': ('source-supported-private-victim-controls-unrun', 'Six-pass stable sort uses MAX only as ineligible index, not timestamp. Stable left ties over initially ascending indices gives (timestamp,slot). Prefix stops at first feasible remaining sum+destination, starts at first_empty, replaces destination on each selected victim. trailing_zeros emits ascending slot. Full private victim ordering/obstruction controls are unrun.'),
        'P11': ('source-supported-scoped-execution', 'semantic 564-607 requires feasible plan, first outstanding selected slot, exact pending bytes/unpinned resident. Taken stages empty row and commits immediately; Commit requires that Take/empty row and saved pending bytes. First Failure returns before new row mutation, so previous Take is retained. No rollback/refund path exists.'),
        'P12': ('source-supported-matrix-unrun', 'BuildBegin/Ready require complete feasible committed selection and exact requested bytes; neither stages resident/token. Publication joins exact hit or planned destination, actual remembered/current first-free pin and current nonce, postcount and bytes, then stages resident/pin and publication work. Full seeded numeric/corruption controls remain unrun.'),
        'P13': ('source-supported-scoped-execution', 'Old envelope requires Idle release; inherited full_identity joins function/offset/type and lenMAX. semantic 668-696 joins exact pin slot+nonce and resident function/bytes/postcount; resident is copied and only pins updated, retaining age; pin is cleared. Full stale/double/wrong-entry matrix remains unrun.'),
        'P14': ('source-supported-scoped-execution', 'Accepted Failure returns reject14 at333-335 before scratch/row access. Caller increments calls/latches14 without replacing Q and performs cleanup. No later semantic dispatch; old framing/envelope may continue. Projection uses prior Q and M+1 failure coordinate, subject to earlier terminal suppression.'),
        'P15': ('rejected-confirmed-Q9-Q10', 'shape_q 210-214 unconditionally reads planned masks, violating Q10 outside stages6..10;216-219 omits feasible=true for stage7/8, violating Q9. Seven admitted seeded private witnesses reproduce both guard failures in default and optimized builds with exact full32 differences. They establish no public from-empty reachability. All remaining terminal matrix cases are unrun.'),
        'P16': ('source-supported-private-IO-controls-unrun', 'Caught input Err is evaluated first in projection (Binding15=>Unavailable2, Budget4=>Limited1, other=>Unavailable3), before poison. Macro write_report? and final budget Err return no aggregate; sole Ok follows them. All old fixed errors are propagated/caught without replacement except intended framing observation. Fault-injected actual IO/error matrices were not executed.'),
        'P17': ('source-construction-proved-zero-runtime-credit', 'Sole product Paid literal1293-1297 has1/1/0, after propagating finish256 and setup512 reservations1291-1292. Only records changes after replay8151 succeeds1123-1125. Sole production aggregate Ok1367 is in that same macro body. No public constructor/clone/copy. Thus returned Ok with00/01/10 cannot be constructed by this source. Three exclusions remain zero runtime passes.'),
        'P18': ('source-supported', 'Full ARENA_BYTES exact-length check1088 before Candidate and1157 before Loan, immutable constants/valid selected limits prove all arena/Candidate row, scalar and12 restore ranges. Child leaf receives exclusive nonresizable slice; no Vec resize occurs. Config lives outside mutable arena and supplies validated limits; same underlying vector/array is retained through cleanup.'),
        'P19': ('source-supported-complete-initializer-accounting-pending', 'One named Candidate [u8;2048] initialized1092 and borrowed sequentially; never returned/passed by value. No per-record full zero array source; cleanup uses one8-byte zero word. Source/destination initializer and helper-place attribution still belongs to the complete lifetime obligation P28, not a size-only acceptance.'),
        'P20': ('source-supported', 'Actual semantic call1170 always returns to audit, optional committed Q extraction and sole cleanup1204; no ?/outer return inside1160-1207. Semantic contains no callback/IO/allocator; proved ranges exclude panics. Reader/field/framing errors happen before current loan or after previous cleanup; footer/drift/report occur after record scope.'),
        'P21': ('functional-source-supported-debit-pending', 'cleanup770-792 has256 direct8-byte zero stores, then12 direct already-LE arena-to-Candidate copies restoring888..984-exclusive from CELLS. No LE decode/re-encode or full2048 argument. Exact group6 scalar/address/loop final-test attribution remains pending; count of stores alone is not a debit proof.'),
        'P22': ('source-supported-injected-fault-controls-unrun', 'Commit status failure returns poison16; caller still cleanup, audits or cleanup false latch16. Future outer1135 requires terminal!=16 before either leaf; semantic also requires terminal0. Poison suppresses every extent. Current private run tests shape/projection only and receives zero commit/cleanup fault-pass credit.'),
        'P23': ('not-closed-exact-microoperation-ledger-required', 'Reservation constants and broad ownership groups agree with accepted7680+471=8151/preflight8192, but producer source-work-ledger rows mostly bind whole functions and broad statements instead of every named <=16-operation block/copy/move. Group6 claimed637/640 is structurally consistent yet administrative/loop/helper details are not independently reconciled. This is an unresolved proof, not a demonstrated cap overrun.'),
        'P24': ('reservation-order-source-supported-work-bounds-pending', 'Macro old T42/F42 then new F256/S512 precede new owners; actual context/profile/header and old S534/F47/G112/newG128 precede Candidate. Guard refusal latch prevents repeat. Exact work coverage of early errors, helpers, complete aggregate/Result movement and old/new finalizers under each unchanged cap still needs a fine ledger; no spare credits are accepted.'),
        'P25': ('algorithm-count-source-proved-work-unit-detail-pending', 'Pass widths1/2/4/8/16/32 produce six times64 transfers=384; per pair lengths2w require <=2w-1 comparisons, summing32+48+56+60+62+63=321. Six swaps leave result in512. IndexMAX avoids treating timestampMAX as absent and stable left preference preserves slot ties. Exact four ld/helper/scalar mapping into each eight comparison groups is part of unresolved P23, not measured by this review.'),
        'P26': ('source-equation-proved-scoped-execution', 'Every successful8151 charge increments NC before reading fields and increases inherited debit425; failed preflight does neither. projection D=512*setup+256*finish+7680*records is independent of calls/framed/latch. No refund path. Old setup534/finish47 remain independently admitted. Actual File basics agree; exact budget-edge private injection is unrun.'),
        'P27': ('source-supported-limit-controls-unrun', 'Semantic terminal skips only semantic while ordinary envelope/framing continue with charges; poison16 skips both leaves. Replay preflight<8192 stops all record processing and uses inherited bounded drain/footer/EOF. No broad target retry/fallback exists. Full private preflight/debit exhaustion controls are unrun.'),
        'P28': ('not-closed-complete-place-ledger-required', 'Production macro expands in public entry; cfg(test) cache_core introduces no production forwarding Result. Observation z/return, public cache_state, aggregate source/payload, public Result and external caller are visible. Producer owner intervals cite wrong birth ranges for Progress/Paid (walk/inputs rather than macro1306/1293), and broad helper/Option buckets lack exact source/received/drop/peak mapping. This does not establish a numeric overrun, but full lexical union is not proved.'),
        'P29': ('not-closed-dependent-on-P28', 'Declared arithmetic24656+1280+256+2896+256=29344 is correct and no new unbounded arena/heap owner appears. Actual unchanged arena8388608 and sole Candidate2048 remain. Role union cannot be accepted until complete owner/control/Option/Result map P28 reconciles within each fixed role without using global margin.'),
        'P30': ('public-layouts-measured-private-helper-layouts-unrun', 'Bound Rust1.99.0 public driver measures104/128/232/256/488 and complete Result488<=512 across39 cases. This lane has not compiled new private helper layout instrumentation for Progress/Paid/Reply/Loan/Options; producer layout claims remain uncredited. Layout values alone never establish moves/physical stack/RSS.'),
        'P31': ('source-supported-scoped-execution', 'All four new observation and aggregate authority getters are literalfalse; fields private/non-Copy/non-Clone, no raw serializer. Projection reserves words26..31 zero and no reason15/17 is selected by why. Existing write_report receives framing only. Counts describe fixture state only, with no real source/custody/crypto/applicability or release authority.'),
        'P32': ('scoped-public-and-private-executed-full-matrix-unrun', 'Unchanged sealed runner executed39 basics through four ordinary distinct quiescent Files, all full32/report/input integrity assertions pass. Separately admitted binary overlay executes7 private cases per mode:3 pass/4 fail each. All public words/transitions/sequences and other private matrices remain unrun and receive zero credit.'),
        'P33': ('API-compile-supported-old-runtime-regressions-unrun', 'One positive14negative attributed API probes behave as expected on actual candidate. Exact old source prefixes imply unchanged old implementation bytes and layouts; this independent lane did not execute either old86-member regression suite. Producer114-method/mode claims are metadata only, not independent passes; preliminaryfolders zero credit.'),
        'P34': ('review-boundary-observed', 'This initial candidate is rejected for two confirmed guards; no implementation or GA acceptance. Public/private/source evidence remains separate. Original bytes and all sealed preaccess/preparation files remain immutable; no evolving correction source read. No native/UI/capture/phone/device/production action.'),
        'P35': ('source-order-recorded-overlap-matrix-unrun', 'Actual order: field/profile/coordinate and envelope first; semantic config/header/Failure; resident invariant/checked sum/requested duplicate; token invariant/free/nonce duplicate; counts/body join; event guards. Lookup nonce before free pin before resident; publication nonce/free/slot then bytes/pins; release token join before resident/postcount. Single-defect named expectations and overlap allowed sets remain sealed unchanged; no new precedence invented, and full runtime overlap/nonmutation controls remain unrun.')}
    original = json.loads((PRE / 'proof-obligations.json').read_bytes())
    records = []
    for p in original['obligations']:
        status, explanation = observations[p['id']]
        records.append({'id': p['id'], 'name': p['name'], 'disposition': status,
                        'review': explanation, 'full_implementation_acceptance': False})
    assert len(records) == 35
    write('source-proof-review.json', {'schema': 1, 'source_sha256': HASH,
          'scope': 'Independent review of original frozen candidate; no evolving correction source access',
          'dispositions': records, 'implementation_accepted': False,
          'confirmed_defects': ['F01-Q10-inactive-mask-read', 'F02-Q9-pending-feasibility'],
          'work_and_lifetime_bounds_accepted': False, 'unrun_matrix_credit': 0,
          'proof_basis': 'manual source read plus exact hash/excerpt consistency; no producer model/harness execution'})
    print(json.dumps({'snapshot_members': len(manifest['members']), 'historical_sources': len(source_identities), 'verified_seams': len(seams), 'obligations_reviewed': len(records), 'candidate_executions_by_this_control': 0}))


if __name__ == '__main__':
    main()
