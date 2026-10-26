#!/usr/bin/env python3
"""Independent read-only source/component audit; never imports the producer."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCER = ROOT / 'verification/swift-cache-state-g6-complete'
SOURCE = ROOT / 'verification/swift-semantic-adapter-root-review/clear128-anonymous-proposal/cache_state.rs'
SOURCE_SHA = '0ab577c36f9836539181ba5156bdfbc7764ea065266e68d94b431da5fdb47ea8'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def info(path):
    raw = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(raw), 'sha256': sha(raw)}

def read_json(path):
    return json.loads(path.read_text())

def write(name, obj):
    (HERE / name).write_text(json.dumps(obj, indent=2) + '\n')

@dataclass(frozen=True)
class Cost:
    scalar: int = 0
    copy: int = 0
    def __add__(self, other):
        return Cost(self.scalar + other.scalar, self.copy + other.copy)
    def __mul__(self, n):
        return Cost(self.scalar * n, self.copy * n)
    def row(self):
        return {'scalars': self.scalar, 'copies': self.copy,
                'scalar_blocks': (self.scalar + 15) // 16,
                'groups': (self.scalar + 15) // 16 + self.copy}

# These are independent component formulas derived from the selected model and
# Rust source. They are not obtained by importing/executing producer ledger.py.
# A literal/local edge costs1; binary costs operands+primitive+result edge;
# scalar fixed-array Index costs20+index expression; p.q field projection adds2.
WORD = 1
W = 20 + WORD
Q = W + 2
FIELD = 3
REGION = 3 + FIELD
ARRAY_SLICE = 6
SLICE_SLICE = 5
THIN = 2
RANGE_ARRAY_FIXED = 2 + 25
RANGE_SLICE_FIXED = 2 + 26
RANGE_SLICE_AT8 = 1 + (1 + 1 + 2) + 26
COPY_TAIL = Cost(5 + 2, 1)
UNIT_FN = 3
ST_BODY = Cost(RANGE_SLICE_AT8 + 3 + 3 + 7 + UNIT_FN, 1) + COPY_TAIL
ST = Cost(ARRAY_SLICE + 1 + 1 + 1) + ST_BODY
SQ = Cost(THIN + 1 + 1 + 1 + ARRAY_SLICE + 7 + 1 + 1 + UNIT_FN) + ST_BODY
LD_BODY = Cost(RANGE_SLICE_AT8 + 24 + 2 + 6, 1)
LD = Cost(ARRAY_SLICE + 1 + 1) + LD_BODY
CQ = Cost(THIN + 1 + 1 + ARRAY_SLICE + 7 + 1 + 2) + LD_BODY
ROW = Cost(SLICE_SLICE + 1 + 1 + 1 + SLICE_SLICE + 18 + 1 + 2) + LD_BODY
DIRECT = Cost(RANGE_ARRAY_FIXED + RANGE_SLICE_FIXED + 3 + 3) + COPY_TAIL
# Existing within has two receiver edges. Required six-edge coercion adds4.
WITHIN_FROZEN = Cost(39, 1)
WITHIN_AMENDED = Cost(39 - THIN + ARRAY_SLICE, 1)
PIN_GUARD = (W + 1 + 2) + (1 + FIELD + 2) + (Q + FIELD + 2) + 2 + 2
PIN_COMPUTE = LD + Cost(1 + 1 + 11, 1) + Cost(PIN_GUARD)

TEMPLATE_FORMULAS = {
    'st Candidate/value': (ST, 'array->slice6 + at1 + n1 + entry1 + st-body54; LE-return8 and destination8 are distinct'),
    'sq literal/value': (SQ, 'thin2+i1+n1+entry1 + nested slice6+offset7+n1+entry1+st-body54 + unit3'),
    'ld Candidate/literal': (LD, 'slice6+at1+entry1 + range31+first_chunk/expect24+deref2+conversion/return6; full8 array argument'),
    'cq literal': (CQ, 'thin2+i1+entry1 + nested slice6+offset7+entry1+ld-body63 + return2'),
    'rr literal field': (ROW, 'outer8 + nested slice5+Region/offset18+entry1+ld-body63+return2'),
    'literal Candidate->arena8': (DIRECT, 'slice range28 + receiver3 + array range27 + source3 + copy-tail7'),
    'literal arena->Candidate8': (DIRECT, 'array range27 + receiver3 + slice range28 + source3 + copy-tail7'),
    'copy_within64': (WITHIN_FROZEN, 'frozen39+copy1; required complete Candidate->slice receiver replaces thin2 with6, yielding43+copy1'),
    'indexed record word': (Cost(W), 'index literal1+borrow/receive/guards/address/return/deref20'),
}

def st(n=1, at=1, arena=False):
    return Cost((SLICE_SLICE if arena else ARRAY_SLICE) + at + n + 1) + ST_BODY

def sq(n=1):
    return SQ + Cost(n - 1)

def final_prefix(kind, variant):
    stage_zero = kind in (11, 12, 13)
    # 3 indexed-coordinate sq; stage match/index+dispatch+selected scalar;
    # stage sq; two conditional argument sq. Event2 has one extra24+2 guard.
    return sq(W) * 3 + Cost(W + 1 + 1 + (26 if kind == 2 else 0)) + sq() + sq(7 if stage_zero else 27) * 2

def stage(kind, variant, stop='', amended=False):
    within = WITHIN_AMENDED if amended else WITHIN_FROZEN
    if kind == 1:
        return sq() * 9
    if kind == 2:
        return sq() * 2
    if kind in (3, 9, 10, 13) or kind == 4 and variant == 'reuse':
        return Cost()
    if kind == 4:
        # i0 st95; i1..3 st104 each; i4 st81. Loop setup12,
        # 5 Some/advance/guard/body-control20 each, final None12, result2.
        return Cost(12 + 20 * 5 + 12 + 2 + 95 + 104 * 3 + 81 + 3, 2 * 5 + 6)
    if kind == 5:
        result = Cost(93, 1) + st(W) + Cost(3) + sq(W) + Cost(4)
        if stop == 'prefix-refusal':
            return result
        # Four final scalar stores; destination choose has bool guard3+value1;
        # feasibility conversion has received bool1+entry/conversion/return4.
        return result + sq() * 4 + sq(4) + sq(5)
    if kind == 6:
        return sq()
    if kind == 7:
        return within + st() + Cost(1) + sq(4) + sq(24) + sq(29)
    if kind == 8:
        return sq(29) + sq()
    if kind == 11:
        if variant == 'built':
            result = within + st() + st(W) * 3 + sq(4)
            result += Cost(1 + W + (9 if stop == 'sum-refusal' else 11), 1)
            if stop == 'sum-refusal':
                return result
            result += sq()
        else:
            result = Cost(93, 1)
        result += LD + Cost(1 + 1 + (9 if stop == 'pin-overflow' else 11), 1)
        if stop == 'pin-overflow':
            return result
        result += Cost(PIN_GUARD)
        if stop == 'pin-refusal':
            return result
        # Eight st bodies: pins, w4, cast-slot, w12, w3, w3, w4, w5.
        return result + st() + st(W) * 6 + st(3) + Cost(3 + 1) + sq(Q + 1 + 2) * 2
    if kind == 12:
        # Pin reset:6 st75, loop fixed26 +6*20,7 complete Option16.
        return Cost(93, 1) + st(W) + Cost(6 * 75 + 26 + 6 * 20, 6 * 2 + 7) + Cost(W * 2) + sq(Q + 1 + 2)
    raise AssertionError((kind, variant, stop))

CLEANUP = Cost(26 + 16 * (43 + 130) + 12 * 68 + 7, 16 + 12)
PRIVATE_CLEANUP_ATOMIC = Cost(9 + 2)
PRIVATE_CLEANUP_CORRUPTION = Cost(19)

def final(kind, variant, private=False, fail=False):
    result = final_prefix(kind, variant)
    resident = kind in (7, 11, 12)
    pin = kind in (11, 12)
    plan = kind == 5 or kind == 4 and variant != 'reuse'
    if fail:
        assert resident and private
        return result + Cost(6 + 14 + 71 + 19, 1)
    result += Cost(3 * 6 + 85 * (resident + pin + plan), resident + pin + plan)
    if resident:
        result += Cost(19 if private else 8)
    result += DIRECT * 12 + Cost(W + 1 + 2 + 2)
    if kind == 6:
        result += st(W, REGION + (1 + 1 + 2) + 2, arena=True)
    return result

def paths(amended=False):
    result = {}
    specs = [(1,''),(2,'lookup-new'),(2,'lookup-hit'),(3,'reuse'),(3,'collision'),(4,'reuse'),(4,'collision'),
             (5,'feasible'),(5,'infeasible'),(6,''),(7,''),(8,''),(9,''),(10,''),(11,'hit'),(11,'built'),(12,''),(13,'')]
    for kind, variant in specs:
        stem = f'event{kind}' + ('.' + variant if variant else '')
        for mode in ('production','instrumented-success','instrumented-cleanup-failure'):
            private = mode != 'production'
            result[stem + '.' + mode] = stage(kind, variant, amended=amended) + final(kind, variant, private) + CLEANUP
            if private:
                result[stem + '.' + mode] += PRIVATE_CLEANUP_ATOMIC
            if mode == 'instrumented-cleanup-failure':
                result[stem + '.' + mode] += PRIVATE_CLEANUP_CORRUPTION
    refusals = [(5,'feasible','prefix-refusal'),(11,'built','sum-refusal'),(11,'built','pin-overflow'),
                (11,'built','pin-refusal'),(11,'hit','pin-overflow'),(11,'hit','pin-refusal')]
    for kind, variant, stop in refusals:
        for private in (False, True):
            name = f'event{kind}.{variant}.{stop}' + ('.instrumented' if private else '')
            result[name] = stage(kind, variant, stop, amended) + CLEANUP + (PRIVATE_CLEANUP_ATOMIC if private else Cost())
    for kind, variant in ((7,''),(11,'hit'),(11,'built'),(12,'')):
        result[f'event{kind}.{variant}.private-commit-failure'] = stage(kind, variant, amended=amended) + final(kind, variant, True, True) + CLEANUP + PRIVATE_CLEANUP_ATOMIC
    result['prestage-refusal'] = CLEANUP
    result['zero-debit-guard-after-loan'] = CLEANUP
    result['invalid-length-cleanup'] = Cost(26 + 7)
    return result

def verify_seal(rel, expected_sha, expected_count, expected_bytes):
    path = ROOT / rel
    assert info(path)['sha256'] == expected_sha, rel
    manifest = read_json(path)
    members = manifest['members']
    assert len(members) == expected_count
    assert sum(row['bytes'] for row in members) == expected_bytes
    for row in members:
        assert info(ROOT / row['path']) == row, row['path']
    return {'seal': info(path), 'member_count': len(members), 'member_bytes': sum(row['bytes'] for row in members)}

def main():
    inputs = [verify_seal(*x) for x in [
        ('verification/swift-cache-state-g6-complete/seal.json', 'c806b2967e37978403641c0172f3d70013b1e74c0d28128236f26fb618812597', 14, 565517),
        ('verification/swift-cache-state-implementation/correction-3/candidate-repo-seal.json', '7044a00eef658d8c729e7301c0923ed193ec405c6c6009989a964b3159bad12f', 570, 15387058),
        ('verification/swift-cache-state-g6-independent-review/seal.json', '21343e183de35954dc39f74c27dbca01afed0f91793fac9d3d68ae1682a199e9', 12, 79478),
        ('verification/swift-semantic-adapter-root-review/clear128-anonymous-proposal/seal.json', 'ed0fa3abe9394bf4f7edfca280d80de7f89011a5eb6abb0db5742a13cf8cabb2', 5, 55421),
    ]]
    assert info(SOURCE)['sha256'] == SOURCE_SHA
    assert (ROOT / 'verification/swift-cache-state-implementation/correction-3/source/library/cache_state.rs').read_bytes() == SOURCE.read_bytes()
    source = SOURCE.read_text().splitlines()
    assert source[595].strip() == 'c.copy_within(1944..2008, 1536);'
    assert source[641].strip() == 'c.copy_within(1944..2008, 1536);'
    assert [i+1 for i, line in enumerate(source) if 452 <= i+1 <= 773 and 'c.copy_within(' in line] == [596,642]
    assert all(source[780+i].strip() == f'c[{128*i}..{128*(i+1)}].copy_from_slice(&[0u8; 128]);' for i in range(16))
    assert sum('if !cleanup(' in line for line in source) == 1
    assert 'type Candidate2048 = [u8; 2048];' in (ROOT/'verification/swift-cache-state-implementation/correction-3/source/library/envelope.rs').read_text()

    templates = read_json(PRODUCER / 'operation-templates.json')['templates']
    checked_templates = []
    for row in templates:
        independent, formula = TEMPLATE_FORMULAS[row['name']]
        assert (row['scalars'], row['copies']) == (independent.scalar, independent.copy), row['name']
        assert sum(op['kind'] == 'scalar' for op in row['operations']) == independent.scalar
        assert sum(op['kind'] == 'copy' for op in row['operations']) == independent.copy
        checked_templates.append({'name':row['name'], **independent.row(), 'independent_formula':formula})
    frozen_paths = paths()
    amended_paths = paths(True)
    published = read_json(PRODUCER / 'paths.json')['paths']
    segments = json.loads(gzip.decompress((PRODUCER/'path-segments.json.gz').read_bytes()))['paths']
    assert len(frozen_paths) == len(published) == len(segments) == 73
    assert set(frozen_paths) == {row['path'] for row in published}
    checked_paths = []
    for row, detail in zip(published, segments):
        name = row['path']
        cost = frozen_paths[name]
        assert row['actual_G6_scalars'] == cost.scalar, (name, cost, row)
        assert row['actual_G6_payload_groups'] == cost.copy, name
        assert row['actual_G6_scalar_blocks'] == cost.row()['scalar_blocks'], name
        assert row['actual_G6_groups'] == cost.row()['groups'], name
        assert detail['path'] == name
        actual_segments = [s for s in detail['segments'] if s['owner'] == 'G6']
        assert sum(s['scalars'] for s in actual_segments) == cost.scalar
        assert sum(s['copies'] for s in actual_segments) == cost.copy
        amended = amended_paths[name]
        within_segments = [s for s in actual_segments if s['line'] in (596,642)]
        assert len(within_segments) <= 1
        assert amended.scalar - cost.scalar == 4 * len(within_segments)
        assert amended.copy == cost.copy
        assert amended.row()['groups'] <= 640
        checked_paths.append({'path':name, 'frozen':cost.row(), 'receiver_corrected':amended.row(), 'affected_source_lines':[s['line'] for s in within_segments]})

    extremal = json.loads(gzip.decompress((PRODUCER/'extremal-operations.json.gz').read_bytes()))
    ops = extremal['operations']
    assert len({op['id'] for op in ops}) == len(ops)
    actual = [op for op in ops if op['owner'] == 'G6']
    scalar = [op for op in actual if op['kind'] == 'scalar']
    copies = [op for op in actual if op['kind'] == 'copy']
    assert Cost(len(scalar),len(copies)) == frozen_paths[extremal['path']]
    assert all(0 < op['bytes'] <= 128 for op in copies)
    blocks = [scalar[i:i+16] for i in range(0,len(scalar),16)]
    assert all(1 <= len(b) <= 16 for b in blocks)
    assert [op for b in blocks for op in b] == scalar
    detail = next(p for p in segments if p['path'] == extremal['path'])
    for segment in detail['segments']:
        part = ops[segment['first_operation']:segment['first_operation']+segment['operation_count']]
        assert sha(json.dumps(part,separators=(',',':')).encode()) == segment['ordered_operations_sha256']
        assert all(op['owner'] == segment['owner'] for op in part)
    max_production = max((n for n in amended_paths if n.endswith('.production')), key=lambda n:amended_paths[n].row()['groups'])
    max_all = max(amended_paths, key=lambda n:amended_paths[n].row()['groups'])
    supplemental_controls = {
        n + '.also-cleanup-corruption': c + PRIVATE_CLEANUP_CORRUPTION
        for n, c in amended_paths.items()
        if n.endswith('.private-commit-failure') or n.endswith('.instrumented')
    }
    assert all(c.row()['groups'] <= amended_paths[max_all].row()['groups'] for c in supplemental_controls.values())
    result = {
        'status':'independent audit found finite copy_within receiver omission; producer exact completeness not accepted',
        'source_sha256':SOURCE_SHA, 'source_only':True, 'producer_module_imports_or_executions':0,
        'runtime_compiler_native_capture_process_inventory_executions':0,
        'verified_custody':inputs, 'independent_templates':checked_templates,
        'paths_compared_to_independent_source_recipes':len(checked_paths),
        'frozen_production':frozen_paths[max_production].row(),
        'receiver_corrected_production':{'path':max_production,**amended_paths[max_production].row()},
        'receiver_corrected_all_paths':{'path':max_all,**amended_paths[max_all].row()},
        'supplemental_combined_fault_prefixes':{n:c.row() for n,c in supplemental_controls.items()},
        'corrected_within_template':WITHIN_AMENDED.row(),
        'clear_only':Cost(16*(43+130),16).row(),
        'G6_cap':640, 'cap_overrun_proved':False,
        'root_addendum_selection_required':True, 'all_implementation_and_lifetime_acceptance':False,
        'paths':checked_paths,
    }
    write('results.json', result)
    custody = {'at':datetime.now(timezone.utc).isoformat(), 'command':[sys.executable,'-B',str(Path(__file__).resolve())],
               'python':sys.version, 'platform':platform.platform(),
               'HEAD_context_only':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
               'source':info(SOURCE), 'producer_seal':info(PRODUCER/'seal.json'),
               'binding_prerequisite':info(ROOT/'docs/swift-semantic-adapter-prerequisite.md'),
               'selected_amendment':info(ROOT/'docs/swift-cache-state-clear128-selection.md'),
               'selection':info(ROOT/'verification/swift-semantic-adapter-root-review/clear128-correction3-selection.json'),
               'owned_scope':['verification/swift-cache-state-g6-complete-independent/**'],
               'source_only':True, 'product_compiler_runtime_native_UI_capture_or_process_inventory_executions':0,
               'producer_import_or_execution':False, 'frozen_packet_mutations':False}
    write('custody.json',custody)
    print(json.dumps({k:v for k,v in result.items() if k not in ('paths','verified_custody','independent_templates')},indent=2))

if __name__ == '__main__':
    main()
