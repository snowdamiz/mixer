#!/usr/bin/env python3
"""Finite correction controls. Never invokes the frozen one-shot runners or rustc."""
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import sys
import time
from datetime import datetime, timezone

OWN = Path(__file__).resolve().parent
REPO = OWN.parents[1]
PRODUCER = REPO / 'verification/swift-guarded-snapshot-export-preparation'
REVIEW = REPO / 'verification/swift-guarded-snapshot-export-contract-independent'
OUT = OWN / 'controls'
PACKETS = [
    ('swift-guarded-snapshot-export-preparation', '7787c8bbd9164ebdd360186f79c5d696739e89d6b08cd2f7cfbc71e9c156a1fe', 639),
    ('swift-guarded-snapshot-export-contract-independent', 'be091218c0c8c47f66c83ac39cded51012c942e7e91d9660b1b25985243401e1', 767),
    ('swift-guarded-snapshot-export-accounting-review', 'c638a996d2fa1f54c62f739758c5219f23439541b249e480b0084d1038112068', 29),
    ('swift-guarded-snapshot-export-binding-review', '7d3faabd2f930d2daac9865f27dbbb3bc9a661097e6a7834584a93d0527b1cf0', 6),
]
ROOT_INPUTS = [
    ('guarded-snapshot-export-correction-selection.json', '9365220136da4af59d1403cf694f3c8108c4f601647c3fe7bf1b4385aff37511'),
    ('guarded-snapshot-export-positive-fixture-amendment.json', '327db1241e13af8b0c68b0c795c1dcba2c8692c9da5bd7dc100b013025c11457'),
    ('guarded-snapshot-export-fixture-inventory-amendment.json', '76a2a3c91c46f401d04bfd51f830b50374c24b0d8cbbd4f5d91b48ab15eda518'),
]
FAILED_FIVE = [
    'bad-memory-minimum-duplicate', 'bad-memory-host-duplicate',
    'bad-table-minimum-duplicate', 'bad-table-max-option-duplicate',
    'bad-runtime-type-count-duplicate',
]


def sha(value):
    return hashlib.sha256(value).hexdigest()


def ref(path):
    return {'path': path.relative_to(REPO).as_posix(),
            'bytes': path.stat().st_size, 'sha256': sha(path.read_bytes())}


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_packet(name, expected, count):
    folder = REPO / 'verification' / name
    seal_path = folder / 'seal.json'
    assert sha(seal_path.read_bytes()) == expected
    seal = json.loads(seal_path.read_text())
    assert seal['member_count'] == count == len(seal['members'])
    actual = sorted(p.relative_to(folder).as_posix() for p in folder.rglob('*')
                    if p.is_file() and p != seal_path)
    assert actual == sorted(r['path'] for r in seal['members'])
    for row in seal['members']:
        p = folder / row['path']
        assert p.stat().st_size == row['bytes'] and sha(p.read_bytes()) == row['sha256'], str(p)
    assert sum(r['bytes'] for r in seal['members']) == seal['bytes']
    if seal.get('tree_digest_algorithm') == 'sha256 of sorted per-member lines: sha256 SPACE decimal-bytes SPACE relative-path LF':
        tree = sha(''.join(r['sha256']+' '+str(r['bytes'])+' '+r['path']+'\n'
                           for r in seal['members']).encode())
    else:
        assert 'tree_digest_algorithm' not in seal
        tree = sha(json.dumps(seal['members'], sort_keys=True, separators=(',', ':')).encode())
    assert tree == seal['tree_sha256']
    return {'seal': ref(seal_path), 'members': count, 'bytes': seal['bytes'],
            'tree_sha256': seal['tree_sha256'], 'all_members_verified': True}


def custody():
    result = {'packets': [verify_packet(*row) for row in PACKETS]}
    result['root_inputs'] = []
    for name, digest in ROOT_INPUTS:
        p = REPO / 'verification/swift-semantic-adapter-root-review' / name
        assert sha(p.read_bytes()) == digest
        result['root_inputs'].append(ref(p))
    manifest = json.loads((PRODUCER / 'inputs/source-manifest.json').read_text())
    assert manifest['member_count'] == len(manifest['members']) == 144
    assert manifest['tree_sha256'] == '9fbdabbc5122f71809483b3b0a0e95a71b9813def61572f366bcebc8ac6d08fb'
    for row in manifest['members']:
        p = PRODUCER / 'inputs/accepted-source/vm' / row['path']
        assert p.stat().st_size == row['bytes'] and sha(p.read_bytes()) == row['sha256']
    result['accepted_source'] = {'manifest': ref(PRODUCER / 'inputs/source-manifest.json'),
                                 'members': 144, 'tree_sha256': manifest['tree_sha256']}
    return result


def command(name, argv, expected=0):
    folder = OUT / 'commands' / name
    folder.mkdir(parents=True)
    started = time.monotonic()
    run = subprocess.run(argv, cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         timeout=30)
    (folder / 'stdout').write_bytes(run.stdout)
    (folder / 'stderr').write_bytes(run.stderr)
    receipt = {'argv': argv, 'cwd': str(REPO), 'exit_code': run.returncode,
               'expected_exit_code': expected, 'expectation_met': run.returncode == expected,
               'elapsed_seconds': time.monotonic() - started,
               'stdout_sha256': sha(run.stdout), 'stderr_sha256': sha(run.stderr),
               'timeout_seconds': 30, 'child_reaped': True}
    write(folder / 'receipt.json', receipt)
    assert receipt['expectation_met']
    return receipt


def parsed(model, data):
    try:
        model.parse(data)
        return {'accepted': True, 'refusal': None}
    except model.Refused as error:
        return {'accepted': False, 'refusal': str(error)}


def migration(model, old):
    before = old.assemble_unverified_fixture()
    after = model.assemble_unverified_fixture()
    changes = [(offset, struct.unpack_from('<Q', before, offset)[0],
                struct.unpack_from('<Q', after, offset)[0])
               for offset in range(0, len(before) - 7, 8)
               if before[offset:offset+8] != after[offset:offset+8]]
    assert changes == [(792,3,64),(1408,2,16777216),(1416,1,8388608)]
    folder = OUT / 'migration'
    folder.mkdir()
    (folder / 'original-synthetic-positive.bin').write_bytes(before)
    (folder / 'migrated-synthetic-positive.bin').write_bytes(after)
    assert parsed(old,before)['accepted'] and not parsed(model,before)['accepted']
    assert parsed(model,after)['accepted']
    controls = []
    for offset, old_word, new_word in changes:
        negative = bytearray(after)
        negative[offset:offset+8] = struct.pack('<Q', old_word)
        path = folder / ('original-disagreement-' + str(offset) + '.bin')
        path.write_bytes(negative)
        value = parsed(model,negative)
        controls.append({'offset':offset,'original':old_word,'migrated':new_word,
                         'fixture':ref(path), **value,
                         'expectation_met':not value['accepted']})
    test_before = (PRODUCER/'test_format_model.py').read_text()
    test_after = (OWN/'test_format_model.py').read_text()
    assert test_after == test_before.replace('self.assertEqual(len(f.DIGESTS),6)',
        'self.assertEqual(len(f.DIGESTS),5); self.assertEqual(len(f.RETAINED_VALUES),6)')
    value = {'root_selected':True,'original_fixture':ref(folder/'original-synthetic-positive.bin'),
             'migrated_fixture':ref(folder/'migrated-synthetic-positive.bin'),
             'word_changes':controls,'original_accepted_by_original_model':True,
             'original_refused_by_corrected_model':True,'migrated_accepted_by_corrected_model':True,
             'test_method_count_unchanged':12,'test_source_changes':'inventory assertion only, root-selected',
             'original_test':ref(PRODUCER/'test_format_model.py'),'corrected_test':ref(OWN/'test_format_model.py')}
    assert all(c['expectation_met'] for c in controls)
    write(OUT / 'migration.json',value)
    return value


def source_controls():
    evidence = json.loads((OWN/'source-equation-evidence.json').read_text())
    for row in evidence['sources']:
        p = REPO/row['path']
        assert sha(p.read_bytes()) == row['sha256']
        actual = '\n'.join(p.read_text().splitlines()[row['line_start']-1:row['line_end']])
        assert actual == row['text']
    roster=json.loads((OWN/'source-roster.json').read_text())
    for source in roster['sources']:
        p=REPO/source['path'];assert sha(p.read_bytes())==source['sha256']
        for fact in source['facts']:
            if fact['line'] is not None:
                assert fact['token'] in p.read_text().splitlines()[fact['line']-1]
    cache=next(s for s in roster['sources'] if s['accepted_member_path']=='src/experimental_swift_reactor/cache.rs')
    prepare=next(f for f in cache['facts'] if f['token']=="pub(crate) fn prepare<'a>(")
    assert prepare['line']==1473 and prepare['status'].startswith('existing')
    contract=(OWN/'contract.md').read_text()
    assert 'one 64-byte Source File identity' in contract
    assert 'one 64-byte executable identity' not in contract
    return {'bounded_source_excerpts':len(evidence['sources']),
            'all_source_roster_facts_checked':True,'existing_prepare_line':1473,
            'existing_wrapper_call_line':138,'actual_loader_bytes_changed':False,
            'actual_loader_first_session_section_role':'Source','expectation_met':True}


def main():
    assert not OUT.exists(), 'one final run per packet; preserve an existing run rather than overwrite'
    OUT.mkdir()
    before = custody()
    write(OWN/'input-custody-before.json', before)
    commands = [command('python-version',[sys.executable,'-B','--version']),
                command('producer-format-methods',[sys.executable,'-B',str(OWN/'test_format_model.py')])]
    model=load('corrected_model',OWN/'format_model.py')
    old=load('frozen_original_model',PRODUCER/'format_model.py')
    independent=load('frozen_independent_controls',REVIEW/'review_controls.py')
    independent.CANDIDATE=OWN
    independent.OUT=OUT/'independent-format'
    independent.GROUPS=[]
    independent.formats()  # Only six data groups; no compilers, adoption or wrapper.
    groups=independent.GROUPS
    assert [g['id'] for g in groups]==['F01','F02','F03','F04','F05','F06']
    assert sum(len(g['subcases']) for g in groups)==26
    assert all(g['expectation_met'] for g in groups)
    write(OUT/'independent-format-result.json',{'groups':groups,'group_count':6,
          'subcase_count':26,'format_function_source':ref(REVIEW/'review_controls.py'),
          'only_formats_function_invoked':True,'fresh_independent_compilers':False})
    five=[]
    old_result=json.loads((REVIEW/'controls-result.json').read_text())
    old_failed=[c for g in old_result['groups'] for c in g['subcases'] if not c['expectation_met']]
    assert [c['name'] for c in old_failed]==FAILED_FIVE
    for name in FAILED_FIVE:
        original=REVIEW/'controls/fixtures'/(name+'.bin')
        replayed=OUT/'independent-format/fixtures'/(name+'.bin')
        data=original.read_bytes()
        assert data==replayed.read_bytes()
        prior=next(c for c in old_failed if c['name']==name)
        assert sha(data)==prior['fixture_sha256']
        baseline=parsed(old,data);corrected=parsed(model,data)
        assert baseline['accepted'] and not corrected['accepted']
        five.append({'name':name,'original':ref(original),'replayed':ref(replayed),
                     'original_failed_expectation_preserved':True,
                     'original_model_result':baseline,'corrected_model_result':corrected,
                     'expectation_met':True})
    write(OUT/'exact-five-regressions.json',{'count':5,'fixtures':five})
    migrated=migration(model,old)
    boundaries=load('correction_boundaries',OWN/'boundary_controls.py').controls(model)
    write(OUT/'boundary-result.json',{'count':len(boundaries),'subcases':boundaries,
                                     'failed':[c['name'] for c in boundaries if not c['expectation_met']]})
    assert all(c['expectation_met'] for c in boundaries)
    source=source_controls()
    write(OUT/'source-result.json',source)
    compiler_refs=[]
    for path in sorted((PRODUCER/'commands/attempt-4').glob('*/receipt.json')):
        value=json.loads(path.read_text())
        if value['name'].startswith(('debug-','optimized-')):
            assert value['expectation_met']
            compiler_refs.append(ref(path))
    assert len(compiler_refs)==28
    compiler_inputs=[ref(p) for p in sorted((PRODUCER/'prototype').glob('*.rs'))]
    compiler_inputs += [ref(p) for p in sorted((PRODUCER/'compile-cases').glob('*.rs'))]
    compiler_inputs += [ref(p) for p in sorted((PRODUCER/'compiler-variants/attempt-4').rglob('*')) if p.is_file()]
    write(OUT/'inherited-compiler-attribution.json',{
        'freshly_compiled':False,'prior_case_count':28,'prior_positive':2,'prior_expected_negative':26,
        'prior_scope':'prototype privacy/signature feasibility, not runtime or exporter behavior',
        'unchanged_exact_inputs_verified_in_original639seal':compiler_inputs,
        'original_receipts':compiler_refs,
        'accepted_source144_unchanged':True,
        'independent_prior_compiler_source':ref(REVIEW/'controls-result.json'),
        'independent_prior_count':{'production_builds':2,'negative_controls':9},
        'independent_prior_compilers_rerun':False})
    after=custody()
    assert before==after
    write(OWN/'input-custody-after.json',after)
    inputs={p.name:sha(p.read_bytes()) for p in sorted(OWN.iterdir()) if p.is_file()
            and p.name in ['run_controls.py','boundary_controls.py','format_model.py','test_format_model.py',
                           'contract.md','source-roster.json','equality-table.json','source-equation-evidence.json']}
    result={'schema':1,'at':datetime.now(timezone.utc).isoformat(),
        'status':'corrected-finite-contract-model-controls-pass-awaiting-independent-review-root-acceptance',
        'command':{'argv':[sys.executable,'-B',str(Path(__file__).resolve())],'cwd':str(REPO)},
        'python':sys.version,'python_executable':str(Path(sys.executable).resolve()),
        'python_executable_sha256':sha(Path(sys.executable).resolve().read_bytes()),
        'source_revision_context':'606c42876855897c315ee279dcd38fabaeb561ad',
        'accepted_source_tree_sha256':before['accepted_source']['tree_sha256'],
        'source_inputs_sha256':inputs,'producer_format_methods_passed':12,
        'fresh_independent_format_groups':6,'fresh_independent_format_subcases':26,
        'exact_five_original_failures_retained_now_refused':5,
        'new_boundary_controls':len(boundaries),'new_boundary_failed':[],
        'original_positive_word_disagreements_retained_as_negatives':3,
        'source_controls':source,'frozen_input_packets_unchanged':True,
        'fresh_compiler_controls':0,'inherited_prototype_compiler_controls':28,
        'fresh_native_checks':0,'product_native_OTA_GA_accepted':False,'GA_gates_verified':0,
        'transfer_bytes':4096,'attempts_per_transfer':32,
        'original300000grant':'unchanged required refusal','historical400000fixture':'unchanged refusal-only',
        'cleanup':{'owned_children_reaped':True,'compiler_products_created':False,
                   'scratch_created':False,'native_UI_capture_process_inventory':False,
                   'frozen_packets_written':False,'bytecode_written':False},
        'pending':['fresh independent correction review and root acceptance','working exporter',
            'separately owned concrete work/deadline/cancellation and storage design',
            'runtime same-owner reads and actual new layouts/admission/consuming cleanup',
            'File close/name/hash custody','semantic context/FSM/full workload','canonical integration',
            'native checks paused','FieldLog separate repository immutable published package',
            'OTA/signing/store/customer/operational/GA']}
    write(OWN/'correction-result.json',result)
    print(json.dumps({'producer_methods':12,'independent_groups':6,'independent_subcases':26,
                      'exact_five_refused':5,'boundary_controls':len(boundaries),
                      'migration_negative_controls':3,'failed':0,'cleanup':result['cleanup']}))


if __name__=='__main__':
    main()
