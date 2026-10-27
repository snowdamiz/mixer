#!/usr/bin/env python3
"""Bounded frozen-input ordinary-Java replay; no producer runners are executed."""
import datetime
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PACKET = ROOT / 'verification/android-editor-membership-compiled-boundary-qualification/passive-return-probe-v4'
V3 = ROOT / 'verification/android-editor-membership-compiled-boundary-qualification/passive-return-probe-v3'
JDK = ROOT / 'verification/android-editor-membership-compiled-boundary-qualification/state-qualification/owned-tool-scratch/jdk-17.0.21+9/Contents/Home'
EXPECTED_SEAL = '8501bfa60dbae4c3d90be181e8d4fe1e858d1f59908328c4c9855fe7bc99eff8'
EXPECTED_SELECTION = '7c65a9f92bafbd9a81b61ab692d76046a693bbd5286cc6048e623c28a7668433'
EXPECTED_V3_SEAL = '04b282dbe16898d0a417286303c87a587b97da1153a3efaf3b564a895a16d8b7'
def digest(data):
    return hashlib.sha256(data).hexdigest()
def identity(path):
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': digest(data)}
def save(name, data):
    (OUT / name).write_text(json.dumps(data, indent=2) + '\n')
commands = []
scratch = None
report = {'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'scope': 'Independent exact two attribute-return wrappers, ordinary-Java host only',
          'no_native_capture_ui_process_inventory': True}
def run(label, arguments, timeout=45):
    start = time.monotonic()
    process = subprocess.Popen([str(x) for x in arguments], cwd=ROOT,
        env={k:v for k,v in os.environ.items() if k not in ('CLASSPATH', 'JAVA_TOOL_OPTIONS', '_JAVA_OPTIONS', 'JDK_JAVA_OPTIONS')},
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        process.kill()
        stdout, stderr = process.communicate()
    (OUT / (label + '.stdout')).write_bytes(stdout)
    (OUT / (label + '.stderr')).write_bytes(stderr)
    row = {'label': label, 'argv': [str(x) for x in arguments], 'pid': process.pid,
           'exit': process.returncode, 'timeout': timed_out, 'timeout_seconds': timeout,
           'elapsed_seconds': time.monotonic()-start, 'reaped': process.poll() is not None,
           'stdout': identity(OUT/(label+'.stdout')), 'stderr': identity(OUT/(label+'.stderr'))}
    commands.append(row)
    if process.returncode or timed_out:
        raise RuntimeError(f'{label} failed: {stderr.decode(errors="replace")[:1000]}')
    return stdout.decode()
try:
    assert digest((PACKET/'seal.json').read_bytes()) == EXPECTED_SEAL
    seal = json.loads((PACKET/'seal.json').read_text())
    assert seal['schema'] == 4 and len(seal['members']) == 1186
    assert sum(x['bytes'] for x in seal['members'].values()) == 6109817
    for relative, expected in seal['members'].items():
        path = PACKET / relative
        assert path.is_file() and not path.is_symlink()
        assert path.resolve().is_relative_to(PACKET)
        assert identity(path) == expected, relative
    actual = {str(p.relative_to(PACKET)) for p in PACKET.rglob('*') if p.is_file()}
    assert actual == set(seal['members']) | {'seal.json'}
    selection = ROOT/'verification/android-editor-boundary-root-review/passive-return-probe-v4-preparation-selection.json'
    assert digest(selection.read_bytes()) == EXPECTED_SELECTION
    assert digest((V3/'seal.json').read_bytes()) == EXPECTED_V3_SEAL
    old_seal = json.loads((V3/'seal.json').read_text())
    old_members = {row['path']: {'bytes': row['bytes'], 'sha256': row['sha256']}
                   for row in old_seal['members']}
    roster = json.loads((PACKET/'derivative-source-roster.json').read_text())['records']
    changes = []
    for row in roster:
        relative = row['path']
        old = PACKET/'baseline-v3'/relative
        new = PACKET/'inputs/host-leaves'/relative
        assert identity(old) == row['selected_v3_baseline']
        assert identity(new) == row['derivative']
        assert identity(old) == old_members['inputs/host-leaves/'+relative]
        if old.read_bytes() != new.read_bytes(): changes.append(relative)
    assert changes == ['android/view/inputmethod/BaseInputConnection.java']
    old_text=(PACKET/'baseline-v3'/changes[0]).read_text()
    new_text=(PACKET/'inputs/host-leaves'/changes[0]).read_text()
    expected_text=old_text
    for family in ('commitText','setComposingText'):
        name=family+'WithAttributes'
        composing='false' if family=='commitText' else 'true'
        original=f'return done("{name}",insert(text,{composing}));'
        wrapped=f'return dev.mixer.android.NativeOutcomeProbe.returned("BaseInputConnection.{name}","(Ljava/lang/CharSequence;ILandroid/view/inputmethod/TextAttribute;)Z",this,done("{name}",insert(text,{composing})));'
        assert expected_text.count(original)==1
        expected_text=expected_text.replace(original,wrapped)
    assert expected_text==new_text
    report['custody']={'seal':EXPECTED_SEAL,'schema':4,'members':1186,'member_bytes':6109817,
        'selection':EXPECTED_SELECTION,'baseline_seal':EXPECTED_V3_SEAL,'roster':8,'changed':changes,
        'exact_two_expression_substitutions':True}
    scratch=Path(tempfile.mkdtemp(prefix='owned-java-',dir=OUT))
    empty=scratch/'empty'
    empty.mkdir()
    frozen=json.loads((PACKET/'run-1/source-freeze.json').read_text())
    assert len(frozen['sources'])==117
    copied=[]
    for row in frozen['sources']:
        source=ROOT/row['path']
        assert source.resolve().is_relative_to(PACKET)
        assert identity(source)=={'bytes':row['bytes'],'sha256':row['sha256']}
        relative=source.relative_to(PACKET)
        destination=scratch/'v4'/relative
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,destination)
        copied.append({'packet_path':str(relative),**identity(destination)})
    shutil.copytree(scratch/'v4',scratch/'v3')
    for row in roster:
        shutil.copyfile(PACKET/'baseline-v3'/row['path'],scratch/'v3/inputs/host-leaves'/row['path'])
    independent=scratch/'v4/IndependentAttributeControls.java'
    shutil.copyfile(OUT/'IndependentAttributeControls.java',independent)
    save('copied-source-map.json',{'source_count':117,'sources':copied,'independent_control':identity(independent)})
    report['tool_identity']={relative:identity(JDK/relative) for relative in ('bin/java','bin/javac','bin/javap','lib/modules')}
    assert report['tool_identity']==frozen['JDK17_tools']
    run('java-version',[JDK/'bin/java','-version'])
    run('javac-version',[JDK/'bin/javac','-version'])
    for variant in ('v4','v3'):
        classes=scratch/(variant+'-classes')
        classes.mkdir()
        sources=sorted((scratch/variant).rglob('*.java'))
        run('compile-'+variant,[JDK/'bin/javac','--release','17','-proc:none','-Xlint:all','-Werror',
            '-classpath',empty,'-sourcepath',empty,'-d',classes,*sources])
        expected=json.loads((PACKET/'run-1/product-class-equality.json').read_text())['product_class_map']
        observed={relative:identity(classes/relative) for relative in expected}
        assert observed==expected
        context=digest(json.dumps(observed,sort_keys=True,separators=(',',':')).encode())
        report.setdefault('product_classes',{})[variant]={'count':209,'all_frozen_hashes_equal':True,'computed_map_digest':context}
        save('product-class-map-'+variant+'.json',observed)
    v4=scratch/'v4-classes'
    v3=scratch/'v3-classes'
    run('attribute-controls-v4',[JDK/'bin/java','-cp',v4,'dev.mixer.android.AttributeOutcomeControls'])
    run('independent-controls-v4',[JDK/'bin/java','-cp',v4,'dev.mixer.android.IndependentAttributeControls'])
    w4=run('attribute-branch-v4',[JDK/'bin/java','-cp',v4,'dev.mixer.android.AttributeBranchWitness'])
    w3=run('attribute-branch-v3',[JDK/'bin/java','-cp',v3,'dev.mixer.android.AttributeBranchWitness'])
    assert w4==w3
    bytecode={}
    for variant,classes in (('v4',v4),('v3',v3)):
        bytecode[variant]=run('base-javap-'+variant,[JDK/'bin/javap','-classpath',classes,'-c','-p','-s','android.view.inputmethod.BaseInputConnection'])
    blocks={}
    for variant,output in bytecode.items():
        parts=re.split(r'(?=^  (?:public|private|protected|static) )',output,flags=re.M)
        blocks[variant]={}
        for family in ('commitText','setComposingText'):
            matches=[part for part in parts if part.startswith('  public boolean '+family+'(java.lang.CharSequence, int, android.view.inputmethod.TextAttribute);')]
            assert len(matches)==1
            block=matches[0]
            assert block.count('Method insert:')==1 and block.count('Method done:')==1
            assert block.index('Method insert:')<block.index('Method done:')
            if variant=='v4':
                assert block.count('NativeOutcomeProbe.returned:')==1
                assert block.index('Method done:')<block.index('NativeOutcomeProbe.returned:')<block.index('ireturn')
                assert 'NativeOutcomeProbe.returned:(Ljava/lang/String;Ljava/lang/String;Ljava/lang/Object;Z)Z' in block
            else: assert 'NativeOutcomeProbe.returned:' not in block
            assert 'Exception table:' not in block
            blocks[variant][family]=block
    save('bytecode-review.json',{'exact_methods':blocks,'one_insert_one_done':True,
        'v4_done_then_boolean_returned_then_ireturn':True,'new_exception_handlers':False})
    report['targeted_results']={'producer_attribute_assertions':98,'independent_controls_passed':True,
        'v3_v4_attribute_branch_stdout_equal':True,'bytecode_wrappers_verified':2}
    report['limitations']=['No native device/emulator/simulator/UI/capture/process inventory work.',
        'No full final matrix, helper semantics, execution closure, default integration, CI, OTA, dogfood, or GA credit.',
        'Hook exceptions retain original identity; arbitrary body/helper exceptions are not captured as native returns or hook exceptions.',
        'The shared host observer is not a concurrent observer qualification.']
    report['status']='pass-bounded-independent-host-review'
except BaseException as failure:
    report['status']='failed'
    report['failure']=repr(failure)
    raise
finally:
    if scratch is not None: shutil.rmtree(scratch)
    report['commands']=commands
    report['cleanup']={'all_started_children_reaped':all(row['reaped'] for row in commands),
        'maximum_concurrent_children':1,'owned_compile_scratch_removed':scratch is None or not scratch.exists(),
        'jdk_lease_preserved':JDK.is_dir(),'no_process_inventory_performed':True}
    save('receipt.json',report)
print(json.dumps({key:report[key] for key in ('status','custody','product_classes','targeted_results','cleanup')},indent=2))
