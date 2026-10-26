"""Lossless reviewer fixture transport. This module never accesses a candidate."""
import json
from pathlib import Path
import stat
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PRE = ROOT / 'verification/swift-cache-state-independent-review/preaccess'
PREP = ROOT / 'verification/swift-cache-state-independent-review/execution-preparation'
sys.dont_write_bytecode = True
sys.path.insert(0, str(PREP))
import future_runner as sealed
from harness import sha, write_json

FILES = {'basics': 'cases.json', 'words': 'word-mutations.json',
         'transitions': 'stage-transitions.json', 'sequences': 'sequence-variants.json',
         'terminal-full32': 'terminal-full32.json'}
ROLES = {'stream', 'profile', 'context', 'fixture', 'policy'}
ROLE_CAPS = {'stream': 1048576, 'profile': 2560512, 'context': 8192, 'fixture': 262144, 'policy': 65536}


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':')) + '\n').encode()


def terminal_eligibility(item):
    if (item['input']['SS'], item['input']['SF']) != (1, 1):
        return 'partial-paid-domain-contract-exclusion-source-proof-only-zero-runtime-pass-credit'
    if item['expected_words'] is None:
        return 'outer-error-no-observation-private-source-or-IO-seam-not-implemented'
    return 'unimplemented-private-seam-requires-separate-root-admission'


def selection(kind, start, count):
    if kind not in FILES or type(start) is not int or type(count) is not int or start < 0 or not 1 <= count <= 64:
        raise ValueError('closed kind and bounded1..64 selection')
    path = PRE / 'fixtures' / FILES[kind]
    raw = path.read_bytes()
    data = json.loads(raw)
    if start + count > len(data):
        raise ValueError('selection exceeds sealed case list')
    return path, raw, data[start:start + count]


def put_object(root, objects, role, raw):
    if role not in ROLES or type(raw) is not bytes:
        raise ValueError('closed role/raw bytes')
    if len(raw) > ROLE_CAPS[role]:
        raise ValueError('bounded reviewer fixture object')
    digest = sha(raw)
    key = role + '/' + digest
    path = root / 'objects' / role / (digest + '.bin')
    value = {'role': role, 'sha256': digest, 'bytes': len(raw), 'path': str(path.relative_to(root))}
    if key in objects:
        if objects[key] != value or path.read_bytes() != raw:
            raise ValueError('content object mismatch')
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        objects[key] = value
    return key


def build_pack(kind, start, count, destination):
    """Reuses sealed data-only materialization; no expectation/oracle changes."""
    path, raw, selected = selection(kind, start, count)
    destination = Path(destination)
    if destination.exists():
        raise ValueError('preserve existing transport evidence')
    destination.mkdir(parents=True)
    objects = {}
    policy_raw = (PRE / 'private-controls.json').read_bytes()
    policy_ref = put_object(destination, objects, 'policy', policy_raw)
    public = None if kind == 'terminal-full32' else iter(sealed.cases(kind, start, count))
    cases = []
    logical_bytes = 0
    for index, item in enumerate(selected, start):
        fixture = put_object(destination, objects, 'fixture', canonical(item))
        refs = None
        layer = 'private terminal data only; no actual-File claim or execution support'
        eligibility = 'unimplemented-private-seam-requires-separate-root-admission'
        if public is not None:
            old = next(public)
            if old['id'] != item['id'] or old['expected_words'] != item['expected_words']:
                raise ValueError('sealed case identity/expectation drift')
            refs = {role: put_object(destination, objects, role, payload)
                    for role, payload in zip(['stream', 'profile', 'context'], old['payload'])}
            logical_bytes += sum(len(v) for v in old['payload'])
            layer = old['coverage_layer']
            eligibility = 'public-four-distinct-ordinary-quiescent-Files'
        else:
            eligibility = terminal_eligibility(item)
        cases.append({'index': index, 'id': item['id'], 'source_item': fixture,
                      'expected_words': item.get('expected_words'),
                      'expected_error': item.get('expected_error'), 'input_refs': refs,
                      'coverage_layer': layer, 'runtime_eligibility': eligibility})
    result = {'schema': 1, 'kind': kind, 'start': start, 'count': count,
              'source_fixture_path': str(path.relative_to(ROOT)), 'source_fixture_sha256': sha(raw),
              'preaccess_seal_sha256': sealed.PREACCESS_SHA,
              'sealed_materializer_sha256': sha((PREP / 'future_runner.py').read_bytes()),
              'policy_ref': policy_ref, 'objects': objects, 'cases': cases,
              'logical_input_bytes': logical_bytes,
              'unique_input_bytes': sum(o['bytes'] for o in objects.values() if o['role'] in {'stream', 'profile', 'context'}),
              'candidate_execution_count': 0,
              'policy': 'Verbatim sealed expected words and source metadata; explicit private overlap allowed sets retained unchanged; no broadened reason matching or precedence inference.'}
    write_json(destination / 'transport.json', result)
    return result


def object_path(root, data, ref, expected_role=None):
    if not isinstance(ref, str) or ref not in data['objects']:
        raise ValueError('unknown object reference')
    o = data['objects'][ref]
    if set(o) != {'role', 'sha256', 'bytes', 'path'} or o['role'] not in ROLES:
        raise ValueError('closed object metadata')
    if expected_role is not None and o['role'] != expected_role:
        raise ValueError('object role mismatch')
    if len(o['sha256']) != 64 or any(c not in '0123456789abcdef' for c in o['sha256']):
        raise ValueError('object digest')
    expected_key = o['role'] + '/' + o['sha256']
    expected_path = 'objects/' + o['role'] + '/' + o['sha256'] + '.bin'
    if ref != expected_key or o['path'] != expected_path:
        raise ValueError('closed content-addressed path')
    if type(o['bytes']) is not int or not 0 <= o['bytes'] <= ROLE_CAPS[o['role']]:
        raise ValueError('bounded reviewer object size')
    p = Path(root) / expected_path
    for q in [p, p.parent, p.parent.parent]:
        if q.is_symlink():
            raise ValueError('symlink object path')
    if not stat.S_ISREG(p.lstat().st_mode) or p.stat().st_size != o['bytes']:
        raise ValueError('regular exact-size object only')
    raw = p.read_bytes()
    if type(o['bytes']) is not int or o['bytes'] != len(raw) or sha(raw) != o['sha256']:
        raise ValueError('object byte/hash mismatch')
    return p


def validate_pack(root):
    root = Path(root)
    data = json.loads((root / 'transport.json').read_bytes())
    path, raw, original = selection(data['kind'], data['start'], data['count'])
    if data['schema'] != 1 or data['source_fixture_path'] != str(path.relative_to(ROOT)) or data['source_fixture_sha256'] != sha(raw):
        raise ValueError('sealed source binding')
    if data['preaccess_seal_sha256'] != sealed.PREACCESS_SHA or data['sealed_materializer_sha256'] != sha((PREP / 'future_runner.py').read_bytes()):
        raise ValueError('immutable reviewer input/tool binding')
    if len(data['cases']) != len(original):
        raise ValueError('case count')
    for ref in data['objects']:
        object_path(root, data, ref)
    policy = object_path(root, data, data['policy_ref'], 'policy').read_bytes()
    if policy != (PRE / 'private-controls.json').read_bytes():
        raise ValueError('refusal/overlap policy changed')
    materialized = None if data['kind'] == 'terminal-full32' else iter(sealed.cases(data['kind'], data['start'], data['count']))
    logical_bytes = 0
    for index, (case, expected) in enumerate(zip(data['cases'], original), data['start']):
        if set(case) != {'index', 'id', 'source_item', 'expected_words', 'expected_error', 'input_refs', 'coverage_layer', 'runtime_eligibility'}:
            raise ValueError('closed case mapping')
        if case['index'] != index or case['id'] != expected['id']:
            raise ValueError('case identity/order drift')
        if object_path(root, data, case['source_item'], 'fixture').read_bytes() != canonical(expected):
            raise ValueError('verbatim source case changed')
        if case['expected_words'] != expected.get('expected_words') or case['expected_error'] != expected.get('expected_error'):
            raise ValueError('expectation changed')
        if data['kind'] == 'terminal-full32':
            if case['input_refs'] is not None or case['coverage_layer'] != 'private terminal data only; no actual-File claim or execution support' or case['runtime_eligibility'] != terminal_eligibility(expected):
                raise ValueError('terminal/private classification changed')
        else:
            if set(case['input_refs']) != {'stream', 'profile', 'context'} or case['runtime_eligibility'] != 'public-four-distinct-ordinary-quiescent-Files':
                raise ValueError('public input map')
            paths = [object_path(root, data, case['input_refs'][role], role) for role in ['stream', 'profile', 'context']]
            if len({(p.stat().st_dev, p.stat().st_ino) for p in paths}) != 3:
                raise ValueError('public inputs must be three distinct ordinary Files')
            inherited = next(materialized)
            if inherited['id'] != case['id'] or inherited['expected_words'] != case['expected_words'] or inherited['coverage_layer'] != case['coverage_layer']:
                raise ValueError('sealed materialized case drift')
            for p, payload in zip(paths, inherited['payload']):
                if p.read_bytes() != payload:
                    raise ValueError('per-case exact logical input bytes changed')
                logical_bytes += len(payload)
    unique = sum(o['bytes'] for o in data['objects'].values() if o['role'] in {'stream', 'profile', 'context'})
    if data['logical_input_bytes'] != logical_bytes or data['unique_input_bytes'] != unique:
        raise ValueError('lossless storage accounting')
    return data
