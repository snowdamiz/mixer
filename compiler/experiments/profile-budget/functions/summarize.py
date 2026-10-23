"""Summarize non-authorizing per-body observations and labeled capacity bounds."""
import csv
import math
import re

COLUMNS = 'function,defined,type_index,body_offset,wire_bytes,local_groups,declared_locals,parameters,raw_instructions,raw_branch_targets,raw_branch_tables,raw_max_block_nesting,raw_immediate_bytes,raw_code_wire_bytes,raw_max_operand_height,status,error_offset,error_message_utf8_hex,instructions,instruction_capacity_bytes,branch_targets,branch_capacity_bytes,locals_capacity_bytes,max_block_nesting,retained_requested_above_baseline,peak_requested_above_baseline,peak_live_allocations_above_baseline,maximum_live_allocation_count'.split(',')
SHAPE = ['instructions', 'instruction_capacity_bytes', 'branch_targets', 'branch_capacity_bytes', 'locals_capacity_bytes', 'max_block_nesting']


def distribution(values):
    values = sorted(values)
    if not values:
        return None
    return {'count': len(values), 'minimum': values[0], 'p50': values[math.ceil(len(values) * .5) - 1],
            'p95': values[math.ceil(len(values) * .95) - 1], 'p99': values[math.ceil(len(values) * .99) - 1], 'maximum': values[-1]}


def summarize(path, observed):
    with open(path, newline='') as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != COLUMNS:
            raise ValueError('unexpected function observation columns')
        rows = []
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ValueError('incomplete function observation row')
            value = {key: item if key in ('status', 'error_message_utf8_hex') else (None if item == '' else int(item)) for key, item in row.items()}
            if any(item is not None and item < 0 for key, item in value.items() if key not in ('status', 'error_message_utf8_hex')):
                raise ValueError('negative observation')
            if value['defined'] != len(rows) or value['function'] != observed['imports'] + len(rows):
                raise ValueError('noncontiguous function observations')
            if value['body_offset'] + value['wire_bytes'] > observed['source_bytes']:
                raise ValueError('body span exceeds source')
            if value['status'] == 'decoded':
                if any(value[key] is None for key in SHAPE) or value['error_offset'] is not None or value['error_message_utf8_hex']:
                    raise ValueError('decoded body lacks observed shape')
                value['decoded_payload_capacity_bytes'] = sum(value[key] for key in ('instruction_capacity_bytes', 'branch_capacity_bytes', 'locals_capacity_bytes'))
                value['entry_bytes_with_inline_Function_header_estimate'] = value['decoded_payload_capacity_bytes'] + observed['layout']['function']
            elif any(value[key] is not None for key in SHAPE) or value['error_offset'] is None or not value['error_message_utf8_hex']:
                raise ValueError('rejected body must not report fake zero shape')
            value['error_message'] = bytes.fromhex(value['error_message_utf8_hex']).decode('utf8') if value['error_message_utf8_hex'] else None
            if value['raw_code_wire_bytes'] != value['raw_instructions'] + value['raw_immediate_bytes']: raise ValueError('raw instruction/immediate bytes disagree')
            if value['raw_max_operand_height'] is None or value['raw_max_operand_height'] > value['raw_instructions']:
                raise ValueError('invalid static operand-height inventory')
            # Conditional bound for this IR's payload capacity, not total heap/RSS:
            # one byte per instruction minimum; geometric push allocation;
            # br_table label capacities <=16*wire bytes; locals geometric extend.
            wire = value['wire_bytes']
            code_cap = 1 << (max(value['raw_instructions'], 4) - 1).bit_length()
            local_cap = max(8, 2 * value['declared_locals']) if value['declared_locals'] else 0
            value['conditional_payload_capacity_upper_bound_estimate'] = code_cap * observed['layout']['instruction'] + 8 * value['raw_branch_targets'] + 16 * value['raw_branch_tables'] + local_cap
            if value['status'] == 'decoded' and value['decoded_payload_capacity_bytes'] > value['conditional_payload_capacity_upper_bound_estimate']:
                raise ValueError('observed payload exceeds conservative bound')
            rows.append(value)
    if len(rows) != observed['functions']:
        raise ValueError('missing function observation')
    good = [row for row in rows if row['status'] == 'decoded']
    bad = [row for row in rows if row['status'] != 'decoded']
    if len(good) != observed['successful_bodies']:
        raise ValueError('decoder success count disagreement')
    layout = observed['layout']
    return {'authorization': False, 'valid': False, 'scope': 'all functions inventoried; scalar-arity/control operand heights are diagnostic, not operand type validation; only successful per-body decodes have measured IR shapes; no module type validation or execution',
            'function_count': len(rows), 'decoded_count': len(good), 'rejections': bad,
            'wire_body_bytes': sum(row['wire_bytes'] for row in rows),
            'raw_instruction_count': sum(row['raw_instructions'] for row in rows),
            'raw_maximum_block_nesting': max(row['raw_max_block_nesting'] for row in rows),
            'static_maximum_operand_height': max(row['raw_max_operand_height'] for row in rows),
            'static_maximum_declared_locals': max(row['declared_locals'] for row in rows),
            'static_maximum_parameters_plus_locals': max(row['parameters'] + row['declared_locals'] for row in rows),
            'largest_static_operand_heights': sorted(rows, key=lambda row: (-row['raw_max_operand_height'], row['function']))[:20],
            'operand_height_scope': 'per-function abstract stack slots using scalar arity, control label/result heights and unreachable polymorphism; includes retained operands below current control height; no type comparison or dynamic/caller/recursion stack measurement',
            'raw_branch_target_count': sum(row['raw_branch_targets'] for row in rows),
            'raw_branch_table_count': sum(row['raw_branch_tables'] for row in rows),
            'raw_immediate_wire_bytes': sum(row['raw_immediate_bytes'] for row in rows),
            'successful_instruction_count': sum(row['instructions'] for row in good),
            'successful_instruction_capacity_bytes_sum_arithmetic': sum(row['instruction_capacity_bytes'] for row in good),
            'successful_branch_capacity_bytes_sum_arithmetic': sum(row['branch_capacity_bytes'] for row in good),
            'successful_local_capacity_bytes_sum_arithmetic': sum(row['locals_capacity_bytes'] for row in good),
            'successful_decoded_payload_capacity_sum_arithmetic': sum(row['decoded_payload_capacity_bytes'] for row in good),
            'all_body_conditional_payload_capacity_bound_sum_estimate': sum(row['conditional_payload_capacity_upper_bound_estimate'] for row in rows),
            'capacity_bound_scope': 'conditional upper estimate on Instruction/branch/local Vec payload capacities using raw instruction/branch/local counts for this IR and Rust push/extend policy, if supported and structurally decoded; excludes native allocator metadata/transient realloc copies, inventory, cache bookkeeping, caller source, full validation and runtime memory; not a total-allocation bound',
            'distributions': {key: distribution([row[key] for row in good]) for key in SHAPE + ['decoded_payload_capacity_bytes', 'retained_requested_above_baseline', 'peak_requested_above_baseline', 'peak_live_allocations_above_baseline']},
            'largest_conditional_payload_bounds': sorted(rows, key=lambda row: (-row['conditional_payload_capacity_upper_bound_estimate'], row['function']))[:20],
            'largest_wire_bodies': sorted(rows, key=lambda row: (-row['wire_bytes'], row['function']))[:20],
            'largest_measured_payloads': sorted(good, key=lambda row: (-row['decoded_payload_capacity_bytes'], row['function']))[:20],
            'largest_observed_body_allocation_peaks': sorted(rows, key=lambda row: (-row['peak_requested_above_baseline'], row['function']))[:20],
            'existing_per_function_validator_scratch_bound_estimates': {
                'scope': 'conditional on passing current local/operand/control ceilings; no actual type-validator scratch or maximum operand-stack height was measured',
                'expanded_parameter_plus_local_vector_capacity_bytes': max(8, 2 * 4096),
                'operand_vector_capacity_bytes': 4096 * layout['validator_operand'],
                'control_vector_capacity_bytes': 128 * layout['validator_control'],
                'validator_inline_stack_bytes': layout['validator_state'],
                'decoder_control_vector_capacity_bytes': 128 * layout['decoder_control'],
                'actual_metadata_local_count_based_capacity_upper_estimate': max(8, 2 * observed['maximum_parameters_plus_locals']),
                'raw_control_inventory_if_future_ceiling_changed': {
                    'scope': 'hypothetical capacity arithmetic only; existing ceiling remains128 and rejected bodies remain rejected',
                    'required_control_depth_floor_including_function': max(row['raw_max_block_nesting'] for row in rows) + 1,
                    'current_control_vector_growth_capacity_to_cover_raw_depth': (1 << max(row['raw_max_block_nesting'] for row in rows).bit_length()),
                    'hypothetical_validator_control_capacity_bytes': (1 << max(row['raw_max_block_nesting'] for row in rows).bit_length()) * layout['validator_control'],
                    'hypothetical_decoder_control_capacity_bytes': (1 << (max(row['raw_max_block_nesting'] for row in rows) - 1).bit_length()) * layout['decoder_control']},
                'excludes': ['decoded code and branch payloads', 'diagnostic index/source', 'error formatting and other validation metadata', 'allocator internal metadata/transient realloc copies', 'guest runtime frames/memory', 'future streaming validator implementation']},
            'raw_control_nesting_over_existing_body_ceiling': [{'function': row['function'], 'nested_blocks': row['raw_max_block_nesting'], 'including_function': row['raw_max_block_nesting'] + 1} for row in rows if row['raw_max_block_nesting'] >= 128],
            'parameters_plus_locals_over_existing_ceiling': [{'function': row['function'], 'count': row['parameters'] + row['declared_locals']} for row in rows if row['parameters'] + row['declared_locals'] > 4096],
            'static_operand_heights_over_existing_ceiling': [{'function': row['function'], 'count': row['raw_max_operand_height']} for row in rows if row['raw_max_operand_height'] > 4096]}


def attribute(csv_path, map_path, statistics):
    """Require an exact all-function map-to-wire relation before naming samples."""
    selected = {row['function'] for key in ('rejections', 'largest_wire_bodies', 'largest_measured_payloads', 'largest_conditional_payload_bounds', 'largest_static_operand_heights') for row in statistics[key]}
    pattern = re.compile(r'\s*(-|[0-9a-f]+)\s+([0-9a-f]+)\s+([0-9a-f]+)( +)(.*)')
    def inputs():
        group = None
        with open(map_path) as stream:
            for line in stream:
                match = pattern.fullmatch(line.rstrip('\n'))
                if not match: continue
                address, offset, size, spaces, name = match.groups()
                if len(spaces) == 1: group = name
                elif group == 'CODE' and len(spaces) == 9:
                    yield int(offset, 16), int(size, 16), name
    mapped = inputs(); samples = []; count = 0; biases = set()
    with open(csv_path, newline='') as stream:
        for row in csv.DictReader(stream):
            item = next(mapped, None)
            if item is None: raise ValueError('map lacks corresponding function input')
            offset, size, name = item
            wire = int(row['wire_bytes']); prefix = max(1, math.ceil(wire.bit_length() / 7))
            if size != wire + prefix: raise ValueError('link map function size does not equal actual body plus length LEB')
            bias = int(row['body_offset']) - prefix - offset; biases.add(bias)
            function = int(row['function']); count += 1
            if function in selected: samples.append({'function': function, 'defined': int(row['defined']), 'input': name,
                'link_map_file_offset': offset, 'body_bytes': wire, 'length_prefix_bytes': prefix})
    if next(mapped, None) is not None or biases != {5}: raise ValueError('unqualified map order or file-offset bias')
    return {'authorization': False, 'scope': 'CODE input ordinal/size and constant file-offset relation checked against every actual body; no approximate name matching',
            'verified_function_count': count, 'observed_link_map_offset_bias_bytes': 5, 'samples': samples}
