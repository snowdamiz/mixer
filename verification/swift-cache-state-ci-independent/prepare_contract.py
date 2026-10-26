#!/usr/bin/env python3
"""Derive a closed independent API contract from accepted, exact probe bytes."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).absolute().parent
ROOT = HERE.parent.parent
PRODUCER = ROOT / 'verification/swift-cache-state-scalar-cursor-implementation'
INDEPENDENT = ROOT / 'verification/swift-cache-state-scalar-cursor-implementation-independent'
SEAL_SHA = 'efc43d467a112522b40b4113bb21aa13086c0669d9d911707a85a148e3d4037c'
INDEPENDENT_SEAL_SHA = '267905beda1bd6abdb4a83bbfe174c87258a5d432603306946ca88c047ba3f86'
SOURCE_SHA = 'f98f7801925bc280e0e2a9c08ec2b4841b7ffc2942d2fedf6c4d3b4c1796bf1b'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def accepted(base, seal_sha, relative):
    raw = (base / 'seal.json').read_bytes()
    assert sha(raw) == seal_sha
    matches = [r for r in json.loads(raw)['members'] if r['path'] == relative]
    assert len(matches) == 1
    data = (base / relative).read_bytes()
    assert len(data) == matches[0]['bytes'] and sha(data) == matches[0]['sha256']
    return data, matches[0]

def span(data, token):
    encoded = token.encode()
    assert data.count(encoded) == 1, (token, data)
    start = data.index(encoded)
    return {'byte_start': start, 'byte_end': start + len(encoded), 'text': token}

# These are obligations derived from the intended Rust source failure, before
# fresh compilation. In particular, each mismatched four-File call is one E0308
# on the callee, while its argument labels are secondary spans only.
TARGETS = {
    'raw_record': ('E0422', ['cannot find', 'FixtureDecodedRecordV1', 'in this scope'], ['FixtureDecodedRecordV1']),
    'loan': ('E0422', ['cannot find', 'Loan', 'in this scope'], ['Loan']),
    'candidate': ('E0425', ['cannot find type', 'Candidate2048', 'in this scope'], ['Candidate2048']),
    'receipt': ('E0422', ['cannot find', 'Paid', 'in this scope'], ['Paid']),
    'authority_boolean': ('E0308', ['arguments to this function are incorrect'], ['analyze_fixture_cache_state_v1']),
    'fd_adoption': ('E0308', ['arguments to this function are incorrect'], ['analyze_fixture_cache_state_v1']),
    'state_seed': ('E0599', ['no associated function or constant named', 'from_state', 'FixtureCacheStateOutcomeV1'], ['from_state']),
    'aggregate_fields': ('E0616', ['field', 'cache_state', 'FixtureCacheStateOutcomeV1', 'private'], ['cache_state']),
    'observation_fields': ('E0616', ['field', 'extent', 'FixtureCacheStateObservationV1', 'private'], ['extent']),
    'copy_aggregate': ('E0277', ['trait bound', 'Copy', 'FixtureCacheStateOutcomeV1', 'not satisfied'], ['FixtureCacheStateOutcomeV1']),
    'clone_aggregate': ('E0277', ['trait bound', 'Clone', 'FixtureCacheStateOutcomeV1', 'not satisfied'], ['FixtureCacheStateOutcomeV1']),
    'copy_observation': ('E0277', ['trait bound', 'Copy', 'FixtureCacheStateObservationV1', 'not satisfied'], ['FixtureCacheStateObservationV1']),
    'clone_observation': ('E0277', ['trait bound', 'Clone', 'FixtureCacheStateObservationV1', 'not satisfied'], ['FixtureCacheStateObservationV1']),
    'old_cache_activation': ('E0599', ['no method named', 'cache_state', 'FixtureEnvelopeOutcomeV1'], ['cache_state']),
    'public_words': ('E0599', ['no method named', 'words', 'FixtureCacheStateObservationV1'], ['words']),
    'inherited/private-field': ('E0616', ['envelope_debit', 'FixtureEnvelopeObservationV1', 'private'], ['envelope_debit']),
    'inherited/no-clone': ('E0277', ['trait bound', 'Clone', 'FixtureEnvelopeObservationV1', 'not satisfied'], ['FixtureEnvelopeObservationV1']),
    'inherited/no-copy': ('E0277', ['trait bound', 'Copy', 'FixtureEnvelopeOutcomeV1', 'not satisfied'], ['FixtureEnvelopeOutcomeV1']),
    'inherited/no-record-constructor': ('E0432', ['unresolved import', 'FixtureDecodedRecordV1'], ['mixer_absence::FixtureDecodedRecordV1']),
    'inherited/no-word-or-boolean-entry': ('E0061', ['takes 4 arguments', '2 arguments were supplied'], ['analyze_fixture_envelope_v1']),
    'inherited/no-private-reply': ('E0432', ['unresolved import', 'FixtureEnvelopeReplyV1'], ['mixer_absence::FixtureEnvelopeReplyV1']),
    'inherited/no-observation-constructor': ('E0451', ['FixtureEnvelopeObservationV1', 'private'], [
        'boundary', 'reason', 'observed_records', 'state', 'phase', 'mask',
        'last_operation', 'active_operation', 'requested_function', 'pin_failure',
        'terminal_failure', 'last_work', 'last_instructions', 'envelope_debit',
        'full_replay_accepted', 'stored_prefix_validated']),
    'inherited/no-raw-serializer': ('E0599', ['no method named', 'to_bytes', 'FixtureEnvelopeObservationV1'], ['to_bytes']),
}

def main():
    rows = []
    for source in sorted((PRODUCER / 'api').rglob('*.rs')):
        relative = source.relative_to(PRODUCER).as_posix()
        data, inherited = accepted(PRODUCER, SEAL_SHA, relative)
        name = relative.removeprefix('api/').removesuffix('.rs')
        row = {'name': name, 'source': relative, 'bytes': len(data), 'sha256': sha(data),
               'crate_alias': 'mixer_absence' if name.startswith('inherited/') else 'cache_fixture',
               'expected_success': name in ('positive', 'inherited/positive')}
        if not row['expected_success']:
            code, messages, texts = TARGETS[name]
            row.update(code=code, message_contains=messages, primary_spans=[span(data, text) for text in texts])
        rows.append(row)
    assert len(rows) == 25 and sum(not r['expected_success'] for r in rows) == len(TARGETS) == 23
    assert sum(len(r.get('primary_spans', [])) for r in rows) == 38
    selected = []
    for name in ('analyzer.rs', 'envelope.rs', 'cache_state.rs'):
        data, row = accepted(PRODUCER, SEAL_SHA, 'source/library/' + name)
        if name == 'cache_state.rs':
            assert sha(data) == SOURCE_SHA
        selected.append(row)
    _, private = accepted(PRODUCER, SEAL_SHA, 'controls/selected_controls.rs')
    _, control = accepted(INDEPENDENT, INDEPENDENT_SEAL_SHA, 'source/scalar_cursor_independent.rs')
    result = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
              'argv': sys.argv, 'python': sys.version,
              'basis': 'Exact accepted frozen source; candidate files not read',
              'producer_seal_sha256': SEAL_SHA, 'independent_seal_sha256': INDEPENDENT_SEAL_SHA,
              'source_sha256': SOURCE_SHA, 'selected_library': selected,
              'private_append_sources': [private, control],
              'API_dispositions_per_mode': 25, 'API_negative_per_mode': 23,
              'API_positive_per_mode': 2, 'primary_target_spans_per_mode': 38, 'probes': rows,
              'source_only_static_contract': True,
              'fresh_compiler_validation_pending': True}
    (HERE / 'independent-api-contract.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print('25 dispositions; 23 negative; 38 independently selected primary spans')

if __name__ == '__main__':
    main()
