#!/usr/bin/env python3
"""Independent hostile inputs against released v3 checker; no product acceptance."""
import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
RELEASED = HERE / 'interface-v3'
PINNED_SEAL = '2941189d35873edceff76e2f4b7ff3bf960632d19a869a5e9faf54e4df7a671f'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def raw(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()

def write(path, value):
    path.write_bytes(raw(value))

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def run(argv, cwd, expected=0):
    p = subprocess.run([str(x) for x in argv], cwd=cwd, capture_output=True,
                       text=True, timeout=60, env={**os.environ, 'PYTHONDONTWRITEBYTECODE':'1'})
    if p.returncode != expected:
        raise AssertionError({'argv':[str(x) for x in argv], 'exit':p.returncode,
                              'stdout':p.stdout, 'stderr':p.stderr})
    return {'command':[str(x) for x in argv], 'exit':p.returncode,
            'stdout':p.stdout, 'stderr':p.stderr}

def integrity():
    seal_path = RELEASED / 'seal.json'
    assert sha(seal_path.read_bytes()) == PINNED_SEAL
    seal = json.loads(seal_path.read_bytes())
    actual = {p.relative_to(RELEASED).as_posix() for p in RELEASED.rglob('*') if p.is_file()}
    assert actual == {r['path'] for r in seal['members']} | {'seal.json'}
    for row in seal['members']:
        data = (RELEASED / row['path']).read_bytes()
        assert len(data) == row['bytes'] and sha(data) == row['sha256']
    return {'seal_sha256':PINNED_SEAL, 'members':len(seal['members']),
            'member_bytes':sum(r['bytes'] for r in seal['members'])}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--jdk-home', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    custody = integrity()
    scratch = HERE / 'control-scratch'
    assert not scratch.exists(), 'fresh scratch required'
    scratch.mkdir()
    log = []
    try:
        # Actual CLI must refuse draft before absent source/map/class/result inputs.
        missing = scratch / 'missing'
        command = [sys.executable, '-B', RELEASED/'check_qualified_matrix.py',
                   '--policy', RELEASED/'semantic-policy-draft.json', '--map', missing,
                   '--source-root', missing, '--classes', missing, '--matrix', missing]
        result = run(command, HERE, 2)
        refused = json.loads(result['stdout'])
        assert refused['reason'] == 'semantic policy remains draft; no qualified producer/map accepted'
        log.append({'name':'actual-cli-draft-must-refuse-before-source-access', **result})

        # Re-run producer's shape/context controls separately; their result scope stays synthetic.
        for name in ('test_structured_rows.py', 'test_context_authority.py'):
            result = run([sys.executable, '-B', RELEASED/name], HERE)
            assert json.loads(result['stdout'])['all_rejected'] is True
            log.append({'name':'released-'+name, **result})

        # Independently construct a full, typed certificate; do not import producer test fixtures.
        sr = load_module('independent_released_rows', RELEASED/'structured_rows.py')
        caller = {'class':'example/Subject','class_sha256':'a'*64,'source_sha256':'b'*64,
                  'method':'left','descriptor':'()Ljava/lang/String;','bci':1,
                  'opcode':'invokevirtual', 'callee':{'owner':'java/lang/Object',
                  'name':'toString','descriptor':'()Ljava/lang/String;'}}
        policy = {'mandatory_subjects':['membership','field-preservation','lifecycle-loss'],
                  'boundaries':[{'id':'scope','required_states':['healthy','fatal'],
                  'subjects':['membership','field-preservation','lifecycle-loss']}]}
        context = {'boundaries':[{'id':'scope','required_states':['healthy','fatal'],
                                 'caller':copy.deepcopy(caller)}]}
        outcome = {'original_result':{'kind':'boolean','value':True},
                   'gate_state':{'terminal':False,'draw_allowed':True,'input_allowed':True},
                   'retirement_state':{'attempt_revoked':False,'target_disposition':'active'},
                   'count_state':{'busy':0,'field_preservations':0,'native_calls':1},
                   'cleanup_state':{'target_close_calls':0,'busy':False,'pending':False},
                   'fatal_state':{'class':None,'identity':None,'escaped_exact':False}}
        matrix = {'status':'passed','rows':[]}
        for state in ('healthy','fatal'):
            matrix['rows'].append({'boundary_id':'scope','state':state,'status':'passed',
                'evidence_kind':'executed-host','hit':1,'caller':copy.deepcopy(caller),
                'original_authority':{'mode':'TRANSACTION','fence_identity':'fence-original',
                'token_identity':'token-original','record_identity':'record-original',
                'view_identity':'view-original','editable_identity':'editable-original',
                'binding_identity':'binding-original','attempt_identity':'attempt-original',
                'target_identity':'target-original'},'receiver_identity':'view-original',
                'production_frames':[{k:caller[k] for k in ('class','method','descriptor','bci')}],
                'native_event_jni_sequence':[{'method':'Object.toString','phase':'entry',
                                            'frame_index':0,'receiver_identity':'view-original'}],
                'cleanup_fatal_disposition':{'cleanup_attempted':False,'busy_balanced':True,
                                           'first_fatal_identity':None,'pending_reason':None},
                'expected':copy.deepcopy(outcome),'observed':copy.deepcopy(outcome),
                'unsupported_successor_authority':False})
        assert sr.validate(policy, context, matrix) == {'boundaries':1,'states':2}
        controls = [
            ('state-and-matching-row-shrink', lambda c,m:(c['boundaries'][0]['required_states'].pop(),m['rows'].pop())),
            ('active-boundary-and-all-rows-shrink', lambda c,m:(c['boundaries'].clear(),m['rows'].clear())),
            ('coherent-row-only-neighbor', lambda c,m:m['rows'][0]['caller'].update(bci=4)),
            ('boolean-as-hit', lambda c,m:m['rows'][0].update(hit=True)),
            ('boolean-as-frame-bci', lambda c,m:m['rows'][0]['production_frames'][0].update(bci=True)),
            ('boolean-as-sequence-index', lambda c,m:m['rows'][0]['native_event_jni_sequence'][0].update(frame_index=True)),
            ('noninteger-as-native-count', lambda c,m:m['rows'][0]['observed']['count_state'].update(native_calls=1.0)),
            ('missing-exact-authority-field', lambda c,m:m['rows'][0]['original_authority'].pop('editable_identity')),
            ('untyped-authority-string', lambda c,m:m['rows'][0].update(original_authority='declared-reviewed')),
            ('missing-captured-token', lambda c,m:m['rows'][0]['original_authority'].update(token_identity=None)),
            ('missing-fence', lambda c,m:m['rows'][0]['original_authority'].update(fence_identity=None)),
            ('opaque-cleanup-string', lambda c,m:m['rows'][0].update(cleanup_fatal_disposition='balanced')),
            ('empty-event-sequence', lambda c,m:m['rows'][0].update(native_event_jni_sequence=[])),
            ('source-only-receipt', lambda c,m:m['rows'][0].update(evidence_kind='source-only')),
            ('missing-observed', lambda c,m:m['rows'][0].pop('observed')),
            ('result-difference', lambda c,m:m['rows'][0]['observed']['original_result'].update(value=False)),
            ('unsupported-successor', lambda c,m:m['rows'][0].update(unsupported_successor_authority=True)),
            ('duplicate-state-row', lambda c,m:m['rows'].append(copy.deepcopy(m['rows'][0]))),
            ('invented-state', lambda c,m:m['rows'][0].update(state='unreviewed')),
            ('caller-not-in-production-frames', lambda c,m:m['rows'][0]['production_frames'][0].update(method='neighbor')),
        ]
        for name, mutation in controls:
            c,m = copy.deepcopy(context),copy.deepcopy(matrix)
            mutation(c,m)
            try:
                sr.validate(policy,c,m)
            except (ValueError,TypeError) as exc:
                log.append({'name':name,'status':'refused','reason':str(exc)})
            else:
                raise AssertionError('typed hostile input accepted: '+name)

        # Exact binding/reference source closure is tested at actual CLI entry without root selection.
        for filename, suffix in [('approved-policy-binding.json','binding'),
                                 ('reference-obligations.json','reference')]:
            closure = scratch / suffix
            closure.mkdir()
            for leaf in ('check_qualified_matrix.py','classfile.py','structured_rows.py',
                         'approved-policy-binding.json','reference-obligations.json'):
                shutil.copyfile(RELEASED/leaf, closure/leaf)
            (closure/filename).write_bytes((closure/filename).read_bytes()+b' ')
            argv = command.copy(); argv[2] = closure/'check_qualified_matrix.py'
            result = run(argv,HERE,2)
            reason = json.loads(result['stdout'])['reason']
            assert reason.startswith('altered '),reason
            log.append({'name':'actual-cli-adjacent-'+suffix+'-file-drift',**result})

        if args.jdk_home:
            exercise_real_checker(args.jdk_home, scratch, caller, policy, context, matrix, log)
        result = {'scope':'Independent preaccess evidence-integrity controls only; synthetic trusted fixture is not approved product policy/context or product behavior',
                  'custody':custody,'controls':log,'all_controls_passed':True,
                  'actual_checker_compiled_fixture_exercised':bool(args.jdk_home),
                  'product_policy_accepted':False,'full_matrix_accepted':False,
                  'native_runtime_executed':False,'native_OTA_GA_authorized':False}
        write(args.output,result)
        print(json.dumps({'controls':len(log),'all_controls_passed':True,'output':str(args.output)}))
    finally:
        shutil.rmtree(scratch)

def exercise_real_checker(jdk, scratch, caller, policy, context, matrix, log):
    # Exercise the actual checker, with changed pins isolated to this explicitly synthetic trust root.
    fixture = scratch/'actual-checker'; fixture.mkdir()
    (fixture/'empty-sourcepath').mkdir()
    (fixture/'empty-classpath').mkdir()
    sources = fixture/'sources';sources.mkdir()
    classes = fixture/'classes';classes.mkdir()
    source = sources/'Subject.java'
    source.write_text('package example; public class Subject { public String left(Object o) { return o.toString(); } public String right(Object o) { return o.toString(); } }\n')
    for binary in ('java','javac','javap'):
        executable=jdk/'bin'/binary
        log.append({'name':'fixture-'+binary+'-version',
                    'executable_sha256':sha(executable.read_bytes()),
                    'executable_bytes':executable.stat().st_size,
                    **run([executable,'-version'],fixture)})
    log.append({'name':'compile-independent-synthetic-fixture',**run([jdk/'bin'/'javac','--release','17','-Xlint:all','-Werror','-proc:none','-sourcepath',str(fixture/'empty-sourcepath'),'-classpath',str(fixture/'empty-classpath'),'-d',classes,source],fixture)})
    for leaf in ('check_qualified_matrix.py','classfile.py','structured_rows.py'):
        shutil.copyfile(RELEASED/leaf,fixture/leaf)
    cf = load_module('independent_released_classfile',fixture/'classfile.py')
    parsed = cf.parse((classes/'example/Subject.class').read_bytes())
    write(fixture/'parsed-class.json',parsed)
    disassembly=run([jdk/'bin'/'javap','-c','-p','-s',classes/'example/Subject.class'],fixture)
    assert disassembly['stdout'].count('1: invokevirtual')==2
    assert disassembly['stdout'].count('java/lang/Object.toString:()Ljava/lang/String;')==2
    log.append({'name':'independent-javap-actual-instruction-comparison',**disassembly})
    def fileid(p):
        b=p.read_bytes();return {'bytes':len(b),'sha256':sha(b)}
    source_map={'Subject.java':fileid(source)}
    class_map={'example/Subject.class':fileid(classes/'example/Subject.class')}
    def bind(method):
        m=next(x for x in parsed['methods'] if x['name']==method)
        ins=next(i for i in m['instructions'] if i.get('target',{}).get('name')=='toString')
        return {'class':parsed['class'],'class_sha256':class_map['example/Subject.class']['sha256'],
                'source_sha256':source_map['Subject.java']['sha256'],'method':m['name'],
                'descriptor':m['descriptor'],'bci':ins['bci'],'opcode':ins['mnemonic'],'callee':ins['target']}
    bound=bind('left');neighbor=bind('right');assert bound!=neighbor
    for b in (bound,neighbor):
        assert b['bci']==1 and b['opcode']=='invokevirtual'
        assert b['descriptor']=='(Ljava/lang/Object;)Ljava/lang/String;'
        assert b['callee']=={'owner':'java/lang/Object','name':'toString','descriptor':'()Ljava/lang/String;'}
    policy=copy.deepcopy(policy)
    policy.update(schema='mixer.android.semantic-boundary-policy.v2',source_pair='mixer.android-source-pair.5',
        product_sources=source_map,exact_input_connection_descriptors=['fixture%d()V'%x for x in range(38)],
        historical_dispositions=[{'historical_id':'historical-%d'%x} for x in range(189)],
        v1_baselines=['v1-%d'%x for x in range(5)])
    context=copy.deepcopy(context);context['boundaries'][0]['caller']=bound
    contextid=sha(json.dumps({'source_map':source_map,'class_map':class_map},sort_keys=True,separators=(',',':')).encode())
    write(fixture/'policy.json',policy);policyhash=sha((fixture/'policy.json').read_bytes())
    context.update(schema='mixer.android.compiled-boundary-context.v2',context_id=contextid,
        class_map=class_map,policy_sha256=policyhash,identity_review_status='reviewed-exact-context')
    matrix=copy.deepcopy(matrix)
    matrix.update(schema='mixer.android.compiled-boundary-results.v2',context_id=contextid,
        policy_sha256=policyhash,class_map=class_map,product_sources=source_map)
    for row in matrix['rows']:
        row['caller']=copy.deepcopy(bound)
        row['production_frames']=[{k:bound[k] for k in ('class','method','descriptor','bci')}]
    write(fixture/'context.json',context);write(fixture/'matrix.json',matrix)
    binding={'policy_sha256':policyhash,'root_selected':True,
             'approved_context_map_hashes':{contextid:sha((fixture/'context.json').read_bytes())}}
    reference={'exact16_source_map':source_map,'exact38_descriptors':policy['exact_input_connection_descriptors'],
               'historical189_ids':[x['historical_id'] for x in policy['historical_dispositions']]}
    write(fixture/'approved-policy-binding.json',binding);write(fixture/'reference-obligations.json',reference)
    checker=fixture/'check_qualified_matrix.py';text=checker.read_text()
    original_binding=sha((RELEASED/'approved-policy-binding.json').read_bytes())
    original_reference=sha((RELEASED/'reference-obligations.json').read_bytes())
    text=text.replace(original_binding,sha((fixture/'approved-policy-binding.json').read_bytes()))
    text=text.replace(original_reference,sha((fixture/'reference-obligations.json').read_bytes()))
    checker.write_text(text)
    command=[sys.executable,'-B',checker,'--policy',fixture/'policy.json','--map',fixture/'context.json',
             '--source-root',sources,'--classes',classes,'--matrix',fixture/'matrix.json']
    result=run(command,fixture);assert json.loads(result['stdout'])['status']=='passed-exact-host-qualified-matrix'
    log.append({'name':'actual-checker-synthetic-trusted-positive',**result})
    substitutions=[
        ('real-neighbor-and-all-matching-rows',lambda c,m:(c['boundaries'][0].update(caller=neighbor),[r.update(caller=neighbor,production_frames=[{k:neighbor[k] for k in ('class','method','descriptor','bci')}]) for r in m['rows']])),
        ('same-context-state-and-row-shrink',lambda c,m:(c['boundaries'][0]['required_states'].pop(),m['rows'].pop())),
        ('same-context-boundary-and-row-shrink',lambda c,m:(c['boundaries'].clear(),m['rows'].clear())),
        ('self-review-string-only',lambda c,m:c.update(identity_review_status='self-reviewed')),
        ('foreign-compiler-context',lambda c,m:c.update(context_id='f'*64)),
    ]
    for name,mutation in substitutions:
        c,m=copy.deepcopy(context),copy.deepcopy(matrix);mutation(c,m)
        write(fixture/'context.json',c);write(fixture/'matrix.json',m)
        result=run(command,fixture,2)
        assert 'foreign exact context-map hash' in json.loads(result['stdout'])['reason']
        log.append({'name':'actual-checker-'+name,**result})
    write(fixture/'context.json',context);write(fixture/'matrix.json',matrix)
    # A certificate cannot authorize another compiled output or substitute an actual instruction.
    for name,mutation in [
        ('foreign-result-context',lambda m:m.update(context_id='0'*64)),
        ('wrong-result-caller-and-frame',lambda m:[r.update(caller=neighbor,production_frames=[{k:neighbor[k] for k in ('class','method','descriptor','bci')}]) for r in m['rows']]),
        ('incomplete-certificate',lambda m:m['rows'].pop()),
    ]:
        m=copy.deepcopy(matrix);mutation(m);write(fixture/'matrix.json',m)
        result=run(command,fixture,2)
        log.append({'name':'actual-checker-'+name,**result})
    # Adjacent reference/binding reauthorizing coherent drift still fails checker source pins.
    for filename in ('reference-obligations.json','approved-policy-binding.json'):
        p=fixture/filename;before=p.read_bytes();p.write_bytes(before+b' ')
        result=run(command,fixture,2)
        assert json.loads(result['stdout'])['reason'].startswith('altered ')
        log.append({'name':'actual-checker-source-pin-'+filename,**result});p.write_bytes(before)
    write(fixture/'matrix.json',matrix)
    destination=HERE/'retained-synthetic-control-fixture'
    if destination.exists():
        fresh={p.relative_to(fixture).as_posix():p.read_bytes() for p in fixture.rglob('*') if p.is_file()}
        retained={p.relative_to(destination).as_posix():p.read_bytes() for p in destination.rglob('*')
                  if p.is_file() and p.name!='SCOPE.json'}
        assert fresh==retained,'retained synthetic fixture differs; use fresh owned review copy'
    else:
        shutil.copytree(fixture,destination)
        write(destination/'SCOPE.json',{'synthetic_fixture_only':True,'production_policy_context_authority':False,
            'reason':'Source pins changed only inside this synthetic trust fixture to exercise actual checker control flow.'})

if __name__=='__main__':
    main()
