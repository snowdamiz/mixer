"""Independent arithmetic oracle; synthetic controls select no product floor."""
import json

MAXIMUM = (1 << 64) - 1


def add(a, b):
    if min(a, b) < 0 or a > MAXIMUM - b:
        raise OverflowError((a, b))
    return a + b


def multiply(a, b):
    if min(a, b) < 0 or max(a, b) > MAXIMUM or (b and a > MAXIMUM // b):
        raise OverflowError((a, b))
    return a * b


def aligned(value, alignment):
    if alignment <= 0 or alignment & (alignment - 1):
        raise ValueError(alignment)
    return add(value, alignment - 1) & ~(alignment - 1)


def aggregate(fields):
    """Rust repr(C)-style control only; Rust default layout requires measurement."""
    extent, maximum_alignment = 0, 1
    for size, alignment in fields:
        extent = add(aligned(extent, alignment), size)
        maximum_alignment = max(maximum_alignment, alignment)
    return aligned(extent, maximum_alignment)


def phase_sum(occurrences, expected_ids, phase):
    ids = [row['id'] for row in occurrences]
    if len(ids) != len(set(ids)) or set(ids) != set(expected_ids):
        raise ValueError('duplicate or missing source occurrence')
    total = 0
    for row in occurrences:
        if row['begin'] <= phase < row['end']:
            # A None value has no effect on its measured inline storage extent.
            total = add(total, multiply(row['measured_type_bytes'], row['count']))
    return total


def controls():
    cases = []
    def check(name, actual, expected):
        assert actual == expected, (name, actual, expected)
        cases.append({'name': name, 'passed': True, 'actual': actual})
    def rejects(name, operation, expected):
        try:
            operation()
        except expected:
            cases.append({'name': name, 'passed': True, 'rejected': expected.__name__})
        else:
            raise AssertionError(name)
    check('zero', add(0, 0), 0)
    check('inclusive maximum', add(MAXIMUM - 1, 1), MAXIMUM)
    rejects('addition overflow', lambda: add(MAXIMUM, 1), OverflowError)
    rejects('multiplication overflow', lambda: multiply(MAXIMUM, 2), OverflowError)
    rejects('alignment overflow', lambda: aligned(MAXIMUM, 8), OverflowError)
    rejects('non power of two alignment', lambda: aligned(0, 3), ValueError)
    check('aggregate internal and trailing padding', aggregate([(1, 1), (8, 8), (1, 1)]), 24)
    rows = [
        {'id': 'scope.Option.none', 'measured_type_bytes': 40, 'count': 1, 'begin': 0, 'end': 3, 'value': None},
        {'id': 'retained.outer.error', 'measured_type_bytes': 24, 'count': 2, 'begin': 1, 'end': 4},
        {'id': 'phase.return', 'measured_type_bytes': 16, 'count': 1, 'begin': 1, 'end': 2},
    ]
    expected = [row['id'] for row in rows]
    check('None occupies full measured inline extent', phase_sum(rows, expected, 0), 40)
    check('error and return lifetimes overlap', phase_sum(rows, expected, 1), 104)
    check('scope ends but retained errors remain', phase_sum(rows, expected, 3), 48)
    check('all places destroyed', phase_sum(rows, expected, 4), 0)
    rejects('missing source occurrence', lambda: phase_sum(rows[:-1], expected, 1), ValueError)
    rejects('duplicate source occurrence', lambda: phase_sum(rows + [rows[0]], expected, 1), ValueError)
    return {'schema': 1, 'scope': 'synthetic arithmetic oracle controls only; no Mixer layout or operational total', 'cases': cases}


if __name__ == '__main__':
    print(json.dumps(controls(), indent=2, sort_keys=True))
