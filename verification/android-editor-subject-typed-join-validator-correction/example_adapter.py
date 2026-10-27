#!/usr/bin/env python3
"""Bounded read-only adapter for the released one-overload raw/compact examples.

This does not replay or execute the corpus. Native-hook states are separate from
pre-public-call cases, and no supplier/helper body result is inferred.
"""
import gzip
import hashlib
import json
from pathlib import Path
from typed_join import SCHEMA, POLICY_SHA256, STATES, Refusal, require, load_policy, validate_rows

HERE = Path(__file__).resolve().parent
PACKET = HERE.parent / 'android-editor-membership-compiled-boundary-qualification/delegated-overload-association'
SEAL = '68916bf61a5204f022c7e0e6190dd698f621924b25389c3ffcd4989fbbed3104'
PUBLIC_ID = 'dev/mixer/android/NativeEditorConnectionV2$Api33#setComposingRegion(IILandroid/view/inputmethod/TextAttribute;)Z'
SUPPLIER_ID = 'dev/mixer/android/NativeEditorConnectionV2$Api33#lambda$setComposingRegion$4(IILandroid/view/inputmethod/TextAttribute;)Ljava/lang/Boolean;'
DESC = '(IILandroid/view/inputmethod/TextAttribute;)Z'
FILES = ('producer-run/direct-setComposingRegionWithAttributes.rows.jsonl.gz', 'producer-run/direct-setComposingRegionWithAttributes.rows.jsonl.gz.compact.jsonl', 'standalone-replay/attribute-states.rows.jsonl.gz', 'standalone-replay/attribute-states.rows.jsonl.gz.compact.jsonl')

def read_rows(relative):
    require(relative in FILES, 'unreleased-example-path')
    require(hashlib.sha256((PACKET/'seal.json').read_bytes()).hexdigest() == SEAL, 'example-seal-drift')
    manifest = json.loads((PACKET/'seal.json').read_text())
    member = next(x for x in manifest['members'] if x['path'] == relative)
    path = PACKET/relative
    require(path.stat().st_size == member['bytes'] and hashlib.sha256(path.read_bytes()).hexdigest() == member['sha256'], 'example-member-drift')
    stream = gzip.open(path, 'rt') if relative.endswith('.gz') else path.open()
    with stream: rows = [json.loads(line) for line in stream]
    require(len(rows) == 13 and len({r['state'] for r in rows}) == 13, 'example-state-roster')
    return rows, member['sha256']

def value(v, source_row):
    if v['kind'] == 'boolean':
        require(set(v) == {'kind', 'value'} and type(v['value']) is bool, 'example-boolean-type')
        return dict(v)
    if v['kind'] == 'exception':
        require(set(v) == {'kind', 'identity', 'class'}, 'example-exception-fields')
        identity = v['identity']
        fatal = source_row['post_operation_authority']['editor']['firstFatal'] == identity
        return dict(v, **{'class': v['class'].replace('.', '/'), 'fatal': fatal})
    raise Refusal('example-value-unsupported-no-snapshot-invented')

def document(relative, policy=None):
    policy = policy or load_policy()
    rows, receipt_hash = read_rows(relative)
    public = next(s for s in policy['subjects'] if s['id'] == PUBLIC_ID)
    supplier = next(s for s in policy['subjects'] if s['id'] == SUPPLIER_ID)
    native_tuple = next(i for i in supplier['exact_invocations'] if i['callee']['owner'] == 'android/view/inputmethod/InputConnection')
    public_tuple = next(i for i in public['exact_invocations'] if i['callee']['name'] == 'call')
    normalized, skipped = [], []
    for source_row in rows:
        require(source_row['family'] == 'setComposingRegionWithAttributes', 'example-family-drift')
        original_state = source_row['state']
        state = 'clean' if original_state == 'current' else original_state
        case = '$state'
        if original_state in ('terminal', 'dirty', 'stale', 'changing'):
            case = original_state+'-before-entry-refuses'
            state = {'terminal': 'terminal-at-entry', 'dirty': 'dirty-at-entry'}.get(original_state, 'clean')
            require(source_row['native_target_entries'] == 0, 'pre-public-case-must-have-zero-selected-native-entries')
        elif state not in STATES:
            skipped.append({'source_state': original_state, 'disposition': 'pending-no-alias-to-canonical-state'})
            continue
        public_value = value(source_row['actual_operation_outcome'], source_row)
        observed = {'subject_outcome': public_value, 'public_outcome': public_value}
        selected = source_row['selected_event']
        completions = source_row.get('selected_actual_native_completions', source_row.get('actual_native_outcomes', []))
        matches = [c for c in completions if c['method'] == 'BaseInputConnection.setComposingRegion' and c['descriptor'] == DESC and c['completion'] == 'return']
        require(len(matches) <= 1, 'ambiguous-outer-attribute-completion')
        if matches:
            completion = matches[0]
            require(completion['native_outcome_association'] == 'selected-original-delegated-overload-return', 'outer-overload-source-delegation-proof-missing')
            require(completion['receiver_identity'] == source_row['original_target'], 'outer-completion-original-receiver-mismatch')
            frames = completion['production_frames']
            require(any(f['class'].replace('.', '/') == supplier['class'] and f['method'] == supplier['method'] and f['descriptor'] == supplier['descriptor'] and f['bci'] == native_tuple['bci'] for f in frames), 'outer-exact-supplier-frame-missing')
            observed['native_outcome'] = value(completion['value'], source_row)
            observed['native_invocation'] = native_tuple
        event_id = original_state+':'+str(selected[0]['sequence_index'] if selected else 'public-entry')
        evidence = {'kind': 'method-exit', 'environment': 'host-jvm', 'receipt_sha256': receipt_hash, 'event_id': event_id}
        normalized.append({'subject_id': PUBLIC_ID, 'case_id': case, 'state_id': state, 'invocation': public_tuple, 'association': 'direct-body', 'observations': observed, 'evidence': evidence})
        if selected:
            # The supplier appears in an active frame. Its own return is absent.
            # Keep native/public observations as association data only.
            association_obs = {k: v for k,v in observed.items() if k != 'subject_outcome'}
            normalized.append({'subject_id': SUPPLIER_ID, 'case_id': '$state', 'state_id': state, 'invocation': native_tuple, 'association': 'ancestor-presence', 'observations': association_obs, 'evidence': dict(evidence, kind='ancestor-frame')})
    doc = {'schema': SCHEMA, 'encoding': 'raw', 'policy_sha256': POLICY_SHA256,
        'context': {'product_context': policy['context_id'], 'source_map_sha256': policy['source_map_sha256'], 'class_map_sha256': policy['class_map_sha256'], 'execution_closure_sha256': None}, 'rows': normalized}
    return doc, skipped

def run():
    reports = {}
    for relative in FILES:
        doc, skipped = document(relative)
        result = validate_rows(load_policy(), doc)
        reports[relative] = {'rows': result['rows'], 'typed_consistent_count': result['typed_consistent_count'], 'skipped_without_alias': skipped, 'qualified': False}
    for prefix in ('producer-run/direct-setComposingRegionWithAttributes', 'standalone-replay/attribute-states'):
        require(reports[prefix+'.rows.jsonl.gz'] == reports[prefix+'.rows.jsonl.gz.compact.jsonl'], 'raw-compact-semantic-result-mismatch')
    return {'schema': 1, 'input_seal_sha256': SEAL, 'reports': reports, 'raw_compact_equivalent': True, 'scope': 'one exact public attribute adapter plus pending supplier associations; no runtime replay', 'qualified': False}

if __name__ == '__main__': print(json.dumps(run(), indent=2))
