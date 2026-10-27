"""Pure source146 payload component arithmetic. This does not admit or execute.

Positive cut numbers are unresolved interface inputs, not evidence of a bound.
A caller needs independent source/backing/authority review before using a value.
"""
from __future__ import annotations

U64 = (1 << 64) - 1


class Refused(ValueError):
    pass


def natural(value):
    if type(value) is not int or value < 0 or value > U64:
        raise Refused('not-u64')
    return value


def positive(value):
    natural(value)
    if value == 0:
        raise Refused('required-positive-cut')
    return value


def add(*values):
    result = 0
    for value in values:
        natural(value)
        if result > U64 - value:
            raise Refused('add-overflow')
        result += value
    return result


def mul(left, right):
    natural(left)
    natural(right)
    if left and right > U64 // left:
        raise Refused('mul-overflow')
    return left * right


def evaluate_row(row, cuts, missing_inline_extent=None):
    """Return a *conditional component*, never a whole-host quote or grant.

    Each resource frontier needs two positive reviewed terms: source/interface
    destructor work and native/resource/backing request allowance. An unknown
    backing is not the inline handle extent and cannot default to zero.
    """
    extent = row['inline_bytes']
    if extent is None:
        extent = positive(missing_inline_extent)
    else:
        positive(extent)
    result = mul(row['structural_occurrence_allowance'], add(1, extent))
    expected = set(row['resource_frontiers'])
    if set(cuts) != expected:
        raise Refused('missing-or-unknown-resource-cut')
    for name, count in sorted(row['resource_frontiers'].items()):
        cut = cuts[name]
        element = row.get('dynamic_resource_elements', {}).get(name)
        fields = {'interface_work', 'native_resource_backing'}
        if element is not None:
            fields |= {'max_live_elements', 'element_inline_bytes', 'element_cuts'}
        if type(cut) is not dict or set(cut) != fields:
            raise Refused('incomplete-resource-cut')
        component = add(positive(cut['interface_work']), positive(cut['native_resource_backing']))
        if element is not None:
            component = add(component, mul(positive(cut['max_live_elements']),
                            evaluate_row(element, cut['element_cuts'], positive(cut['element_inline_bytes']))))
        result = add(result, mul(positive(count), component))
    return positive(result)


def required_cut_names(rows):
    return sorted({name for row in rows for name in row['resource_frontiers']})


def per_visit_maximum(rows, cuts):
    """The child-entry lane applies its separately proved 53 visit multiplier."""
    if not rows or set(cuts) != set(required_cut_names(rows)):
        raise Refused('incomplete-per-visit-domain')
    return max(evaluate_row(row, {name: cuts[name] for name in row['resource_frontiers']})
               for row in rows)


def returned_payload(rows, cuts):
    if len(rows) != 1 or rows[0]['type'] != 'OwnedFixtureOutcomeV1':
        raise Refused('wrong-returned-payload')
    return evaluate_row(rows[0], cuts)


def compose_p5(returned_carrier, actual_payload):
    return add(positive(returned_carrier), positive(actual_payload))
