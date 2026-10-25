"""Strict, supplementary telemetry only; never a guest or cleanup oracle."""
import json

LABELS = ('constructed', 'initialize', 'corpus_1', 'corpus_2', 'before_cleanup', 'final_cleanup')
ENVELOPE = 4608
LIFETIME = 27648
U8 = (1 << 8) - 1
U32 = (1 << 32) - 1
U64 = (1 << 64) - 1
# The bound producer is aarch64-apple-darwin: usize is 64 bits.
USIZE = U64
FUNCTION_BITS = 80000
ARRAYS = {'credits': 16, 'calls': 16, 'plans': 4, 'scan_credits': 2,
          'scan_calls': 2, 'scan_published': 2, 'build_credits': 2, 'build_calls': 2}
COUNTERS = ('completed', 'distinct', 'repeated')
ENVELOPE_FIELDS = frozenset(('lifecycle', 'sequence', 'reset_count', 'formatted',
    'observer_invalid', 'invariant_mask', 'adapter_invalid', 'prior_write_failed',
    'valid', 'cache_work', 'cache_decodes', 'decodes_bound_before_consumption', 'payload'))
AGGREGATE_FIELDS = frozenset((*ARRAYS, *COUNTERS, 'invalid', 'first_rejection'))
REJECTION_FIELDS = frozenset(('site', 'requested', 'cursor_function', 'cursor_offset',
    'kind', 'resource', 'function', 'offset', 'attempted', 'limit'))
KINDS = frozenset(('InvalidBudget', 'Cancelled', 'Deadline', 'Allocation', 'Adoption',
    'CategoryExhausted', 'CombinedExhausted', 'ResourceExhausted', 'FuelExhausted',
    'WorkExhausted', 'HostCallLimit', 'PinLimit', 'FrameLimit', 'ValueLimit',
    'ControlLimit', 'DecoderMismatch', 'UnsupportedEnvironment', 'GuestTrap',
    'GuestExit', 'Wasi', 'Invariant'))
RESOURCE_VARIANTS = ('Combined', 'CacheEntryBytes', 'CacheEntries', 'ActivePins',
    'Frames', 'Values', 'Controls', 'MemoryPages', 'CacheWork', 'ExecutionWork',
    'InstructionFuel', 'HostCalls', 'Deadline', 'TicketInventory', 'OwnerIdentity', 'ExactCapacity')
RESERVATIONS = ('RetainedSource', 'RetainedMetadata', 'Cache', 'State', 'Wasi', 'Shared', 'Construction')
RESOURCES = frozenset(('None', *(f'Some({r})' for r in RESOURCE_VARIANTS),
                     *(f'Some(Reservation({r}))' for r in RESERVATIONS)))


def uint(value, maximum):
    return type(value) is int and 0 <= value <= maximum


def strict_json(data):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate key')
            result[key] = value
        return result

    def reject_number(value):
        raise ValueError('producer emits integers only: ' + value)

    return json.loads(data, object_pairs_hook=pairs, parse_float=reject_number,
                      parse_constant=reject_number)


def rejection_schema(value):
    if value is None:
        return True
    if type(value) is not dict or set(value) != REJECTION_FIELDS:
        return False
    if not uint(value['site'], 15):
        return False
    if any(not uint(value[k], U64) for k in ('requested', 'attempted', 'limit')):
        return False
    if any(not (uint(value[k], U32) or (type(value[k]) is int and value[k] == U64))
           for k in ('cursor_function', 'function')):
        return False
    if any(not uint(value[k], USIZE) for k in ('cursor_offset', 'offset')):
        return False
    return (type(value['kind']) is str and value['kind'] in KINDS and
            type(value['resource']) is str and value['resource'] in RESOURCES)


def aggregate_schema(value):
    if type(value) is not dict or set(value) != AGGREGATE_FIELDS:
        return False
    if not uint(value['invalid'], U32):
        return False
    if any(not uint(value[k], U64) for k in COUNTERS):
        return False
    for key, length in ARRAYS.items():
        if type(value[key]) is not list or len(value[key]) != length:
            return False
        if any(not uint(v, U64) for v in value[key]):
            return False
    return rejection_schema(value['first_rejection'])


def envelope_schema(row):
    if type(row) is not dict or set(row) != ENVELOPE_FIELDS:
        return False
    if type(row['lifecycle']) is not str or row['lifecycle'] not in LABELS:
        return False
    if any(not uint(row[k], U8) for k in ('sequence', 'reset_count')):
        return False
    if any(type(row[k]) is not bool for k in ('formatted', 'prior_write_failed', 'valid',
                                            'decodes_bound_before_consumption')):
        return False
    if any(not uint(row[k], U32) for k in ('observer_invalid', 'invariant_mask', 'adapter_invalid')):
        return False
    if any(not uint(row[k], U64) for k in ('cache_work', 'cache_decodes')):
        return False
    return row['payload'] is None or aggregate_schema(row['payload'])


def rejection_matches_original(rejection, original):
    """Bind retained failure fields, without inventing a rejected debit from a failure.

    A sticky failure may precede the first observed rejected work call, so its
    function/offset need not equal that later call's cursor. Requested credits
    never enter successful counters. A null record is allowed for non-work failures.
    """
    failures = [e['payload'] for e in original if e['event'] in
                ('construction_failure', 'runtime_failure', 'final_failure') and
                type(e['payload']) is dict and 'kind' in e['payload']]
    if not failures:
        return False
    failure = failures[0]
    for key in ('kind', 'resource', 'function', 'offset', 'attempted', 'limit'):
        if key not in failure:
            continue
        expected = failure[key]
        if key in ('function', 'offset') and expected is None:
            expected = U64
        if key == 'resource':
            expected = 'None' if expected is None else f'Some({expected})'
        if type(rejection[key]) is not type(expected) or rejection[key] != expected:
            return False
    return True


def classify(path, original):
    issues, rows, total = [], [], 0
    expected = []
    try:
        expected = [e['event'] for e in original if e['event'] in LABELS[:-1]]
        if any(e['event'] == 'final_cleanup_usage' for e in original):
            expected.append('final_cleanup')
        for line in path.read_bytes().splitlines(keepends=True):
            at = line.find(b'MIXER_ATTRIBUTION ')
            if at < 0:
                continue
            encoded = line[at:]
            total += len(encoded)
            if len(encoded) > ENVELOPE:
                issues.append('envelope_overflow')
            if not encoded.endswith(b'\n'):
                issues.append('truncated_telemetry_line')
            try:
                rows.append(strict_json(encoded[len(b'MIXER_ATTRIBUTION '):]))
            except (ValueError, TypeError, UnicodeError):
                issues.append('malformed_telemetry')
        if len(rows) > 6 or total > LIFETIME:
            issues.append('lifetime_output_overflow')
        labels = [r.get('lifecycle') if type(r) is dict else None for r in rows]
        if labels != expected:
            issues.append('missing_duplicate_or_out_of_order_lifecycle')
        ranks = [LABELS.index(label) for label in labels if type(label) is str and label in LABELS]
        if any(a >= b for a, b in zip(ranks, ranks[1:])):
            issues.append('missing_duplicate_or_out_of_order_lifecycle')
        previous = None
        for i, row in enumerate(rows, 1):
            if not envelope_schema(row):
                issues.append('invalid_closed_typed_schema')
                continue
            if row['sequence'] != i or row['reset_count'] != 1:
                issues.append('sequence_or_reset_invalid')
            if row['decodes_bound_before_consumption'] != (row['lifecycle'] == 'final_cleanup'):
                issues.append('preconsumption_phase_invalid')
            if row['prior_write_failed']:
                issues.append('prior_write_failed')
            if not row['formatted']:
                issues.append('formatter_failed')
            usable = (row['formatted'] and row['observer_invalid'] == 0 and
                      row['invariant_mask'] == 0 and row['adapter_invalid'] == 0 and
                      not row['prior_write_failed'])
            if not usable or not row['valid']:
                issues.append('invalid_telemetry')
                if row['payload'] is not None:
                    issues.append('invalid_payload_not_discarded')
                continue
            payload = row['payload']
            if payload is None:
                issues.append('missing_payload')
                continue
            bound_event = 'final_cleanup_usage' if row['lifecycle'] == 'final_cleanup' else row['lifecycle']
            position = next((n for n, e in enumerate(original) if e['event'] == bound_event), len(original))
            event = original[position] if position < len(original) else None
            if row['lifecycle'] == 'final_cleanup':
                finals = [e['payload'] for e in original if e['event'] == 'final_cleanup_usage']
                pre = next((e['payload'] for e in original if e['event'] == 'before_cleanup'), None)
                if not finals or type(finals[-1]) is not dict:
                    issues.append('missing_original_final_usage')
                elif row['cache_work'] != finals[-1]['cache_work']:
                    issues.append('final_original_work_mismatch')
                if pre is not None and row['cache_decodes'] != pre['cache']['decodes']:
                    issues.append('preconsumption_decode_mismatch')
                if pre is None and row['cache_decodes'] != 0:
                    issues.append('construction_decode_mismatch')
            elif event is not None:
                if (row['cache_work'] != event['payload']['usage']['cache_work'] or
                        row['cache_decodes'] != event['payload']['cache']['decodes']):
                    issues.append('original_snapshot_mismatch')
            if payload['invalid'] != 0 or sum(payload['credits']) != row['cache_work']:
                issues.append('credit_sum_mismatch')
            if (payload['completed'] != row['cache_decodes'] or
                    payload['distinct'] + payload['repeated'] != payload['completed'] or
                    payload['distinct'] > FUNCTION_BITS):
                issues.append('completion_mismatch')
            if (sum(payload['scan_credits']) != payload['credits'][6] or
                    sum(payload['scan_calls']) != payload['calls'][6] or
                    sum(payload['scan_published']) != payload['plans'][3]):
                issues.append('scan_partition_mismatch')
            if (sum(payload['build_credits']) != payload['credits'][13] or
                    sum(payload['build_calls']) != payload['calls'][13]):
                issues.append('build_partition_mismatch')
            rejection = payload['first_rejection']
            if rejection is not None and not rejection_matches_original(rejection, original[:position + 1]):
                issues.append('rejection_original_failure_mismatch')
            if previous is not None:
                for key in (*ARRAYS, *COUNTERS):
                    now = payload[key] if key in ARRAYS else [payload[key]]
                    before = previous[key] if key in ARRAYS else [previous[key]]
                    if any(a < b for a, b in zip(now, before)):
                        issues.append('cumulative_counter_regression')
                if previous['first_rejection'] is not None and rejection != previous['first_rejection']:
                    issues.append('first_rejection_not_sticky')
            previous = payload
    except Exception as error:
        issues.append('telemetry_parser_error:' + type(error).__name__)
    issues = list(dict.fromkeys(issues))
    return {'schema': 1, 'authority': 'diagnostic telemetry only; original result and cleanup events authoritative',
        'status': 'valid' if not issues and rows else ('not_started' if not issues else 'invalid_or_missing'),
        'issues': issues, 'expectedLabels': expected, 'snapshots': rows, 'outputBytes': total,
        'maximumBytes': LIFETIME, 'originalResultReplaced': False, 'cleanupTruthInferredFromTelemetry': False}
