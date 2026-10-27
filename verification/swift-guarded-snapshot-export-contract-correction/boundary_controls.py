"""Additional finite data controls; none constructs an authentic proof or guard."""
import struct


def controls(model):
    base = model.assemble_unverified_fixture()
    rows = []

    def changed(*pairs):
        value = bytearray(base)
        for offset, number in pairs:
            value[offset:offset+8] = struct.pack('<Q', number)
        return bytes(value)

    def case(name, accept, *pairs):
        value = changed(*pairs)
        try:
            model.parse(value)
            accepted, refusal = True, None
        except model.Refused as error:
            accepted, refusal = False, str(error)
        rows.append({'name': name, 'expected_acceptance': accept,
                     'accepted': accepted, 'refusal': refusal,
                     'expectation_met': accepted == accept,
                     'mutations': [{'offset': p, 'value': n} for p, n in pairs]})

    # Each newly joined direct field, including both declaration option words.
    for name, offset, number in [
        ('memory-minimum-meta', 392, 2), ('memory-minimum-observation', 328, 2),
        ('memory-host-meta', 400, 767), ('memory-host-observation', 352, 767),
        ('memory-max-meta-presence', 432, 1), ('memory-max-observation-presence', 336, 1),
        ('table-minimum-meta', 416, 2), ('table-minimum-observation', 360, 2),
        ('table-max-meta-value', 456, 65535), ('table-max-observation-value', 376, 65535),
        ('runtime-type-count', 1368, 2), ('runtime-slot-limit', 1376, 2),
        ('runtime-pin-limit', 1384, 2), ('runtime-active-pins', 1168, 2),
        ('runtime-cache-capacity', 1408, 16777215), ('runtime-cache-budget', 1144, 16777215),
        ('runtime-entry-limit', 1416, 8388607), ('runtime-entry-budget', 1152, 8388607),
        ('source-identity-extent', 792, 63), ('validation-usage-deadline', 216, 119999),
    ]:
        case('duplicate-' + name, False, (offset, number))

    case('memory-max-none-pair-contradiction', False, (432,1),(440,1))
    case('table-max-none-pair-contradiction', False, (448,0),(456,0))
    # Clearing all representable metadata/observation memory/table words does
    # not make an absent memory/table into an accepted Swift proof.
    case('coherently-absent-memory-refused', False,
         (384,0),(392,0),(400,0),(432,0),(440,0),(328,0),(336,0),(344,0),(352,0))
    case('coherently-absent-table-refused', False,
         (408,0),(416,0),(424,0),(448,0),(456,0),(360,0),(368,0),(376,0))
    case('none-memory-maximum-uses-policy-cap', True)
    case('none-memory-maximum-zero-payload-required', False, (440,1),(344,1))
    case('none-memory-maximum-host-cannot-narrow', False, (400,767),(352,767))
    case('some-memory-maximum-joins-host', True, (432,1),(440,1),(336,1),(344,1),(400,1),(352,1))
    case('some-memory-maximum-host-mismatch', False, (432,1),(440,1),(336,1),(344,1))
    case('some-memory-maximum-zero-distinct-from-none', True,
         (392,0),(328,0),(400,0),(352,0),(432,1),(440,0),(336,1),(344,0))
    case('memory-minimum-exceeds-host', False,
         (432,1),(440,0),(336,1),(344,0),(400,0),(352,0))
    case('memory-maximum-ceiling-plus-one', False,
         (432,1),(440,769),(336,1),(344,769),(400,769),(352,769))
    case('none-table-maximum-uses-policy-cap', True, (448,0),(456,0),(368,0),(376,0))
    case('none-table-maximum-zero-payload-required', False, (448,0),(456,1),(368,0),(376,1))
    case('none-table-maximum-host-cannot-narrow', False,
         (448,0),(456,0),(368,0),(376,0),(424,65535))
    case('some-table-maximum-host-mismatch', False, (424,65535))
    case('some-table-maximum-zero-distinct-from-none', True,
         (416,0),(360,0),(424,0),(448,1),(456,0),(368,1),(376,0))
    case('table-minimum-exceeds-host', False,
         (424,0),(448,1),(456,0),(368,1),(376,0))
    case('table-maximum-ceiling-plus-one', False, (424,65537),(456,65537),(376,65537))
    # min(cache_entries, defined_functions) is not a blanket equality to budget.
    case('slot-limit-minimum-fewer-defined-than-budget', True, (1160,64))
    case('slot-limit-wrongly-equal-to-larger-budget', False, (1160,64),(1376,64))
    case('slot-budget-zero-refused', False, (1160,0))
    case('slot-budget-ceiling-plus-one', False, (1160,65))
    case('pin-limit-at-ceiling', True, (1168,64),(1384,64))
    case('pin-limit-ceiling-plus-one', False, (1168,65),(1384,65))
    case('pin-limit-zero-refused', False, (1168,0),(1384,0))
    case('initial-nonce-still-one', False, (1392,2))
    case('cache-base-bound-not-equality', True)
    case('cache-base-over-capacity', False, (1400,16777217))
    # Separate loader/runtime configuration: do not invent source equations.
    case('runtime-validation-deadlines-may-differ', True, (1256,1))
    case('wasi-none-zero-optional-record', True)
    case('wasi-some-zero-remains-distinct', True, (1112,1))
    case('wasi-none-nonzero-optional-record-refused', False, (1264,1))
    return rows
