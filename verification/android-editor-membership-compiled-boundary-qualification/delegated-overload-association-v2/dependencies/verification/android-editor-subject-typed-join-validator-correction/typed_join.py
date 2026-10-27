#!/usr/bin/env python3
"""Strict editor outcome joins. Consistency is never runtime qualification."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

POLICY_SHA256 = 'ada20df1315a40d0376f04f8fbb9a5d6985e9ce7f83c456e980eb7b197c184e5'
SCHEMA = 'mixer-editor-typed-rows-v1'
ROW_FIELDS = ('subject_id', 'case_id', 'state_id', 'invocation', 'association', 'observations', 'evidence')
STATES = ('clean', 'terminal-at-entry', 'terminal-before-return', 'dirty-at-entry', 'dirty-before-return', 'ordinary-throw-after-callback', 'fatal-throw-after-callback')

class Refusal(ValueError):
    pass

def require(condition, code):
    if not condition: raise Refusal(code)

def digest(value):
    return hashlib.sha256(value).hexdigest()

def load_policy(path=None):
    path = Path(path) if path else Path(__file__).with_name('policy.json')
    raw = path.read_bytes()
    require(digest(raw) == POLICY_SHA256, 'policy-digest-mismatch')
    return json.loads(raw)

def keys(value, expected, code):
    require(isinstance(value, dict) and set(value) == set(expected), code)

def strict_equal(actual, expected):
    """Structural equality preserving JSON/Python scalar types at every depth."""
    if type(actual) is not type(expected): return False
    if type(expected) is dict:
        return set(actual) == set(expected) and all(type(k) is str and strict_equal(actual[k], expected[k]) for k in expected)
    if type(expected) is list:
        return len(actual) == len(expected) and all(strict_equal(a,b) for a,b in zip(actual,expected))
    return actual == expected

def invocation_equal(actual, expected):
    if type(actual) is not dict: return False
    if type(actual.get('bci')) is not int or type(actual.get('opcode')) is not int: return False
    if actual['bci'] < 0 or not 0 <= actual['opcode'] <= 255: return False
    return strict_equal(actual, expected)

def sha_value(value):
    return isinstance(value, str) and len(value) == 64 and all(x in '0123456789abcdef' for x in value)

def outcome(value):
    """Validate an actual typed union; bool must never pass as int in Python."""
    require(isinstance(value, dict) and isinstance(value.get('kind'), str), 'outcome-not-tagged')
    kind = value['kind']
    if kind == 'boolean':
        keys(value, ('kind', 'value'), 'boolean-outcome-fields')
        require(type(value['value']) is bool, 'boolean-outcome-type')
    elif kind == 'int':
        keys(value, ('kind', 'value'), 'int-outcome-fields')
        require(type(value['value']) is int and -(2**31) <= value['value'] < 2**31, 'int-outcome-type')
    elif kind in ('null', 'void'):
        keys(value, ('kind',), 'empty-outcome-fields')
    elif kind == 'reference':
        keys(value, ('kind', 'identity', 'snapshot'), 'reference-outcome-fields')
        require(isinstance(value['identity'], str) and bool(value['identity']), 'reference-identity-missing')
        require(isinstance(value['snapshot'], dict) and isinstance(value['snapshot'].get('type'), str) and isinstance(value['snapshot'].get('fields'), dict), 'reference-snapshot-missing')
        keys(value['snapshot'], ('type', 'fields'), 'reference-snapshot-fields')
    elif kind == 'exception':
        keys(value, ('kind', 'identity', 'class', 'fatal'), 'exception-outcome-fields')
        require(isinstance(value['identity'], str) and bool(value['identity']) and isinstance(value['class'], str) and bool(value['class']) and type(value['fatal']) is bool, 'exception-outcome-type')
    else: raise Refusal('outcome-kind-unsupported')
    return value

def normalize_rows(document):
    """Raw dictionaries and lossless column tuples share exactly one validator."""
    require(isinstance(document, dict), 'document-not-object')
    require(document.get('schema') == SCHEMA, 'document-schema')
    encoding = document.get('encoding')
    expected = {'schema', 'encoding', 'policy_sha256', 'context', 'rows'}
    if encoding == 'compact': expected.add('columns')
    require(set(document) == expected, 'document-fields')
    require(isinstance(document['rows'], list), 'rows-not-array')
    if encoding == 'raw': rows = document['rows']
    elif encoding == 'compact':
        columns = document['columns']
        require(isinstance(columns, list) and len(columns) == len(set(columns)) and set(columns) == set(ROW_FIELDS), 'compact-columns')
        rows = []
        for values in document['rows']:
            require(isinstance(values, list) and len(values) == len(columns), 'compact-row-width')
            rows.append(dict(zip(columns, values)))
    else: raise Refusal('row-encoding-unsupported')
    for row in rows: keys(row, ROW_FIELDS, 'row-fields')
    return copy.deepcopy(rows)

def check_result_type(value, expected):
    require(value['kind'] == expected or expected == 'reference' and value['kind'] == 'null', 'result-kind-mismatch')

def _check_observations(subject, row, rule):
    observed = row['observations']
    require(isinstance(observed, dict), 'observations-not-object')
    allowed = {'subject_outcome', 'native_outcome', 'public_outcome', 'native_invocation', 'guard', 'thread', 'original_exception', 'first_fatal', 'callback_result', 'executor_identity', 'consumer_identity'}
    require(set(observed) <= allowed, 'candidate-expectation-or-unknown-observation')
    for key in ('subject_outcome', 'native_outcome', 'public_outcome', 'original_exception', 'first_fatal'):
        if key in observed: outcome(observed[key])
    if row['association'] == 'ancestor-presence': return 'pending-ancestor-is-not-an-outcome'
    require(row['association'] == 'direct-body', 'association-unsupported')
    if rule.startswith('pending-'): return rule
    if 'subject_outcome' not in observed: return 'pending-actual-subject-outcome'
    actual = observed['subject_outcome']
    role = subject['role']
    if (role in ('pure-any-thread-null', 'main-thread-constant-false') or role == 'public-adapter' and rule in ('main-thread-refusal', 'entry-refusal', 'guard-refusal')) and 'public_outcome' in observed:
        require(strict_equal(actual, observed['public_outcome']), 'subject-public-result-mismatch')
    if rule == 'any-thread-null' or role == 'pure-any-thread-null':
        require(actual == {'kind': 'null'}, 'getHandler-must-return-null')
        require(not any(x in observed for x in ('native_outcome', 'native_invocation', 'guard')), 'getHandler-must-not-read-native-state')
        require(observed.get('thread') in ('main', 'background'), 'thread-observation-missing')
        return 'typed-consistent'
    if rule == 'main-thread-refusal':
        require(observed.get('thread') == 'background', 'wrong-thread-observation-missing')
        public = observed.get('public_outcome', actual)
        require(public['kind'] == 'exception' and public['class'] == 'java/lang/IllegalStateException' and not public['fatal'], 'wrong-thread-refusal-type')
        require('native_outcome' not in observed and 'native_invocation' not in observed, 'wrong-thread-native-call-forbidden')
        if role in ('inner-native-supplier', 'outer-native-value-supplier', 'proposal-guard-supplier', 'bounds-guard-supplier'):
            return 'pending-supplier-must-not-execute-on-entry-refusal'
        return 'typed-consistent'
    if rule == 'guard-refusal':
        require(subject['source_guard'] is not None or role == 'main-thread-constant-false', 'no-source-guard')
        if role != 'main-thread-constant-false':
            require(strict_equal(observed.get('guard'), {'expression': subject['source_guard'], 'accepted': False}), 'guard-observation-mismatch')
        require(strict_equal(actual, subject['refused_result']), 'guard-refused-result-mismatch')
        require('native_outcome' not in observed and 'native_invocation' not in observed, 'guard-must-short-circuit-native')
        return 'typed-consistent'
    if role == 'main-thread-constant-false':
        require(actual == {'kind': 'boolean', 'value': False}, 'unsupported-must-return-false')
        require('native_outcome' not in observed and 'native_invocation' not in observed and observed.get('thread') == 'main', 'unsupported-main-only-no-native')
        return 'typed-consistent'
    if role.startswith('unsupported-'):
        # Callback union intentionally awaits exact executor/body observations;
        # an ancestor or a void public return is insufficient.
        return 'pending-unsupported-callback-body-and-executor-outcome'
    if rule == 'entry-refusal':
        public = observed.get('public_outcome', actual)
        require(strict_equal(public, subject['refused_result']), 'entry-refused-result-mismatch')
        require('native_outcome' not in observed and 'native_invocation' not in observed, 'entry-refusal-native-call-forbidden')
        if role != 'public-adapter': return 'pending-supplier-must-not-execute-on-entry-refusal'
        return 'typed-consistent'
    native = observed.get('native_outcome')
    public = observed.get('public_outcome')
    if native is None or public is None: return 'pending-distinct-native-and-public-outcomes'
    if rule in ('exact-original-exception', 'exact-first-fatal'):
        origin_key = 'original_exception' if rule == 'exact-original-exception' else 'first_fatal'
        if origin_key not in observed: return 'pending-exact-exception-origin'
        origin = observed[origin_key]
        require(origin['kind'] == 'exception' and origin['fatal'] == (rule == 'exact-first-fatal'), 'exception-origin-type')
        require(strict_equal(native, origin) and strict_equal(public, origin) and strict_equal(actual, origin), 'exception-identity-not-preserved')
        return 'typed-consistent'
    check_result_type(native, subject['result_type'])
    if rule == 'postcheck-refused-public-result':
        require(strict_equal(public, subject['refused_result']), 'postcheck-public-refusal-mismatch')
    elif rule == 'exact-clean-result':
        require(strict_equal(public, native), 'native-public-clean-result-mismatch')
    else: return 'pending-unimplemented-case-oracle'
    if role == 'inner-native-supplier': require(strict_equal(actual, native), 'inner-supplier-result-mismatch')
    else: require(strict_equal(actual, public), 'subject-public-result-mismatch')
    return 'typed-consistent'

def validate_rows(policy, document):
    """No candidate field can upgrade pending closure or qualify a native gate."""
    # Recheck even callers passing a mutable in-memory policy object.
    require(strict_equal(policy, load_policy()), 'policy-object-mutation')
    require(document.get('policy_sha256') == POLICY_SHA256, 'row-policy-digest-mismatch')
    header = document.get('context')
    keys(header, ('product_context', 'source_map_sha256', 'class_map_sha256', 'execution_closure_sha256'), 'context-fields')
    require(header['product_context'] == policy['context_id'], 'product-context-mismatch')
    for name in ('source_map_sha256', 'class_map_sha256'): require(header[name] == policy[name], name+'-mismatch')
    require(header['execution_closure_sha256'] is None or sha_value(header['execution_closure_sha256']), 'execution-closure-hash-type')
    # A caller's hash is only an identity claim. There is no trusted released
    # execution-source closure in this policy, so even correct joins stay pending.
    rows = normalize_rows(document)
    subjects = {s['id']: s for s in policy['subjects']}
    seen = set()
    results = []
    for row in rows:
        require(row['subject_id'] in subjects, 'foreign-subject')
        subject = subjects[row['subject_id']]
        require(row['case_id'] in subject['required_semantic_cases'] or row['case_id'] == '$state', 'foreign-case')
        require(row['state_id'] in STATES, 'noncanonical-state')
        key = tuple(row[x] for x in ('subject_id', 'case_id', 'state_id'))
        require(key not in seen, 'duplicate-subject-case-state')
        seen.add(key)
        if row['case_id'] == '$state':
            constraint = next(x for x in subject['required_states'] if x['state_id'] == row['state_id'])
        else:
            constraint = next(x for x in subject['case_policies'] if x['case_id'] == row['case_id'])
            require(constraint['state_id'] == row['state_id'], 'case-state-mismatch')
        invocation = row['invocation']
        require(any(invocation_equal(invocation, expected) for expected in subject['exact_invocations']) if subject['exact_invocations'] else invocation is None, 'invocation-tuple-mismatch')
        obs = row['observations']
        if isinstance(obs, dict) and ('native_outcome' in obs or 'native_invocation' in obs):
            suppliers = [subjects[x] for x in subject['native_supplier_ids']]
            expected = [i for s in suppliers for i in s['exact_invocations'] if i['callee']['owner'] == 'android/view/inputmethod/InputConnection']
            if subject['role'] == 'inner-native-supplier': expected = [i for i in subject['exact_invocations'] if i['callee']['owner'] == 'android/view/inputmethod/InputConnection']
            require(any(invocation_equal(obs.get('native_invocation'), candidate) for candidate in expected), 'native-overload-tuple-mismatch')
        ev = row['evidence']
        keys(ev, ('kind', 'environment', 'receipt_sha256', 'event_id'), 'evidence-fields')
        require(ev['kind'] in ('method-exit', 'source-analysis', 'ancestor-frame'), 'evidence-kind')
        require(ev['environment'] in ('host-jvm', 'android-native', 'synthetic-validator-test', 'offline-source'), 'evidence-environment')
        require(sha_value(ev['receipt_sha256']) and isinstance(ev['event_id'], str) and bool(ev['event_id']), 'evidence-identity-missing')
        disposition = _check_observations(subject, row, constraint['rule'])
        if ev['kind'] != 'method-exit': disposition = 'pending-no-direct-method-exit'
        results.append({'subject_id': row['subject_id'], 'case_id': row['case_id'], 'state_id': row['state_id'], 'join': disposition, 'evidence_review': 'pending', 'qualified': False})
    return {'schema': 'mixer-editor-typed-join-result-v1', 'rows': results,
        'typed_consistent_count': sum(x['join'] == 'typed-consistent' for x in results),
        'remaining_subjects_without_rows': sorted(set(subjects)-{r['subject_id'] for r in rows}),
        'execution_closure': 'pending-fresh-trusted-execution-source-closure',
        'full_matrix': 'pending', 'native': 'pending', 'OTA': 'pending', 'GA': 'pending', 'qualified': False}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['validate'])
    parser.add_argument('--policy', type=Path)
    parser.add_argument('--rows', type=Path, required=True)
    args = parser.parse_args()
    try:
        # Reject duplicate JSON keys rather than let the last forged value win.
        def pairs(items):
            result = {}
            for key, value in items:
                require(key not in result, 'duplicate-json-key')
                result[key] = value
            return result
        doc = json.loads(args.rows.read_text(), object_pairs_hook=pairs, parse_constant=lambda value: (_ for _ in ()).throw(Refusal('nonfinite-json-number')))
        result = validate_rows(load_policy(args.policy), doc)
        print(json.dumps(result, indent=2))
    except (Refusal, ValueError, OSError, KeyError, TypeError) as failure:
        print(json.dumps({'status': 'refused', 'reason': str(failure), 'qualified': False}))
        raise SystemExit(2)

if __name__ == '__main__': main()
