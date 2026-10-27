#!/usr/bin/env python3
"""Frozen-source custody plus finite abstract countermodels; no product execution."""
from pathlib import Path
import hashlib
import json
import platform
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
DESC = ROOT / 'verification/swift-guarded-snapshot-descriptor-rebinding'
FUND = ROOT / 'verification/swift-guarded-snapshot-funding-implementation/source/vm'
manifest = json.loads((DESC / 'source-manifest.json').read_text())
assert manifest['tree_sha256'] == '450b6d9b3a05d160e19fa888b68173286b8f6af20ecc7216fdf86283f09b308a'
members = {x['path']: x for x in manifest['members']}
paths = [
    'src/experimental/swift.rs', 'src/experimental/account.rs',
    'src/experimental/reader.rs', 'src/experimental/metadata.rs',
    'src/experimental/validate.rs', 'src/experimental/policy.rs',
    'src/experimental_wasi/descriptor.rs', 'src/validate.rs',
    'src/float.rs', 'src/lib.rs',
    'src/experimental_swift_reactor/retained_profile_loader_v1.rs',
]
observed = []
for relative in paths:
    overlay = DESC / 'overlay/vm' / relative
    path = overlay if overlay.is_file() else FUND / relative
    data = path.read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    expected = members[relative]
    assert sha == expected['sha256'], relative
    assert len(data) == expected['bytes'], relative
    observed.append({'path': str(path.relative_to(ROOT)), 'bytes': len(data), 'sha256': sha})

# Model a successful positive debit as a removed edge. Every remaining path
# segment has at most K source actions. This finite enumeration tests only the
# counting lemma; it does not establish K or infer source semantics from text.
cases = []
for budget in range(9):
    for spent in range(budget + 1):
        for segment_cost in range(1, 8):
            actual = segment_cost * (spent + 1)
            bound = segment_cost * (budget + 1)
            assert actual <= bound
            cases.append((budget, spent, segment_cost))

# Countermodels: a zero debit cannot cut a repeat; counting a callback occurrence
# once cannot cover the resolver's 34 calls; fixed outer loops remain work when
# their credited inner iteration sets are empty.
countermodels = {
    'take_zero_is_not_positive_credit': {'repeats': 4, 'credits': 0, 'observed_actions': 4, 'candidate_B_only': 0},
    'find_callback_multiplicity': {'callback_occurrences': 1, 'maximum_callbacks': 34, 'undercount_if_once': 33},
    'segments_outer_empty_inner': {'fixed_outer_iterations': 2, 'successful_inner_debits': 0, 'outer_actions_still_positive': True},
    'loader_interrupted_attempts': {'attempts': 32, 'validator_credits': 0},
    'environment_terminator_observation': {'range_start': 0, 'range_end_inclusive': 64, 'pointer_observations': 65},
    'environment_sort': {'maximum_entries': 64, 'maximum_comparisons': sum(range(64)), 'positive_validator_debits': 0},
}
assert countermodels['environment_sort']['maximum_comparisons'] == 2016
receipt = {
    'schema': 1,
    'generated_at': datetime.now(timezone.utc).isoformat(),
    'scope': 'independent frozen-source preaccess audit and abstract finite models only',
    'command': 'python3 verification/swift-guarded-snapshot-loader-work-independent/preaccess/audit.py',
    'python': sys.version,
    'platform': platform.platform(),
    'accepted_descriptor_source_tree': manifest['tree_sha256'],
    'source_members_verified': observed,
    'abstract_positive_credit_partition_cases': len(cases),
    'countermodels': countermodels,
    'product_execution': False,
    'compiler_execution': False,
    'active_producer_read': False,
    'native_runtime': 'paused and not run',
    'captures_or_ui': 'paused and not used',
    'new_owned_runtime_processes': 0,
    'cleanup': 'No simulator, emulator, capture, loader, VM, guest, cache, scope, constructor, or writer process started.',
    'decision': 'preaccess source audit only; producer bridge and operation coefficient remain unreviewed',
}
(OUT / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'source_members_verified': len(observed), 'abstract_model_cases': len(cases), 'decision': receipt['decision']}))
