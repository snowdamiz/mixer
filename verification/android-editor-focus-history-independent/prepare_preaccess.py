#!/usr/bin/env python3
"""Admit only named frozen inputs and typecheck authored controls, never run product."""
from pathlib import Path
import datetime, hashlib, json, os, shutil, subprocess, sys
D=Path(__file__).resolve().parent
ROOT=D.parents[1]
OLD=ROOT/'verification/android-editor-replacement-independent'
CONTRACT=ROOT/'verification/android-editor-boundary-root-review'
def row(path):
    data=path.read_bytes();return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
assert row(OLD/'review-seal.json')['sha256']=='11cd26bbc78f54e48de297b931fab2fcb9becce4d4aa4884d145641f2a615b15'
members={item['path']:item for item in json.loads((OLD/'review-seal.json').read_text())['members']}
inputs=D/'inputs';inputs.mkdir(exist_ok=False)
copies={}
for name,expected in [('focus-history-amendment.md','736476a269fae9a6745fbfbd5413a7ef231f57f9254c3279e41c2921d2088833'),('focus-history-internal-protocol.md','17463b2c5399ccbf9662ee7446c798803cf332adbffb30a0c14d9f6161c432a0'),('focus-history-protocol-selection.json','90a6aad457e38d8db6aa87ce8fdeddb42bc28e67cfb960c7f767ef71881428f8')]:
    path=CONTRACT/name;assert row(path)['sha256']==expected;shutil.copyfile(path,inputs/name);copies[str(path.relative_to(ROOT))]=row(path)
foundation=D/'foundation';foundation.mkdir()
for relative in ['actual-review/independent-controls-6/source/AdditionalReplacementControls.java','actual-review/independent-controls-3/source/ReplacementReviewControls.java','actual-review/independent-controls-3/source/DescriptorClosure.java']:
    source=OLD/relative;assert row(source)=={key:members[relative][key] for key in ['bytes','sha256']};shutil.copyfile(source,foundation/source.name);copies[str(source.relative_to(ROOT))]=row(source)
classpath=OLD/'actual-review/frozen/runs/host-1/classes'
classrows=[]
for path in sorted(classpath.rglob('*.class')):
    relative=str(path.relative_to(OLD));assert row(path)=={key:members[relative][key] for key in ['bytes','sha256']};classrows.append({'path':relative,**row(path)})
(D/'baseline-class-map.json').write_text(json.dumps(classrows,indent=2)+'\n')
java=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home/bin')
expected_tools={'javac':'e9fb09ca9cb259a164a32c9055931a865943d25c66800996183c86e527ca0688','java':'9ef6c1a939343ac850811551a8b88d4b877630ab2c94ac38c541e25ccc8cf0a5'}
for name,expected in expected_tools.items():assert row(java/name)['sha256']==expected
run=D/'typecheck-1';run.mkdir();empty=run/'empty-source';empty.mkdir();classes=run/'classes';classes.mkdir()
env={key:value for key,value in os.environ.items() if key not in {'JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','_JAVA_OPTIONS','CLASSPATH','JAVA_OPTIONS'}}
commands=[]
def command(name,args):
    argv=[str(arg) for arg in args];item={'name':name,'argv':argv,'timeout_seconds':60};commands.append(item)
    child=subprocess.Popen(argv,cwd=D,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    try:out,err=child.communicate(timeout=60)
    except BaseException:
        child.kill();out,err=child.communicate();item['killed_and_reaped']=True;raise
    finally:item['reaped']=child.poll() is not None
    (run/(name+'.stdout')).write_bytes(out);(run/(name+'.stderr')).write_bytes(err);item['exit_code']=child.returncode
    print(name,child.returncode,out.decode(errors='replace').strip(),flush=True);return child.returncode
try:
    command('javac-version',[java/'javac','-version']);command('java-version',[java/'java','-version'])
    result=command('compile',[java/'javac','--release','17','-Xlint:all','-Werror','-proc:none','-sourcepath',empty,'-classpath',classpath,'-d',classes,*sorted(foundation.glob('*.java')),D/'FocusHistoryControls.java'])
finally:
    empty.rmdir()
    receipt={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'argv':sys.argv,'python':sys.version,'scope':'Control compilation only against prior frozen authored host classes; no product method/constructor invoked','commands':commands,'inputs':copies,'baseline_class_count':len(classrows),'tools':{str(java/name):row(java/name) for name in expected_tools},'source':row(D/'FocusHistoryControls.java'),'active_correction_reads_enumerations_or_hashes':0,'candidate_executions':0,'product_executions_in_typecheck':0,'native_UI_capture_or_process_inventory':False,'cleanup':{'children_reaped':all(item['reaped'] for item in commands),'empty_source_removed':not empty.exists(),'compiler_outputs_retained_for_evidence':True},'limitation':'New internal Input methods, FieldPreservation binding and private fields are reflective prospective hooks, not compiled new interfaces or executed claims; exact binding awaits frozen release.'}
    (run/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
sys.exit(result)
