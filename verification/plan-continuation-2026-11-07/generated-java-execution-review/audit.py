"""Read retained classfiles/receipts and current sources; never execute toolchains."""
import ast
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
BASE=HERE.parent
FIX=BASE/'generated-java-execution-fix'
spec=importlib.util.spec_from_file_location('audited_runner',ROOT/'scripts/ci/check-android-generated-java.py')
M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)
def check(value,message):
    if not value: raise RuntimeError(message)
def read(path): return json.loads(path.read_text())
def binary_members(path):
    data=path.read_bytes()
    check(data[:4]==b'\xca\xfe\xba\xbe','classfile magic')
    count=struct.unpack_from('>H',data,8)[0]
    offset=10;index=1;pool={};members=[]
    sizes={3:4,4:4,5:8,6:8,7:2,8:2,9:4,10:4,11:4,12:4,15:3,16:2,17:4,18:4,19:2,20:2}
    while index<count:
        tag=data[offset];offset+=1
        if tag==1:
            size=struct.unpack_from('>H',data,offset)[0];offset+=2
            pool[index]=(tag,data[offset:offset+size]);offset+=size
        else:
            check(tag in sizes,'unknown binary CP tag')
            pool[index]=(tag,data[offset:offset+sizes[tag]]);offset+=sizes[tag]
            if tag in (9,10,11):members.append(index)
        check(offset<=len(data),'truncated classfile CP')
        index+=2 if tag in (5,6) else 1
    def utf(index):
        tag,raw=pool[index];check(tag==1,'expected UTF8 entry');return raw.decode('utf-8')
    result=[]
    for index in members:
        tag,raw=pool[index]
        owner,nt=struct.unpack('>HH',raw)
        owner_tag,owner_raw=pool[owner];nt_tag,nt_raw=pool[nt]
        check(owner_tag==7 and nt_tag==12,'bad member links')
        name,desc=struct.unpack('>HH',nt_raw)
        result.append({'class_file':str(path),'constant_pool_index':'#'+str(index),
          'kind':{9:'Fieldref',10:'Methodref',11:'InterfaceMethodref'}[tag],
          'semantic_member':utf(struct.unpack('>H',owner_raw)[0])+'.'+utf(name)+':'+utf(desc)})
    return result

runner=ROOT/'scripts/ci/check-android-generated-java.py'
tests=ROOT/'scripts/ci/tests/test_android_generated_java_runner.py'
current=runner.read_bytes()
old_literal=b"profile['id'] == 'mixer.android-source-pair.7'"
new_literal=b"profile['id'] == 'mixer.android-source-pair.8'"
check(current.count(new_literal)==1,'pair8 guard count')
check(hashlib.sha256(current.replace(new_literal,old_literal)).hexdigest()=='67e571ab863b552175a1ad947da453fea0692b9c7bf47353feff997889846d71','unexpected change beyond literal')
check(M.identity(tests)['sha256']=='99f5436faccd5ce74d8e7fb9d14f13a4be1a1ab2f3d83021da10732860625630','test identity changed')
prior=(FIX/'check-android-generated-java.py.before').read_text()
text=current.decode()
check(prior.split('        finally:\n',1)[1].split('\ndef member_references',1)[0]==text.split('        finally:\n',1)[1].split('\ndef member_references',1)[0],'command cleanup changed')
check(prior.split('    finally:\n        terminal =',1)[1]==text.split('    finally:\n        terminal =',1)[1],'scratch cleanup changed')
check(prior.split('def member_references',1)[1].split('def compile_consumer',1)[0]==text.split('def member_references',1)[1].split('def compile_consumer',1)[0],'parser changed')
accepted=read(BASE/'android-effective-motion-review/result.json')
check(accepted['decision']=='ACCEPT_FOR_PARENT_INTEGRATION' and not accepted['blockingFindings'],'motion review not accepted')
for path,identity in accepted['implementationIdentities'].items():
    check(M.identity(ROOT/path)==identity,'accepted integrated identity differs: '+path)
profile=M.load_profile()
for kind,prefix in [('sdk','sdk'),('adapter','native/android')]:
    for name,identity in profile[kind+'_files'].items():
        path=ROOT/prefix/('engine' if kind=='adapter' and name.startswith('Sources/') else '')/name
        check(M.identity(path)==identity,'canonical source identity differs: '+name)

probes=[];inventories=[];class_baseline=None
for name in ['01-full','02-minimum','03-fixed']:
    proof=read(FIX/name/'proof.json');record=proof['command']
    check(record['terminal_custody'] and record['exit_code']==0 and record['stop'] is None,'failed retained probe')
    for stream,entry in record['logs'].items():
        check(M.identity(Path(entry['path']))=={k:entry[k] for k in ['bytes','sha256']},'retained log drift')
    classes=[Path(arg) for arg in record['argv'][1:] if not arg.startswith('-')]
    raw=Path(record['logs']['stdout']['path']).read_bytes()
    references=M.member_references(raw.decode(),classes)
    check(references==read(FIX/name/'members.json'),'reparsed member inventory differs')
    binary=[ref for path in classes for ref in binary_members(path)]
    parsed=[{k:ref[k] for k in ['class_file','constant_pool_index','kind']}|{'semantic_member':ref['member'].replace('"','')} for ref in references]
    check(binary==parsed,'binary semantic member references differ')
    class_tree=M.inventory(classes[0].parents[3])
    check(M.source_digest(class_tree)==proof['class_inputs_sha256'],'class input digest differs')
    if class_baseline is None:class_baseline=class_tree
    check(class_tree==class_baseline,'classfiles differ between retained probes')
    inventories.append(references)
    probes.append({'name':name,'classes':len(classes),'nested_classes':sum('$' in p.name for p in classes),
        'references':len(references),'kinds':dict(Counter(r['kind'] for r in references)),
        'binary_semantic_entries_equal':True,'raw_output':M.identity(Path(record['logs']['stdout']['path'])),
        'terminal_custody':record['terminal_custody'],'class_inputs_sha256':M.source_digest(class_tree)})
check(inventories[0]==inventories[1]==inventories[2],'probe inventory mismatch')
check(probes[0]['raw_output']==probes[2]['raw_output'],'full outputs differ')

plan=read(FIX/'pair8-integration-plan.json')
apple=M.apple_producer_provenance(plan['selected_environment'])
check(apple==read(FIX/'apple-producer-provenance.json'),'selected Apple metadata drift')
javap=read(FIX/'baseline.json')['javap_tool']
check(M.identity(Path(javap['path']))=={k:javap[k] for k in ['bytes','sha256']},'retained javap file identity drift')

preservation={}
for directory,files in read(FIX/'preserved-before.json').items():
    for name,expected in files.items():
        check(M.identity(Path(directory)/name)==expected,'historical evidence changed '+directory+'/'+name)
    preservation[directory]={'original_file_count':len(files),'all_recorded_files_unchanged':True}

ranges={'pair8':(96,115),'consumer_admission':(118,161),'output_limits':(164,227),
'custody':(229,341),'member_inventory':(344,411),'tamper':(414,465),
'apple_provenance':(495,510),'preflight':(537,565),'producers_and_six_forms':(576,625),
'postflight_and_scratch':(626,660)}
lines=current.splitlines(keepends=True)
references={key:{'file':'scripts/ci/check-android-generated-java.py','start_line':start,'end_line':end,
 'file_sha256':M.identity(runner)['sha256'],'line_range_sha256':hashlib.sha256(b''.join(lines[start-1:end])).hexdigest()}
 for key,(start,end) in ranges.items()}
report={'scope':'Current source/read-only retained evidence and pure Python; no compiler, JVM, javap, native or physical run',
 'finished_utc':datetime.now(timezone.utc).isoformat(),'python':sys.version,'optimized':not __debug__,
 'runner':M.identity(runner),'tests':M.identity(tests),'reversed_pair_literal_sha256':hashlib.sha256(current.replace(new_literal,old_literal)).hexdigest(),
 'canonical_pair':profile['id'],'sdk_count':len(profile['sdk_files']),'adapter_count':len(profile['adapter_files']),
 'product_java_count':len(M.java_roster(profile)),'integrated_reviewed_file_count':len(accepted['implementationIdentities']),
 'all_integrated_identities_equal':True,'command_cleanup_unchanged':True,'scratch_cleanup_unchanged':True,'parser_unchanged':True,
 'probes':probes,'all_probe_inventories_equal':True,'apple_producer':apple,'javap_file_identity':javap,
 'historical_preservation':preservation,'source_references':references,
 'limits':{'default_stream':4194304,'javap_stdout':8388608,'aggregate':67108864,'commands':160,'execution_seconds':2400,'command_seconds':600,'cleanup_seconds_per_command':5,'producer_jobs':2},
 'limitation':'Old retained classfile probes are pair7; pair8 complete output size and all six compiler closures remain unmeasured until next full run.'}
M.save(HERE/('audit-optimized.json' if not __debug__ else 'audit-normal.json'),report)
print(json.dumps({'accepted_integrated_files':report['integrated_reviewed_file_count'],'probes':probes,'historical_files':sum(x['original_file_count'] for x in preservation.values()),'status':'passed-read-only-evidence-audit'},indent=2))
