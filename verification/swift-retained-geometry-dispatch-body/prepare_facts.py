"""Bounded stdlib file/text preparation; never imports or runs analyzed code.

The semantic interpretations below are producer candidates for independent/root
review. This script pins/extracts their complete function evidence and inventories
text. It is not the physical-region verifier and produces no accepted geometry.
"""
from pathlib import Path
import hashlib
import json
import signal
import sys
import time

signal.alarm(50)
START = time.monotonic()
ROOT = Path('/Users/andreyyurlov/Documents/dev/mixer')
OUT = ROOT / 'verification/swift-retained-geometry-dispatch-body'
MAPPING = ROOT / 'verification/swift-retained-capture-terminal-mapping'
MAX_DERIVED = 8 * 1024 * 1024


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()


def write(name, value):
    raw = encode(value)
    assert len(raw) <= MAX_DERIVED
    (OUT / name).write_bytes(raw)


before = json.loads((OUT / 'input-pins-before.json').read_text())
tool_before = {'path': sys.executable, 'bytes': Path(sys.executable).stat().st_size,
               'sha256': sha(Path(sys.executable).read_bytes())}
preparer_before = sha(Path(__file__).read_bytes())
expected = {row['path']: row for row in before['inputs']}
for name, row in expected.items():
    raw = (ROOT / name).read_bytes()
    assert len(raw) == row['bytes'] and sha(raw) == row['sha256'], name

target_map = json.loads((MAPPING / 'target-map.json').read_text())
targets = {row['id']: row for row in target_map['targets']}
raw_pair = {}
for kind, path, count, digest in [
    ('ir', 'verification/swift-root-bound-dispatch-retained-capture-v1/runtime/generated/dispatch.ll',
     66974303, '788126f146f9da84a8e190c87b638bb4ae284a8321cce2ac6f47ffda64b7880a'),
    ('asm', 'verification/swift-root-bound-dispatch-retained-capture-v1/runtime/generated/dispatch.s',
     44456451, 'c6bac3481f6c5ad1223e4a3ae1a069505cf3bf32450fbfb338b073b2a25e0894'),
]:
    raw = (ROOT / path).read_bytes()
    assert len(raw) == count and sha(raw) == digest
    raw_pair[kind] = raw
assert sum(map(len, raw_pair.values())) == 111430754 <= 128 * 1024 * 1024

texts = {}
spans = {}
for target in ('Dispatch', 'Body'):
    for kind, suffix, field in [('ir', 'll', 'llvm_definition'), ('asm', 's', 'assembly_function')]:
        row = targets[target][field]
        raw = raw_pair[kind][row['byte_begin']:row['byte_end']]
        assert raw == (MAPPING / 'excerpts' / (target + '.' + suffix)).read_bytes()
        assert sha(raw) == row['span_sha256']
        texts[target, kind] = raw
        spans[target, kind] = row
    assert texts[target, 'ir'].startswith(b'define ') and texts[target, 'ir'].endswith(b'}\n')
    assert texts[target, 'asm'].endswith(b'\t.cfi_endproc\n')

exception = json.loads((MAPPING / 'body-exception-table.json').read_text())['span']
exception_raw = raw_pair['asm'][exception['byte_begin']:exception['byte_end']]
assert exception_raw == (MAPPING / 'excerpts/Body-exception-table.s').read_bytes()
assert sha(exception_raw) == exception['span_sha256']


def whole(target, kind):
    row = spans[target, kind]
    return {'artifact': kind, 'begin': row['byte_begin'], 'end': row['byte_end'],
            'sha256': row['span_sha256'], 'global_line_begin': row['line_begin'],
            'global_line_end_inclusive': row['line_end_inclusive']}


def lines(target, kind, first, last=None):
    if last is None:
        last = first
    raw = texts[target, kind]
    parts = raw.splitlines(keepends=True)
    assert 1 <= first <= last <= len(parts)
    begin = spans[target, kind]['byte_begin'] + sum(map(len, parts[:first - 1]))
    result = b''.join(parts[first - 1:last])
    return {'artifact': kind, 'begin': begin, 'end': begin + len(result), 'sha256': sha(result),
            'excerpt_line_begin': first, 'excerpt_line_end_inclusive': last,
            'global_line_begin': spans[target, kind]['line_begin'] + first - 1,
            'global_line_end_inclusive': spans[target, kind]['line_begin'] + last - 1}


def needle(target, kind, value):
    raw = texts[target, kind]
    data = value.encode()
    assert raw.count(data) == 1, (target, kind, value)
    first = raw[:raw.index(data)].count(b'\n') + 1
    return lines(target, kind, first, first + data.count(b'\n'))


def slot(name, offset, width, alignment, evidence=None):
    return {'llvm_or_native_name': name, 'final_sp_offset': offset, 'capacity_bytes': width,
            'entry_sp_offset': offset - (41024 if CURRENT_TARGET == 'Dispatch' else 63920),
            'llvm_required_alignment': alignment, 'physical_alignment_known': None,
            'evidence': evidence or [whole(CURRENT_TARGET, 'ir'), whole(CURRENT_TARGET, 'asm')],
            'reviewed': False}


CURRENT_TARGET = 'Dispatch'
dispatch_slots = [slot(name, offset, width, align) for name, offset, width, align in [
    ('%owned / R action destination', 56, 13624, 8),
    ('%_4 copied closure environment', 13680, 48, 8),
    ('%_6 Option<T> temporary', 13728, 13624, 8),
    ('%_7 Some input temporary', 27352, 13624, 8),
    ('%self.dbg.spill', 40976, 16, 8),
]]
dispatch_spills = [
    (0, 8, '%_7 address'), (8, 8, '%_6 address'), (16, 8, 'memcpy length 13624'),
    (24, 8, 'incoming x8 child destination'), (32, 8, '%self.0'),
    (40, 8, '%self.1'), (48, 8, '%_4 address'),
]
CURRENT_TARGET = 'Body'
body_slots = [slot(name, offset, width, align) for name, offset, width, align in [
    ('%source', 216, 4, 4), ('%build', 220, 4, 4), ('%session', 224, 4, 4),
    ('%rows', 228, 4, 4), ('%snapshot', 232, 4, 4), ('%_12', 236, 20, 4),
    ('%_13 SetupOutcomeV1', 256, 40, 8), ('%refused', 296, 40, 8),
    ('%_28 setup return payload', 336, 13616, 8), ('%_29', 13952, 40, 8),
    ('%cancellation', 13992, 8, 8), ('%complete_original', 14000, 1264, 8),
    ('%_36 validation budget', 15264, 40, 8), ('%original_carrier', 15304, 1264, 8),
    ('%_40 loader carrier argument', 16568, 1264, 8), ('%correlated', 17832, 1288, 8),
    ('%_42 attempt argument', 19120, 32, 8), ('%_43 original carrier argument', 19152, 1264, 8),
    ('%args', 20416, 424, 8), ('%_46 rows argument', 20840, 4, 4),
    ('%_47 snapshot argument', 20844, 4, 4), ('%_48 Cancellation argument', 20848, 8, 8),
    ('%_49 copied claims', 20856, 256, 1), ('%_52 product budget', 21112, 136, 8),
    ('%complete leaf result', 21248, 13616, 8), ('%_55 correlated argument', 34864, 1288, 8),
    ('%_56 leaf arguments', 36152, 424, 8), ('%_57 loaded payload temporary', 36576, 13616, 8),
    ('%_58 complete move temporary', 50192, 13616, 8),
    ('%_60 correlated drop flag', 63809, 1, 1), ('%_61 cancellation drop flag', 63810, 1, 1),
    ('%_62 snapshot drop flag', 63811, 1, 1), ('%_63 rows drop flag', 63812, 1, 1),
    ('%_64 session drop flag', 63813, 1, 1), ('%_65 build drop flag', 63814, 1, 1),
    ('%_66 source drop flag', 63815, 1, 1),
    ('%fixture.dbg.spill', 63816, 8, 8), ('%expected.dbg.spill', 63824, 8, 8),
    ('%root.dbg.spill', 63832, 8, 8), ('%binding.dbg.spill', 63840, 8, 8),
    ('%source.dbg.spill', 63852, 4, 4), ('%build.dbg.spill', 63856, 4, 4),
    ('%session.dbg.spill', 63860, 4, 4), ('%rows.dbg.spill', 63864, 4, 4),
    ('%snapshot.dbg.spill', 63868, 4, 4), ('%0 exception record', 63872, 16, 8),
]]
body_spills = [
    (0, 8, '%_58 address'), (8, 8, '%_57 address'), (16, 8, 'memcpy length 13616'),
    (24, 8, '%args address'), (32, 8, '%_55 address'), (40, 8, '%_56 address'),
    (48, 8, 'Instant return i64'), (60, 4, 'Instant return i32'),
    (64, 8, '%_42 address'), (72, 8, '%_43 address'), (80, 8, '%_40 address'),
    (92, 4, 'source outgoing register spill'), (96, 4, 'build outgoing register spill'),
    (100, 4, 'session outgoing register spill'), (104, 8, '%_36 address'),
    (112, 8, '%cancellation address'), (120, 8, 'Cancellation default result'),
    (128, 8, '%refused address'), (136, 8, '%_29 address'), (144, 8, 'memcpy length40'),
    (152, 8, '%_28 address'), (160, 8, '%_42 base alias used for local offsets'),
    (168, 8, 'incoming x8 admitted outcome destination'), (176, 8, '%attempt'),
    (184, 8, '%expected'), (192, 8, 'drop-flag base E_B-111'),
    (200, 8, '%fixture'), (208, 8, '%root'),
]


def spill_rows(rows, frame):
    return [{'final_sp_offset': offset, 'entry_sp_offset': offset - frame, 'capacity_bytes': width,
             'purpose': name, 'reviewed': False} for offset, width, name in rows]


def alloca_rows(target):
    result = []
    for number, line in enumerate(texts[target, 'ir'].decode().splitlines(), 1):
        if ' = alloca ' in line:
            result.append({'declaration': line.strip(), 'evidence': lines(target, 'ir', number)})
    return result


def call_inventory(target, kind):
    result = []
    block = 'start'
    last_label = None
    parts = texts[target, kind].decode().splitlines()
    for index, line in enumerate(parts):
        trimmed = line.strip()
        if trimmed.endswith(':') and not trimmed.startswith(';'):
            last_label = trimmed[:-1]
        if kind == 'ir':
            if ':' in line and not line.startswith(' ') and not line.startswith(';'):
                block = line.split(':')[0]
            if ('call ' not in trimmed and 'invoke ' not in trimmed) or trimmed.startswith(';'):
                continue
            if trimmed.startswith('#'):
                continue
            continuation = parts[index + 1].strip() if 'invoke ' in trimmed else None
            entry = {'block': block, 'instruction': trimmed, 'continuation': continuation}
            evidence_last = index + 2 if continuation else index + 1
        else:
            if not trimmed.startswith('bl\t'):
                continue
            entry = {'last_text_label': last_label, 'instruction': trimmed}
            evidence_last = index + 1
        entry.update(evidence=lines(target, kind, index + 1, evidence_last),
                     external_peak_bytes=None, destruction_complete=False, reviewed=False)
        if target == 'Dispatch' and ('run_one_admitted_fixture_v10Bb_' in trimmed):
            entry['destination'] = 'Closure (mapped frontier target; deeper obligations retained)'
        else:
            entry['destination'] = 'outside this two-function ownership lane'
        result.append(entry)
    return result


def cfg_inventory(target):
    result = []
    for kind in ('ir', 'asm'):
        block = None
        for number, line in enumerate(texts[target, kind].decode().splitlines(), 1):
            trimmed = line.strip()
            if kind == 'ir' and line and not line.startswith((' ', ';', '}')) and ':' in line:
                block = line.split(':')[0]
            if kind == 'asm' and trimmed.startswith('LBB') and trimmed.endswith(':'):
                block = trimmed[:-1]
            if (kind == 'ir' and trimmed.startswith(('br ', 'ret ', 'resume ', 'unreachable', 'to label '))) or (
                    kind == 'asm' and (trimmed.startswith(('b\t', 'b.', 'cbz\t', 'tbnz\t')) or trimmed == 'ret')):
                result.append({'kind': kind, 'block': block, 'instruction': trimmed,
                               'evidence': lines(target, kind, number)})
    return result


def explicit_sp_path(pages, tail, restored):
    result = [{'before': 0, 'delta': -32, 'after': -32,
               'argument': 'preindexed saved-state push'}]
    sp = -32
    for iteration in range(1, pages + 1):
        result.append({'before': sp, 'delta': -4096, 'after': sp - 4096,
                       'argument': 'finite native probe loop iteration' + str(iteration)})
        sp -= 4096
    result.append({'before': sp, 'delta': -tail, 'after': sp - tail,
                   'argument': 'native tail decrement'})
    sp -= tail
    if restored:
        for delta, reason in [(pages * 4096, 'native epilogue page increment'),
                              (tail, 'native epilogue tail increment'),
                              (32, 'postindexed saved-state restore')]:
            result.append({'before': sp, 'delta': delta, 'after': sp + delta, 'argument': reason})
            sp += delta
    return result


scope = {
    'status': 'UNREVIEWED_FINITE_ALTERNATE_CONFIGURATION_GEOMETRY_FACTS',
    'reviewed': False, 'local_geometry_only': True, 'complete_capacity_accepted': False,
    'numeric_union': None, 'whole_capacity': None, 'prices': None, 'root_funding': None,
    'runtime_admission_accepted': False, 'original_capture_qualified': False, 'GA_accepted': False,
    'source146_tree_sha256': before['source146_tree_sha256'],
    'alternate_option': '-C link-dead-code=yes', 'runtime_admission': 'WholeQuotePending',
    'raw_pair_bytes': sum(map(len, raw_pair.values())),
    'inherited_toolchain': 'rustc 1.99.0 b940084d7eb6a299eb4bfeb8e34901bc051e7ac4; LLVM 23.1.1; aarch64-apple-darwin',
    'tools_queried_for_versions': False,
    'whole_function_evidence': {target: {kind: whole(target, kind) for kind in ('ir', 'asm')}
                                for target in ('Dispatch', 'Body')},
    'exception_table': {'artifact': 'asm', 'begin': exception['byte_begin'], 'end': exception['byte_end'],
                        'sha256': exception['span_sha256']},
}

dispatch = {
    **scope, 'target': 'Dispatch', 'entry_base': 'E_D = DispatchEntrySP',
    'symbol': targets['Dispatch']['symbol'],
    'frame': {
        'native_reserved_bytes_candidate': 41024, 'final_sp': 'E_D-41024', 'frame_pointer': 'E_D-16',
        'derivation': '32 saved-state bytes + 10 actual iterations of4096-byte decrement/probe +32-byte final decrement.',
        'prologue_evidence': lines('Dispatch', 'asm', 5, 23),
        'normal_epilogue_evidence': needle('Dispatch', 'asm', '\tadd\tsp, sp, #10, lsl #12'),
        'all_sp_mutations': [{'line': n, 'instruction': text.strip(), 'evidence': lines('Dispatch', 'asm', n)}
                             for n, text in enumerate(texts['Dispatch', 'asm'].decode().splitlines(), 1)
                             if text.strip().startswith(('stp\tx28, x27, [sp, #-32]!', 'sub\tsp, sp,', 'add\tsp, sp,', 'ldp\tx28, x27, [sp], #32'))],
        'normal_exit_restores_entry_sp': True,
        'normal_signed_sp_path_candidate': explicit_sp_path(10, 32, True),
        'explicit_probe_offsets_entry_sp': [-32 - 4096 * iteration for iteration in range(1, 11)],
        'probe_tail_note': 'The final32-byte decrement has no additional explicit ldr-xzr probe.',
        'language_cleanup_in_this_function': 'No landingpad/invoke/cleanup block; source says unwind does not release charged reservation.',
        'unwind_via_external_calls_complete': False,
        'saved_state': [{'register': reg, 'entry_sp_offset': offset, 'bytes': 8}
                        for reg, offset in [('x28', -32), ('x27', -24), ('x29', -16), ('x30', -8)]],
        'native_slots': dispatch_slots, 'native_spills': spill_rows(dispatch_spills, 41024),
        'unassigned_native_padding_intervals': [],
        'outgoing_stack_parameter_slots_observed': [],
        'outgoing_argument_note': 'Closure x0, sret x8; memcpy x0/x1/x2. Local by-value staging and spills are listed. No extra SP change or stack-passed argument is present in this whole function; external callee frames remain unknown.',
        'reservation_lifetime': 'After prologue through normal epilogue or nonlocal unwind; source moves do not shrink the native reservation.',
        'allocation_sum_used_as_frame_evidence': False,
    },
    'llvm_allocas': alloca_rows('Dispatch'),
    'return_storage': {
        'R': {'bytes': 13624, 'required_alignment': 8, 'known_physical_base_congruence': None,
              'base': 'E_D', 'offset': -40968, 'final_sp_offset': 56,
              'lifetime': 'Physical slot is reserved after prologue; normal complete Body result arrives here through Closure before wrapping; remains allocated until Dispatch relinquishes frame.',
              'callee_sret': 'x8 = finalSP+56 at sole direct Closure bl; incoming Body x8 forwarding belongs to peer lane.'},
        'C': {'bytes': 13640, 'required_alignment': 8, 'known_physical_base_congruence': None,
              'base': 'incoming x8 saved at finalSP+24; Caller mapping required', 'offset': 0,
              'relation_to_R': 'Three explicit13624-byte copies; no address equality/reuse inferred.',
              'construction': ['R %owned -> %_7 (finalSP+27352)', '%_7 -> %_6 (finalSP+13728)',
                               '%_6 -> incoming child sret destination offsets[0,13624)',
                               'self.0 -> C+13624,8 bytes', 'self.1 -> C+13632,8 bytes'],
              'contained_T_extent': [0, 13624], 'reservation_extent': [13624, 13640],
              'coverage_semantics': 'Complete allocated representation capacity; padding or inactive enum bytes need not be initialized.',
              'final_destruction_bound': None},
        'copy_semantics': 'memcpy storage copies retain pointer/backing identities; no new backing allocation or final destruction fact follows.',
        'evidence': [whole('Dispatch', 'ir'), whole('Dispatch', 'asm')],
    },
    'cross_entry_relation_candidate': {'left': 'DispatchEntrySP', 'right': 'ClosureEntrySP',
        'right_minus_left': -41024, 'reviewed': False,
        'argument': 'Sole direct Closure bl occurs at finalSP with no intermediate SP mutation.',
        'evidence': [whole('Dispatch', 'asm')]},
}
write('dispatch-facts.json', dispatch)

body = {
    **scope, 'target': 'Body', 'entry_base': 'E_B = BodyEntrySP', 'symbol': targets['Body']['symbol'],
    'frame': {
        'native_reserved_bytes_candidate': 63920, 'final_sp': 'E_B-63920', 'frame_pointer': 'E_B-16',
        'derivation': '32 saved-state bytes +15 actual iterations of4096-byte decrement/probe +2448-byte final decrement/probe.',
        'prologue_evidence': lines('Body', 'asm', 7, 26),
        'normal_exit': 'LBB4876_22 ret restores SP by61440 +2448 +32 =63920.',
        'all_sp_mutations': [{'line': n, 'instruction': text.strip(), 'evidence': lines('Body', 'asm', n)}
                             for n, text in enumerate(texts['Body', 'asm'].decode().splitlines(), 1)
                             if text.strip().startswith(('stp\tx28, x27, [sp, #-32]!', 'sub\tsp, sp,', 'add\tsp, sp,', 'ldp\tx28, x27, [sp], #32'))],
        'normal_exit_restores_entry_sp': True,
        'normal_signed_sp_path_candidate': explicit_sp_path(15, 2448, True),
        'cleanup_and_terminate_signed_sp_path_candidate': explicit_sp_path(15, 2448, False),
        'explicit_probe_offsets_entry_sp': [-32 - 4096 * iteration for iteration in range(1, 16)] + [-63920],
        'complete_native_all_exit_restoration_claimed': False,
        'cleanup_exit': 'LBB4876_36 calls __Unwind_Resume while SP=E_B-63920; no local epilogue before it. CFI is retained, but no unwinder execution or restoration proof is supplied.',
        'terminate_exit': 'LBB4876_23 calls panic_in_cleanup with SP=E_B-63920 and no local epilogue; noreturn outgoing/termination obligation remains.',
        'saved_state': [{'register': reg, 'entry_sp_offset': offset, 'bytes': 8}
                        for reg, offset in [('x28', -32), ('x27', -24), ('x29', -16), ('x30', -8)]],
        'native_slots': body_slots, 'native_spills': spill_rows(body_spills, 63920),
        'unassigned_native_padding_intervals_final_sp': [[56, 60], [88, 92], [63808, 63809], [63848, 63852]],
        'exception_record_internal_padding_final_sp': [63884, 63888],
        'outgoing_stack_parameter_slots_observed': [],
        'outgoing_argument_note': 'Direct callees use x0..x4 and x8 sret; all by-value argument/result storage listed as local native slots. No call-site SP adjustments or separate stack-passed parameters occur in the complete body. Callee/probe fault/unwind handling peaks remain unbounded.',
        'reservation_lifetime': 'Same full local reservation on every internal normal/cleanup block after prologue; normal epilogue restores it. Cleanup/termination hands off externally with reservation active.',
        'allocation_sum_used_as_frame_evidence': False,
    },
    'llvm_allocas': alloca_rows('Body'),
    'admitted_return': {
        'bytes': 13624, 'required_alignment': 8, 'known_physical_base_congruence': None,
        'destination': 'incoming x8, saved at finalSP+168, loaded for both normal-return copies',
        'local_alloca_13624_exists': False,
        'setup_refused_path': ['_13(finalSP+256) -> refused(+296),40 bytes',
            'refused -> _29(+13952),40 bytes', '_29 -> _28(+336)+8,40 bytes',
            'i64 -1 -> _28+0', '_28 -> sret[0,13616),13616-byte memcpy',
            'root pointer -> sret+13616,8 bytes', 'branch to shared LBB4876_22 normal epilogue'],
        'loaded_path': ['callee run_fixture_once writes %complete(finalSP+21248),13616-byte sret',
            '%complete -> %_58(+50192),13616 bytes', '%_58 -> %_57(+36576),13616 bytes',
            '%_57 -> sret[0,13616),13616 bytes', 'root pointer -> sret+13616,8 bytes',
            'clear all drop flags; shared normal epilogue'],
        'normal_return_sites_in_IR': 1, 'incoming_normal_constructions': ['bb3 setup refusal', 'bb12 loaded'],
        'sret_address_stable': 'The saved incoming pointer(finalSP+168) is not overwritten; each construction loads it; no sret PHI/cast/rebase appears.',
        'coverage_semantics': 'The required complete13624-byte representation is13616-byte payload capacity plus8-byte root. Setup initializes a discriminant and active refusal fields, then copies full payload capacity; no claim that inactive/padding bytes are initialized.',
        'backing_aliases': 'Copied carriers retain original pointer/descriptor identities. Physical backing capacities and healthy final destruction are unknown.',
        'evidence': [whole('Body', 'ir'), whole('Body', 'asm')],
    },
    'cleanup_state_machine': {
        'flagbase': 'E_B-111 = finalSP+63809',
        'flags_by_offset': {'0': 'correlated', '1': 'cancellation', '2': 'snapshot', '3': 'rows',
                            '4': 'session', '5': 'build', '6': 'source'},
        'landingpads': {'cleanup': 'bb28 snapshot-first ownership checks',
                       'cleanup6': 'bb26 cancellation then original File ownership checks',
                       'cleanup7': 'bb14 Cancellation temp, bb15 snapshot temp, bb16 rows temp, then correlated/remaining ownership checks',
                       'cleanup8': 'bb24 correlated flag then cancellation and original File flags',
                       'terminate': 'panic_in_cleanup for a second unwind while cleanup drop runs'},
        'conditional_drop_order': ['correlated if flag0', 'Cancellation if flag1', 'snapshot if flag2',
                                   'rows if flag3', 'session if flag4', 'build if flag5', 'source if flag6',
                                   'resume original exception'],
        'exception_record': {'offset': 'finalSP+63872', 'capacity_bytes': 16,
                             'pointer_bytes': 8, 'selector_bytes': 4,
                             'note': 'All four cleanup landingpads save x0 and low32 x1 here; final resume reloads exception pointer.'},
        'counterfactual_branch': 'Generated SetupOutcome recheck/drop branch bb22 is retained without claiming it is reachable in normal File execution.',
        'source_destruction_continuation': 'initial_profile_v1.rs884..889 lies outside this function/frontier and remains unqualified.',
        'evidence': [whole('Body', 'ir'), whole('Body', 'asm'), scope['exception_table']],
    },
}
write('body-facts.json', body)

peer_dir = ROOT / 'verification/swift-retained-geometry-caller-closure'
peer_seal_raw = (peer_dir / 'seal.json').read_bytes()
assert sha(peer_seal_raw) == '31c93475b603342a50d943d8050ff43cdcfe932703bd56fb10f8785b7c09f964'
peer_seal = json.loads(peer_seal_raw)
peer_facts_raw = (peer_dir / 'facts.json').read_bytes()
peer_fact_pin = next(row for row in peer_seal['members'] if row['path'] == 'facts.json')
assert len(peer_facts_raw) == peer_fact_pin['bytes'] and sha(peer_facts_raw) == peer_fact_pin['sha256']
peer = json.loads(peer_facts_raw)
assert peer['Caller']['fixed_reservation_bytes'] == 14000
assert peer['Caller']['child_C']['entry_sp_offset'] == -13840
assert peer['Closure']['fixed_reservation_bytes'] == 48
assert peer['Closure']['R_forwarding']['state'] == 'candidate_resolved_same_pointer'
write('cross-lane-candidate-join.json', {
    **scope,
    'peer_seal': {'path': 'verification/swift-retained-geometry-caller-closure/seal.json',
                  'bytes': len(peer_seal_raw), 'sha256': sha(peer_seal_raw)},
    'peer_facts': {'path': 'verification/swift-retained-geometry-caller-closure/facts.json',
                   'bytes': len(peer_facts_raw), 'sha256': sha(peer_facts_raw)},
    'peer_interpretations_independently_reviewed': False,
    'entry_base_relations_candidates': [
        {'left': 'CallerEntrySP', 'right': 'DispatchEntrySP', 'right_minus_left': -14000,
         'source': 'peer Caller complete function/call-site mapping', 'reviewed': False},
        {'left': 'DispatchEntrySP', 'right': 'ClosureEntrySP', 'right_minus_left': -41024,
         'source': 'this lane sole direct Closure call at finalSP', 'reviewed': False},
        {'left': 'ClosureEntrySP', 'right': 'BodyEntrySP', 'right_minus_left': -48,
         'source': 'peer Closure complete function/call-site mapping', 'reviewed': False},
    ],
    'composed_coordinates_candidates': {
        'BodyEntrySP_minus_DispatchEntrySP': -41072,
        'BodyEntrySP_minus_CallerEntrySP': -55072,
        'R_minus_DispatchEntrySP': -40968,
        'R_minus_BodyEntrySP': 104,
        'C_minus_CallerEntrySP': -13840,
        'argument': 'On this exact counterfactual admitted-success chain, R belongs to the still-active Dispatch frame104 bytes above Body entry, and C belongs to the still-active Caller frame. These are signed coordinate compositions from emitted call sites; no union/peak or physical congruence is inferred.',
    },
    'return_pointer_candidate': 'Dispatch x8=E_D-40968 to Closure; peer Closure leaves x8/%_0 unchanged for Body; Body saves incomingx8 and writes both complete normal representations to it.',
    'closure_capture_copy_candidate': 'Peer Caller x2 points to E_C-200,48 bytes. Dispatch copies all48 bytes to E_D-27344 and passes that local copy to Closure.',
    'child_and_outer': 'Peer Caller C=E_C-13840,13640 bytes; Dispatch incomingx8 writes there; Caller copies13640 to incoming external O. O arena/rebase/relations stay unknown.',
    'alignment': 'No known base congruence in either lane; all fragment review flags false.',
    'no_frame_addition_as_capacity': True,
})

exception_lines = exception_raw.decode().splitlines()
start = exception_lines.index('Lcst_begin493:') + 1
end = exception_lines.index('Lcst_end493:')
directives = [line.strip() for line in exception_lines[start:end] if line.strip()]
assert len(directives) % 4 == 0
table = []
for at in range(0, len(directives), 4):
    table.append({'start_expression': directives[at], 'length_expression': directives[at + 1],
                  'landingpad_expression': directives[at + 2], 'action': directives[at + 3],
                  'reviewed': False})
write('edges-and-exits.json', {
    **scope, 'native_and_IR_call_inventory': {target: {kind: call_inventory(target, kind)
        for kind in ('ir', 'asm')} for target in ('Dispatch', 'Body')},
    'branch_and_exit_inventory': {target: cfg_inventory(target) for target in ('Dispatch', 'Body')},
    'body_LSDA_text_rows': table,
    'LSDA_interpretation': 'Zero landingpad means this table supplies no local handler; it does not mean no unwind/transitive peak. Action1 routes cleanup-drop unwinds to panic_in_cleanup. Raw whole table is frozen independently of these candidate readings.',
    'external_obligations': [
        'Every emitted _memcpy call: implementation/frame/probe/stack peak remains unknown.',
        'original_root_v1 and setup_files_once_v1: deeper frames, acquisition/error/cleanup/OS obligations unknown.',
        'Cancellation::default: Arc/allocator/OS backing capacity and final destruction unknown.',
        'load_selected_retained_profile_v1: loader, VM, validation, allocation, error and executable backing graph unknown.',
        'retain_complete_v1 and correlate_admitted_loader_v1: deeper storage, original proof/error and ownership graphs unknown.',
        'copy_claims_v1 and Instant::now: deeper frames, OS/clock behavior, claims/output storage unknown.',
        'run_fixture_once_v1: leaf, setup/pre-scope failure/refusal/results and nested engine/VM peaks unknown.',
        'SetupOutcome, OwnedCorrelationOutcome, Cancellation and File drop_glue: transitive drop/unwind behavior and healthy OS retirement unknown.',
        'panic_in_cleanup, __Unwind_Resume, rust_eh_personality: termination/unwinder/runtime restoration and deeper peaks unknown.',
        'Inline page probes have finite explicit local decrements; guard fault/OS/probe handling is not bounded by the local reservation.',
        'No normal-return local fact qualifies subsequent admitted-child destruction continuation.',
    ],
})

verifier = (ROOT / 'verification/swift-root-bound-dispatch-physical-evidence-v2/source/region_certificate.py').read_text()
assert "'capture_plan_sha256':'bed9476b169810452ac0932605784125365f57c897d1e3bf74cd9eaa6ebb8184'" in verifier
assert "'argv_sha256':'4022ae1057439fe5ae31d18675a884b2dc3e56f317a8ddced08bfb163a410aaa'" in verifier
write('verifier-readiness.json', {
    **scope, 'executable_verifier_input_prepared': False,
    'reason': 'Existing v2 hard-pins original capture plan/argv and closed binding grammar; alternate link-dead-code capture cannot truthfully satisfy it unchanged. No invocation/import/synthetic substitution is selected.',
    'actual_alternate_capture_plan_sha256': '15413684daf6815fbc9773c7fecf669f035768116524e567a841bd571c3f31c8',
    'actual_alternate_argv_sha256': '799f61fd0bff3d5eba3849b784e7bc7b699a5ee84a2a814f298f407befb28e75',
    'original_v2_capture_plan_sha256': 'bed9476b169810452ac0932605784125365f57c897d1e3bf74cd9eaa6ebb8184',
    'original_v2_argv_sha256': '4022ae1057439fe5ae31d18675a884b2dc3e56f317a8ddced08bfb163a410aaa',
    'non_executable_arena_fragments': [
        {'id': 'A_Dispatch', 'base': 'DispatchEntrySP', 'entry_min': -41024, 'entry_max': 0,
         'rebase': 41024, 'reviewed_rebase': False, 'physical_alignment': None,
         'evidence': [whole('Dispatch', 'asm')]},
        {'id': 'A_Body', 'base': 'BodyEntrySP', 'entry_min': -63920, 'entry_max': 0,
         'rebase': 63920, 'reviewed_rebase': False, 'physical_alignment': None,
         'evidence': [whole('Body', 'asm')]},
    ],
    'missing_before_any_numeric_local_union': [
        'Separately reviewed alternate-binding adapter/schema retaining exact diagnostic scope, custody and source146 pins.',
        'Independent semantic review and external trusted root approval of complete combined four-target candidate map.',
        'Physical base congruence is null; required IR alignment8 and EntrySP names do not prove base alignment. Signed rebases normalize coordinates only.',
        'Caller/Closure lane facts must be joined with actual call-site SP and x8 forwarding, without treating peer messages as sealed artifact approval.',
        'Unknown relation to an incoming external destination stays unknown until actual caller evidence establishes its offset/extent.',
        'Body unwind/terminate exits are outgoing at reservedSP and do not fit a complete explicit restore-to-entry path by fabricating a +63920 step.',
        'Fixed role schema cannot silently omit three distinct Dispatch13624-byte stages and Body local13616-byte copies; containing frame includes those slots once.',
    ],
    'backing_obligations': [{'key': key, 'capacity_bytes': None, 'destruction_complete': False,
        'conditional_source_obligation': True, 'identity_status': 'semantic obligation only; no concrete allocation ID minted'}
        for key in ('acquisition_inputs', 'acquisition_paths', 'p0_binding', 'file0', 'file1', 'file2',
                    'file3', 'file4', 'executable', 'proof', 'error', 'cancellation', 'claims')],
    'backing_transfer_rule': 'Same whole semantic backing obligation survives Body→R→C; memcpy does not clone/mint backing identities, and conditional absence is not zero capacity.',
    'retained_partitions': ['acquisition_operation', 'acquisition_cleanup', 'acquisition_storage', 'P0',
                            'C0', 'C1', 'C2', 'C3', 'C4', 'C5'],
    'prices_and_funding': 'All remain pending; no whole-capacity/quote/grant/refund/durable-root or GA conclusion.',
})

post = []
for name, row in expected.items():
    raw = (ROOT / name).read_bytes()
    actual = {'path': name, 'bytes': len(raw), 'sha256': sha(raw)}
    assert actual == row, name
    post.append(actual)
write('input-pins-after.json', {'schema': 1, 'inputs': sorted(post, key=lambda x: x['path']),
                              'all_before_after_match': True, 'changed': []})
receipt = {
    **scope, 'command': ['python3', '-B', 'verification/swift-retained-geometry-dispatch-body/prepare_facts.py'],
    'cwd': str(ROOT), 'python_interpreter_information': sys.version,
    'python_tool_before_after_pin': tool_before,
    'preparer_source_sha256_before_after': preparer_before,
    'execution_seconds': time.monotonic() - START, 'alarm_seconds': 50, 'command_ceiling_seconds': 55,
    'input_pin_count': len(expected), 'all_before_after_hashes_match': True,
    'whole_ir_and_assembly_functions_rechecked': 4, 'whole_Body_exception_table_rechecked': True,
    'source146_preserved': True, 'raw_pair_copied': False, 'derived_output_ceiling_bytes': MAX_DERIVED,
    'compiler_invocations': 0, 'verifier_imports_or_invocations': 0, 'model_or_test_invocations': 0,
    'native_or_UI_invocations': 0, 'version_commands': 0, 'process_probes': 0,
    'subprocesses_spawned_by_preparer': 0, 'owned_native_instances_started': 0,
    'cleanup': 'No native/capture/process work started; no runtime cleanup owed. Other projects untouched.',
    'global_metadata_or_product_changes': False, 'commit_or_push': False,
    'native_checks': 'Paused/unrun and pending, not a pass.',
}
assert {'path': sys.executable, 'bytes': Path(sys.executable).stat().st_size,
        'sha256': sha(Path(sys.executable).read_bytes())} == tool_before
assert sha(Path(__file__).read_bytes()) == preparer_before
assert (peer_dir / 'seal.json').read_bytes() == peer_seal_raw
assert (peer_dir / 'facts.json').read_bytes() == peer_facts_raw
receipt['peer_seal_and_facts_before_after_equal'] = True
write('preparation-receipt.json', receipt)
summary = {'status': scope['status'], 'inputs_unchanged': len(expected),
    'complete_function_spans_rechecked': 4, 'raw_pair_bytes': scope['raw_pair_bytes'],
    'dispatch_native_reservation_candidate': 41024, 'body_native_reservation_candidate': 63920,
    'numeric_union': None, 'complete_capacity_accepted': False, 'verifier_executed': False}
(OUT / 'preparation.stdout').write_text(json.dumps(summary, sort_keys=True) + '\n')
members = []
for path in sorted(OUT.iterdir()):
    if path.name == 'seal.json':
        continue
    assert path.is_file()
    raw = path.read_bytes()
    members.append({'path': path.name, 'bytes': len(raw), 'sha256': sha(raw)})
assert sum(row['bytes'] for row in members) < MAX_DERIVED
write('seal.json', {**scope, 'members': members, 'member_bytes': sum(row['bytes'] for row in members),
                   'tree_sha256_canonical_compact_JSON': sha(json.dumps(members, sort_keys=True, separators=(',', ':')).encode())})
assert sum(path.stat().st_size for path in OUT.iterdir()) < MAX_DERIVED
print(json.dumps(summary, sort_keys=True))
