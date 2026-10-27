"""Source-pinned receiver bridge plus the mandatory all-state raw join.

This is an ordinary host evidence consistency utility. Its trust root is the
independently selected source/packet identity supplied by the enclosing runner.
It grants no execution, helper-body, native, OTA, or GA admission.
"""
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
POLICY_SHA256 = 'ac78ec62ca626e860f19b1a162a9acb29f492453239714589d32900bddadfad5'


class DelegatedReceiverRefusal(ValueError):
    pass


def require(value, reason):
    if not value:
        raise DelegatedReceiverRefusal(reason)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_packet(dependency, module_name):
    base = HERE / dependency['path']
    require(not base.is_symlink(), 'dependency directory cannot be substituted by symlink')
    require(digest(base / 'seal.json') == dependency['seal_sha256'], 'immutable dependency seal')
    seal = json.loads((base / 'seal.json').read_bytes())
    expected = {'seal.json'} | {item['path'] for item in seal['members']}
    nodes = list(base.rglob('*'))
    require(not any(path.is_symlink() for path in nodes), 'dependency contains symlink')
    require({str(path.relative_to(base)) for path in nodes if path.is_file()} == expected,
            'closed dependency file roster')
    for item in seal['members']:
        relative = Path(item['path'])
        require(not relative.is_absolute() and '..' not in relative.parts, 'bounded dependency path')
        path = base / relative
        require(path.stat().st_size == item['bytes'] and digest(path) == item['sha256'],
                'exact dependency member: ' + item['path'])
    require(digest(base / module_name) == dependency['module_sha256'], 'immutable dependency module')
    require(digest(base / 'policy.json') == dependency['policy_sha256'], 'immutable dependency policy')
    return base


def load_policy():
    require(digest(HERE / 'policy.json') == POLICY_SHA256, 'immutable receiver policy')
    policy = json.loads((HERE / 'policy.json').read_bytes())
    verify_packet(policy['corrected_dependency'], 'typed_join.py')
    base = verify_packet(policy['raw_dependency'], 'delegated_raw.py')
    return policy, base


def same(left, right):
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return left.keys() == right.keys() and all(same(left[key], right[key]) for key in left)
    if type(left) is list:
        return len(left) == len(right) and all(same(a, b) for a, b in zip(left, right))
    return left == right


def integer(value, reason):
    require(type(value) is int and value >= 0, reason)
    return value


def global_identity(value, actual_class):
    require(type(value) is str and len(value) <= 1100 and value.startswith(actual_class + '@'),
            'global receiver exact runtime class')
    suffix = value[len(actual_class) + 1:]
    require(suffix.isascii() and suffix.isdecimal() and 0 < len(suffix) <= 20
            and suffix == str(int(suffix)) and int(suffix) > 0, 'canonical positive global receiver identity')


def validate_receiver_bindings(row, policy):
    require(type(row) is dict, 'raw row object')
    sequence = row.get('native_sequence')
    bindings = row.get('native_receiver_bindings')
    frames = row.get('frame_sets')
    outcomes = row.get('actual_native_outcomes')
    require(type(sequence) is list and len(sequence) <= 100000, 'bounded complete raw event sequence')
    require(type(frames) is list and len(frames) <= 100000, 'bounded complete raw frame sets')
    require(type(outcomes) is list and len(outcomes) <= 65536, 'bounded complete native outcome list')
    require(type(bindings) is list and len(bindings) <= policy['maximum_receivers'],
            'actual ordinal/global receiver bindings required')
    by_row = {}
    globals_seen = set()
    for offset, binding in enumerate(bindings):
        require(type(binding) is dict and set(binding) == set(policy['receiver_binding_fields']),
                'exact receiver binding fields')
        ordinal = integer(binding['ordinal'], 'receiver ordinal must be integer')
        require(ordinal == offset + 1, 'unique contiguous positive receiver ordinal order')
        actual_class = binding['class']
        require(type(actual_class) is str and 0 < len(actual_class) <= 1024 and '@' not in actual_class
                and not any(ord(char) < 33 for char in actual_class), 'actual runtime receiver class')
        row_identity = binding['row_identity']
        require(type(row_identity) is str and row_identity == actual_class + '@row-' + str(ordinal),
                'ordinal row identity equals actual class and ordinal')
        global_id = binding['global_identity']
        global_identity(global_id, actual_class)
        require(row_identity not in by_row and global_id not in globals_seen,
                'unique ordinal and global object identities')
        by_row[row_identity] = global_id
        globals_seen.add(global_id)
    first_seen = []
    used = set()
    for event in sequence:
        require(type(event) is dict and 'receiver_identity' in event, 'raw event receiver field')
        index = integer(event.get('frame_set'), 'raw event frame-set index type')
        require(index < len(frames), 'raw event frame-set range')
        identity = event['receiver_identity']
        if identity is None:
            continue
        require(type(identity) is str and identity in by_row, 'raw event has exact receiver binding')
        if identity not in used:
            first_seen.append(identity)
            used.add(identity)
    require(first_seen == list(by_row), 'closed receiver roster in first actual event order')
    for outcome in outcomes:
        require(type(outcome) is dict, 'native outcome object')
        index = integer(outcome.get('native_event_sequence_index'), 'native outcome exact event index type')
        require(index < len(sequence), 'native outcome exact event index range')
        event = sequence[index]
        identity = event['receiver_identity']
        require('receiver_identity' in outcome and outcome['receiver_identity'] == (None if identity is None else by_row[identity]),
                'native outcome global receiver equals its actual raw event receiver binding')
        require(type(outcome.get('method')) is str and outcome['method'] == event.get('method'),
                'native outcome method equals actual raw event method')
        require(type(outcome.get('native_event_phase')) is str and outcome['native_event_phase'] == event.get('phase'),
                'native outcome phase equals actual raw event phase')
        require(same(outcome.get('production_frames'), frames[event['frame_set']]),
                'native outcome full frames equal its actual raw event frames')
    selected = row.get('selected_event')
    require(type(selected) is list, 'selected immutable events required')
    for point in selected:
        require(type(point) is dict, 'selected immutable event object')
        index = integer(point.get('sequence_index'), 'selected event exact index type')
        require(index < len(sequence), 'selected event exact index range')
        identity = sequence[index]['receiver_identity']
        require(identity is not None and by_row[identity] == row.get('original_target'),
                'selected original Event.receiver maps exactly to original target')
        captured = point.get('authority')
        require(type(captured) is dict and captured.get('receiver') == by_row[identity],
                'selected captured authority uses same actual receiver object')
    return {'receiver_bindings': len(bindings), 'native_outcomes_joined': len(outcomes),
            'receiver_join': 'exact-actual-event-ordinal-global-authority-binding'}


def validate_delegated_raw(raw_row):
    """Require the actual receiver bridge, then the unchanged v1 raw state join.

    All normal returns remain actual observations; a hook exception never supplies
    an unobserved normal scalar/body result. Compact-only rows cannot call this API.
    """
    try:
        policy, base = load_policy()
        receiver_report = validate_receiver_bindings(raw_row, policy)
        spec = importlib.util.spec_from_file_location('_mixer_delegated_raw_v1_reference', base / 'delegated_raw.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        try:
            report = module.validate_delegated_raw(raw_row)
        except module.DelegatedRawRefusal as failure:
            raise DelegatedReceiverRefusal('mandatory raw state join: ' + str(failure)) from failure
        report.update(receiver_report)
        report['receiver_policy_sha256'] = POLICY_SHA256
        report['qualified'] = False
        return report
    except DelegatedReceiverRefusal:
        raise
    except (OSError, KeyError, TypeError, ValueError, IndexError, AttributeError) as failure:
        raise DelegatedReceiverRefusal('missing or malformed receiver/raw dependency: ' + str(failure)) from failure
