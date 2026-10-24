#!/usr/bin/env python3
"""Freeze the source-audited callsite inventory and pending repair requirements."""
import hashlib
import json
from pathlib import Path
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sha = lambda body: hashlib.sha256(body).hexdigest()
enc = lambda value: (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()

def main():
    assert not (HERE / 'seal.json').exists(), 'do not rewrite a sealed packet'
    with tarfile.open(HERE / 'baseline-source.tar.gz') as archive:
        sources = {entry.name: archive.extractfile(entry).read().decode() for entry in archive.getmembers()}
    entries = [
        ('value_operations.rs', 566, 'primitive_pop', 'contextual-active', 'operation.cursor', 'Values', 'After actual pop; preserve existing debt behavior in original caller.'),
        ('value_operations.rs', 631, 'primitive_numeric', 'contextual-active', 'operation.cursor', 'Values', 'After shared arithmetic result; original reconciliation precedes result mapping.'),
        ('value_operations.rs', 649, 'primitive_clear', 'preserve-cleanup', None, 'Values', 'Completion clear; stored operation cursor can be stale.'),
        ('control_operations.rs', 259, 'control_remove', 'contextual-active', 'self.phase.operation.cursor', 'Values or Controls', 'Active shared-control pop/truncate leaf; retain debt latch.'),
        ('frame_operations.rs', 671, 'remove_live', 'preserve-cleanup-split-active-finish', None, 'Values or Controls or Frames', 'Shared rollback/drain/finish adapter: no blanket cursor propagation.'),
        ('cache.rs', 1235, 'CacheControl::remove_live', 'preserve-cleanup-defer-cache-seam', None, 'ActivePins or CacheEntries', 'Shared release/abandon/build-rollback/eviction; cache cursor is not current invocation proof.'),
        ('cache.rs', 1449, 'SwiftFunctionCache::cleanup pin inventory', 'preserve-cleanup', None, 'ActivePins', 'Actual owner cleanup.'),
        ('cache.rs', 1470, 'SwiftFunctionCache::cleanup resident inventory', 'preserve-cleanup', None, 'CacheEntries', 'Actual owner cleanup.'),
        ('execution.rs', 1700, 'SwiftReactorInstance::cleanup_owned', 'preserve-cleanup', None, 'MemoryPages', 'Consuming State memory cleanup.'),
        ('execution.rs', 1811, 'PartialInstance::cleanup_failed', 'preserve-cleanup', None, 'MemoryPages', 'Partial-construction cleanup.'),
        ('memory_growth_operations.rs', 115, 'SwiftGrowthExecution::release_pending', 'preserve-cleanup', None, 'MemoryPages', 'Uncommitted pending-memory cleanup reused by explicit cleanup; cursor can be stale.'),
        ('control.rs', 1602, 'RuntimeControl::remove_live', 'preserve-cleanup', None, 'caller supplied Live', 'Existing no-WASI convenience wrapper.'),
    ]
    rows = []
    for name, line, owner, decision, cursor, resource, rationale in entries:
        path = 'src/experimental_swift_reactor/' + name
        text = sources[path].splitlines()
        assert 'remove_live_with_wasi(' in text[line - 1], (path, line)
        rows.append({'source': path, 'line': line, 'sourceSHA256': sha(sources[path].encode()),
            'enclosing': owner, 'decision': decision, 'actualCursor': cursor,
            'actualResource': resource, 'rationale': rationale,
            'excerptFirstLine': max(1, line - 2), 'excerpt': text[max(0, line - 3):line + 5]})
    observed = []
    for path, text in sources.items():
        if not path.startswith('src/') or not path.endswith('.rs') or path.endswith('tests.rs'):
            continue
        for line, value in enumerate(text.splitlines(), 1):
            if 'remove_live_with_wasi(' in value and 'fn remove_live_with_wasi(' not in value:
                observed.append((path, line))
    assert sorted(observed) == sorted((row['source'], row['line']) for row in rows)
    inventory = {'schema': 1, 'baselineSourceSHA256': 'a0bbe77aca3021e48f1fb76dc97cfbc0406c24e5ba7eacdd33d5dabe8f998d9b',
        'productionCallsites': rows, 'productionCallsiteCount': len(rows),
        'frameAdapterCallers': {'activeFinishNewContextualHelper': [811, 813, 832],
            'rollbackOldHelper': [714, 727, 737], 'drainOldHelper': [923, 926, 941]},
        'relatedCleanupFaults': {'end_construction_phase_with_wasi': [1125, 1132, 1140, 1154],
            'refund_with_wasi': [1320, 1334]},
        'authorization': 'audit only; source inventory is not release authorization'}
    (HERE / 'callsite-inventory.json').write_bytes(enc(inventory))
    groups = [
        ('CDR01', 'Actual retained-pin Load post-pop underflow', 'Invocation stage, exact function/selected absolute offset, Values, amount1/current0, actual nonzero WASI; original prefix and debt.'),
        ('CDR02', 'Actual retained-pin Store post-pop underflows', 'Fault each original pop independently; preserve value/address removal order, memory bytes and contextual source.'),
        ('CDR03', 'Actual pinned control post-pop and truncation underflows', 'If/BrIf/BrTable/shared-close pops plus Values/Controls truncation; correct current decoded offset and original effect prefixes.'),
        ('CDR04', 'Actual pinned bulk memory and MemoryGrow pop faults', 'Original shared pop yields contextual diagnostic without wrapper rewriting; no erroneous memory effect, refund or pin loss.'),
        ('CDR05', 'Original numeric after-effect reconciliation', 'Actual numeric source and removed count; preserve arithmetic Result/removal precedence and typed operands.'),
        ('CDR06', 'All three active finish removals and result pop', 'Values/Controls/Frames each use explicit active helper; current completing instruction cursor, exact retained pin behavior and debt.'),
        ('CDR07', 'All six exact contextual Live mappings', 'Each actual resource maps from live_parts; attempted is requested removal/current is removable availability; count unchanged on underflow; no fake capacity.'),
        ('CDR08', 'Successful contextual and old removals', 'Independently compare the tiny duplicated successful subtraction for all six resources including zero amount, exact subtraction and original peaks; legacy body byte-identical; no additional check/work/fuel/allocation or cursor storage.'),
        ('CDR09', 'Earlier first failure wins', 'Distinct earlier stage/kind/code/resource/function/offset/WASI/at_failure unchanged through contextual and old removal; only independent cleanup latch and later observation may change.'),
        ('CDR10', 'Cursorless cleanup and stale stored cursor', 'Completion clear, failed-entry rollback, drain, explicit cleanup retry, pending-growth release, constructor/refund/cache cleanup keep old None fields/zero attempted+limit; stale operation cursor never leaks.'),
        ('CDR11', 'Cleanup lifecycle and original authority', 'After-failure cancellation/deadline, repeated drain, original rejected pins/tickets, explicit cleanup reacquisition, fixed completion and consuming cleanup barriers preserve every diagnostic/at_failure field; after_cleanup actual only.'),
        ('CDR12', 'Caller boundary and malformed conditions', 'Retained pin proves source before effects; invalid floors/unsupported operation/fuel/work/cancel do not acquire a guessed source or change existing effect/PC prefixes.'),
        ('CDR13', 'Allocation refusal and unit-hook controls', 'Warm successful and failed paths under first-allocation refusal; disabled hooks preserve ordinary behavior; actual selector/accounting bound.'),
        ('CDR14', 'Final accounting and exact admission/restoration', 'Final source canonical MIR/aliases/literals/promoted constants all positively counted; relevant changed header/frame/nested envelopes at bound and one below; old cleanup/foundation source+MIR unchanged; dropped-phase debt conservative.'),
        ('CDR15', 'Frozen compiler and runtime identity', '39 expanded methods byte identical, 2912-byte reservation unchanged, actual Frozen parity; Swift first-failure semantics never copied from Frozen terminal rewrite.'),
        ('CDR16', 'Checks and metadata', 'Fresh Swift/all Debug/Release production/unit owner and every containing inventory size/alignment/offset; all library feature checks, formatting/scoped Clippy, original diagnostic comparison if broad Clippy run.'),
    ]
    matrix = {'schema': 1, 'status': 'pending-no-implementation-candidate', 'implementationAuthorized': False,
        'configurations': [{'features': features, 'profile': profile} for features in ['experimental-swift-reactor', 'all'] for profile in ['debug', 'release']],
        'runtime': 'serial unit tests, original strict-ABI owner fixtures; fresh target per source/features/profile/context',
        'requiredProducerGroups': [{'id': group, 'name': name, 'requiredBehavior': requirement, 'status': 'pending'} for group, name, requirement in groups],
        'requiredIndependentReview': ['Reconstruct source overlay from accepted baseline; own fresh targets and exact binary/test-list/hash binding.',
            'Different actual-pinned body/offset and nested frame; no copied interpreter or diagnostic postprocessing.',
            'Audit every contextual and cursorless callsite against source and original ownership.',
            'Assert every original diagnostic/at_failure field across cleanup, allowing only after_cleanup observation.',
            'Independent final canonical-MIR positive roles and complete owner/inventory metadata/formulas replay.',
            'Root source/receipt review before live integration; G08 stays open for actual original Swift mapping and remaining routes.'],
        'rootSelectedNarrowing': 'Preserve existing remove_live_with_wasi body exactly. Add contextual entry alongside it with the same original live_parts/checked_sub/live_mut primitives. No common-body refactor; independently compare six-resource success behavior and charge all new contextual objects positively.',
        'publicApiChanges': [], 'ownerFieldsAdded': [], 'dependenciesAdded': [],
        'nativeRequiredForThisHostSlice': False, 'physicalPhonesDeferred': True,
        'g08Accepted': False, 'fullSwiftAccepted': False, 'releaseAccepted': False, 'gaAccepted': False}
    (HERE / 'repair-acceptance-matrix.json').write_bytes(enc(matrix))
    files = {str(path.relative_to(HERE)): sha(path.read_bytes()) for path in sorted(HERE.rglob('*')) if path.is_file() and path != HERE / 'seal.json'}
    seal = {'schema': 1, 'files': files, 'externalFiles': {'docs/swift-cleanup-diagnostic-contract.md': sha((ROOT / 'docs/swift-cleanup-diagnostic-contract.md').read_bytes())},
        'selfExclusion': 'Only verification/swift-cleanup-diagnostic-contract/seal.json; no nested file is excluded.'}
    (HERE / 'seal.json').write_bytes(enc(seal))
    print(json.dumps({'sealedFiles': len(files), 'productionCallsites': len(rows), 'pendingRepairGroups': len(groups)}, sort_keys=True))

if __name__ == '__main__':
    main()
