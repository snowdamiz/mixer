#!/usr/bin/env python3
"""Independent raw-evidence reconciliation and finding freeze, no candidate import."""
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import stat
import subprocess
import sys

ROUND=Path(__file__).resolve().parents[1]
REPO=ROUND.parents[2]
OWNED=ROUND.parent
HOST=ROUND/'portable-root/runs/actual-host-explicit'
BAD=ROUND/'portable-root/runs/identity-api-interposition'


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(65536),b''):h.update(block)
    return h.hexdigest()


def demand(ok,message):
    if not ok:raise RuntimeError(message)


def write(path,value):
    with path.open('x') as stream:json.dump(value,stream,indent=2,sort_keys=True);stream.write('\n')


def file_record(path):
    return {'path':path.relative_to(REPO).as_posix(),'bytes':path.stat().st_size,'sha256':sha(path)}


def executed_names(text):
    completed=[];pending=None
    for line in text.splitlines():
        if line.startswith('test ') and ' ... ' in line and not line.startswith('test result:'):
            demand(pending is None,'new method before prior terminal ok')
            label,body=line[5:].split(' ... ',1)
            demand(label and not any(x.isspace() for x in label),'bad method label')
            if body=='ok':completed.append(label)
            else:pending=label
        elif line=='ok':
            demand(pending is not None,'unowned terminal ok')
            completed.append(pending);pending=None
    demand(pending is None,'unterminated last method')
    return completed


host=json.loads((HOST/'receipt.json').read_bytes())
bad=json.loads((BAD/'receipt.json').read_bytes())
early=json.loads((ROUND/'early-controls.json').read_bytes())
expected=json.loads((HOST/'pack/inventories/expected-methods.json').read_bytes())
layouts=json.loads((HOST/'pack/inventories/expected-host-layouts.json').read_bytes())
audit={'schema':1,'at':datetime.now(timezone.utc).isoformat(),'command':[sys.executable,'-B',str(Path(__file__).resolve())],
       'python_executable':sys.executable,'python_version':sys.version,'os':platform.platform(),'machine':platform.machine(),
       'revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),
       'committed_tree':subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=REPO,text=True).strip(),
       'git_version':subprocess.check_output(['git','--version'],cwd=REPO,text=True).strip(),
       'scope':'Independent byte/raw-output reconciliation; no candidate helpers or tests imported.'}
demand(host['status']=='passed-host-fixture-check' and not host['errors'],'clean host result failed')
demand(host['rustc']['identity']['release']=='1.99.0' and host['rustc']['identity']['host']=='aarch64-apple-darwin','wrong clean actual tuple')
method_results={}
for lane,key in [('producer','producer'),('independent','independent_exact_source')]:
    names=expected[key]['names']
    listed=[line.removesuffix(': test') for line in (HOST/'commands'/f'{lane}-list.stdout').read_text().splitlines() if line.endswith(': test')]
    text=(HOST/'commands'/f'{lane}-execute.stdout').read_text()
    executed=executed_names(text)
    demand(len(listed)==len(set(listed))==len(names) and set(listed)==set(names),'independent listing reconciliation failed')
    demand(len(executed)==len(set(executed))==len(names) and set(executed)==set(names),'independent execution reconciliation failed')
    summaries=[line for line in text.splitlines() if line.startswith('test result:')]
    prefix=f'test result: ok. {len(names)} passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in '
    demand(len(summaries)==1 and summaries[0].startswith(prefix),'libtest summary differs')
    method_results[lane]={'listed':len(listed),'executed':len(executed),'names':sorted(executed)}
producer=(HOST/'commands/producer-execute.stdout').read_text()
raw_layouts=[line.partition('CORRECTED_ACTUAL_COMPLETE_LAYOUTS=')[2] for line in producer.splitlines() if 'CORRECTED_ACTUAL_COMPLETE_LAYOUTS=' in line]
demand(len(raw_layouts)==1 and json.loads(raw_layouts[0])==[x['bytes'] for x in layouts['layouts']],'raw layout mismatch')
demand(producer.count('ENVELOPE_ORACLE_CASES=16170')==1 and producer.count('CORRECTED_FINITE_BUDGET_CASES=5544')==1,'comparison markers differ')
audit['fresh_clean_host']={'receipt':file_record(HOST/'receipt.json'),'elapsed_seconds':host['elapsed_seconds'],'compiler':host['rustc'],
                          'methods':method_results,'layouts':layouts['layouts'],'comparisons':21714,'API_positive':host['api']['positive'],'API_negative':len(host['api']['negative'])}
command_streams=0
for folder,receipt in [(HOST,host),(BAD,bad)]:
    for row in receipt['commands']:
        for stream in ('stdout','stderr'):
            record=row[stream];path=folder/record['path']
            demand(path.stat().st_size==record['bytes'] and sha(path)==record['sha256'],'raw command stream differs')
            command_streams+=1
        demand(row['child_returned'] and row['owned_group_gone'],'unreturned owned command')
audit['clean_and_interposed_command_streams_verified']=command_streams
compile_rows=[r for r in host['commands'] if r['name'].endswith('-compile') or r['name']=='api-positive' or r['name'].startswith('api-negative-')]
demand(len(compile_rows)==12,'compiler command count differs')
for row in compile_rows:
    args=row['argv'];demand(args.count('-Dwarnings')==1,'warnings not denied')
    if row['name']=='independent-compile':
        demand(args.count('-A')==1 and args[args.index('-A')+1]=='non_snake_case' and args.index('-Dwarnings')<args.index('-A'),'independent lint allowance differs')
    else:demand('-A' not in args and not any(x.startswith('-A') for x in args),'lint allowance leaked')
audit['lint_compile_scope_verified']={'compiler_invocations':12,'allowance_only':'independent-compile','flags':['-Dwarnings','-A','non_snake_case']}
report_spans={}
for path in sorted((HOST/'commands').glob('api-negative-*.stderr')):
    spans=[]
    for raw in path.read_bytes().splitlines():
        diagnostic=json.loads(raw)
        if diagnostic.get('level')=='error' and diagnostic.get('code'):
            for span in diagnostic.get('spans',[]):
                if span.get('is_primary'):
                    source=(HOST/'pack'/span['file_name']).read_bytes()
                    spans.append({'code':diagnostic['code']['code'],'file':span['file_name'],'byte_start':span['byte_start'],'byte_end':span['byte_end'],'source_text':source[span['byte_start']:span['byte_end']].decode(),'label':span.get('label')})
    report_spans[path.stem.removeprefix('api-negative-')]=spans
audit['clean_actual_primary_API_spans']=report_spans
retention=json.loads((HOST/'retention.json').read_bytes())
demand(retention['test_files']==host['cleanup']['test_files'],'retention manifest/receipt differ')
retained=[]
for name,record in retention['test_files'].items():
    path=HOST/record['path'];demand(path.stat().st_size==record['bytes'] and sha(path)==record['sha256'],'retained encoded bytes differ')
    h=hashlib.sha256();n=0
    opener=gzip.open if record['encoding']=='gzip' else open
    with opener(path,'rb') as stream:
        for block in iter(lambda:stream.read(65536),b''):h.update(block);n+=len(block)
    demand(n==record['original_bytes'] and h.hexdigest()==record['original_sha256'],'lossless retained bytes differ')
    retained.append({'name':name,**record})
paired=['complete','cap','bad-footer','bad-header','bad-profile','unknown-context','bad-second-record']
limited=['limited-zero','limited-bad-footer']
unused=['G-111','G-112','G-113','output-0','output-1','output-2','admission-setup','admission-finish','outer-limit']
expected_independent=set()
for case in paired+limited+unused:
    expected_independent.update('independent-files/'+case+'/'+filename for filename in ('stream.bin','profile.bin','context.bin'))
    reports=['old.report','new.report'] if case in paired else ['new.report'] if case in limited else ['unused.report']
    for report in reports:
        name='independent-files/'+case+'/'+report;expected_independent.add(name)
        demand(retention['test_files'][name]['original_bytes']==(0 if case in unused else 49152),'actual-File report size differs')
actual_independent={name for name in retention['test_files'] if name.startswith('independent-files/')}
demand(actual_independent==expected_independent and len(actual_independent)==79,'incomplete independent actual-File closure')
audit['retention_verified']={'file_count':len(retained),'independent_files':len(actual_independent),'independent_reports':25,'report_records':[r for r in retained if r['name'].startswith('independent-files/') and r['name'].endswith('.report')],'gzip_records':[r for r in retained if r['encoding']=='gzip'],'scratch_absent':not (HOST/'scratch').exists(),'compiler_product_records':retention['compiler_products']}
demand(host['cleanup']['removed'] and not (HOST/'scratch').exists(),'clean scratch cleanup incomplete')
for lane in ('producer','independent'):
    demand(retention['compiler_products'][lane+'-tests']['sha256']==host['test_binaries'][lane]['sha256'],'binary cross-record hash differs')
flags=['storedPrefixValidated','fullReplayAccepted','semanticMetricsValid','GA_qualified']
demand(all(host[x] is False and bad[x] is False for x in flags),'scope flags changed')
demand(bad['status']=='passed-host-fixture-check' and not bad['errors'] and len(bad['commands'])==23,'compound adverse acceptance not reproduced')
version=bad['rustc']['version_verbose']
demand(version.count('host: ')==2 and version.count('release: ')==2,'contradictory identity fixture absent')
wrong_spans=[]
for name,records in bad['api']['negative'].items():
    for record in records:
        span=record['primary_span'];source=(BAD/'pack'/span['file_name']).read_bytes()
        demand(span['byte_start']==0 and span['byte_end']==1 and source[0:1]==b'u','wrong API span interposition absent')
        wrong_spans.append({'probe':name,'code':record['code'],'source_span':[0,1],'source_text':'u'})
demand(len({r['probe'] for r in wrong_spans})==8,'not all eight probes interposed')
audit['acceptance_blockers']=[
    {'id':'R1','source':'scripts/ci/check-analyzer-envelope.py','lines':[269,275],'problem':'Duplicate contradictory compiler fields overwrite earlier values; incomplete verbose identity is admitted.','evidence':[file_record(BAD/'receipt.json'),file_record(ROUND/'faults/early-root/runs/incomplete-identity/receipt.json'),file_record(ROUND/'faults/early-root/runs/duplicate-identity/receipt.json')]},
    {'id':'R2','source':'scripts/ci/check-analyzer-envelope.py','lines':[360,365],'problem':'In-range primary span is not bound to intended refused source item.','wrong_spans':wrong_spans,'evidence':[file_record(BAD/'receipt.json')]}
]
demand(early['cases']==33 and early['control_passed']==31 and early['unexpected_acceptances']==['incomplete-identity','duplicate-identity'],'early control inventory differs')
demand(all(r.get('raw_streams_verified',True) and r.get('environment_scrubbed',True) and r.get('sentinel_preserved',True) for r in early['results']),'fault evidence/environment/sentinel mismatch')
by_name={r['name']:r for r in early['results']}
for name in ('marker-change','inode-change','scratch-link','scratch-fifo'):
    demand(not by_name[name]['cleanup']['removed'] and any(e['phase']=='retention-cleanup' for e in by_name[name]['errors']),'ownership/special cleanup did not refuse')
for name,check in [('snapshot-change','snapshot'),('runner-change','runner'),('compiler-change','compiler')]:
    demand(by_name[name]['postflight'][check] is False,'postflight mutation missed')
timeout=json.loads((ROUND/by_name['owned-descendant-timeout']['receipt']).read_bytes())
timeout_row=next(r for r in timeout['commands'] if r['name']=='rustc-verbose')
demand(timeout_row['timed_out'] and timeout_row['owned_group_gone'] and timeout_row['child_returned'],'owned descendant timeout cleanup incomplete')
try:os.killpg(timeout_row['owned_pgid'],0)
except ProcessLookupError:owned_group_gone=True
else:owned_group_gone=False
demand(owned_group_gone,'owned timeout group still present')
interrupted=by_name['retention-interrupted']
demand(interrupted['sent_retention_SIGTERM_to_owned_pid'] and interrupted['source_sparse_recoverable'] and not interrupted['cleanup']['removed'],'retention interruption did not preserve source')
sparse=ROUND/'faults/early-root/runs/retention-interrupted/scratch/sparse.failure'
demand(sparse.stat().st_size==64*1024*1024+4,'sparse source length differs')
with sparse.open('rb') as stream:
    demand(stream.read(5)==b'FIRST','sparse prefix differs');stream.seek(64*1024*1024);demand(stream.read()==b'LAST','sparse suffix differs')
audit['early_controls_verified']={'invocations':33,'expected_refusals':31,'identity_refusal_failures':2,'owned_descendant_group_gone':owned_group_gone,'retention_interrupted_sparse_source':file_record(sparse),'all_environment_scrubbed':True,'all_raw_streams_verified':True,'sentinel_preserved':True}
preserved=[]
for relative,expected_hash in [('preaccess-seal.json','07af3bdb40573f9c566987a5c261c6403e9cb61153f4066f1ab35c44e1c1cc3e'),('test-lint-preaccess-supplement/seal.json','04d74cdd7295bf092a072ac64aac83c93f178e37f24f53c9c4a079b60b07a27b'),('compiler-preaccess-supplement/seal.json','f6baf7ff5470c07e28582d93a3d149b71638079a75844d9dfff273a313d2dc7f')]:
    path=OWNED/relative;demand(sha(path)==expected_hash,'preaccess seal changed');seal=json.loads(path.read_bytes())
    for member in seal['members']:
        p=REPO/member['path'];demand(p.stat().st_size==member['bytes'] and sha(p)==member['sha256'],'preaccess member changed')
    preserved.append({'path':str(path.relative_to(REPO)),'sha256':expected_hash,'members':len(seal['members'])})
audit['preaccess_preserved']=preserved
runner=REPO/'scripts/ci/check-analyzer-envelope.py'
demand(sha(runner)=='4f5c6d64cb821b3fc1984794c96f81c8610c441ec47e3ff37cabb95b01fb43f1','live admitted runner changed')
manifest=json.loads((REPO/'verification/swift-envelope-ci-pack/manifest.json').read_bytes())
for member in manifest['members']:
    path=REPO/'verification/swift-envelope-ci-pack'/member['path'];demand(path.stat().st_size==member['bytes'] and sha(path)==member['sha256'],'live pack changed')
audit['live_candidate_and_86_pack_members_unchanged']=True
audit['review_status']='rejected-pending-root-selected-parser-correction'
audit['pending']=['Remaining independently malformed listing/execution/layout controls','Additional negative-diagnostic false positives and -O diagnostic control','Remaining launcher/timing variants','Fresh corrected-runner qualification after root selection','Actual Rust1.98.1 CI envelope qualification','All semantic/native/device/release/FieldLog/operations/GA gates']
audit.update({key:False for key in flags})
write(ROUND/'raw-evidence-audit.json',audit)
members=[]
for path in sorted(ROUND.rglob('*')):
    if path.name in ('seal.json','seal.sha256') and path.parent==ROUND:continue
    mode=path.lstat().st_mode
    demand(stat.S_ISDIR(mode) or stat.S_ISREG(mode),'nonordinary evidence member '+str(path))
    if stat.S_ISREG(mode):members.append(file_record(path))
seal={'schema':1,'at':datetime.now(timezone.utc).isoformat(),'status':audit['review_status'],'member_count':len(members),'total_bytes':sum(r['bytes'] for r in members),'members':members,'tree_hash_encoding':'sha256 UTF-8 JSON members sort_keys=true separators comma/colon','tree_sha256':hashlib.sha256(json.dumps(members,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'clean_actual_host':{'release':'1.99.0','host':'aarch64-apple-darwin','producer':78,'independent':14,'API_positive':1,'API_negative':8,'comparisons':21714,'layouts':32},'fault_invocations':33,'expected_refusals':31,'identity_refusal_failures':2,'compound_interposer_false_pass':True,'acceptance_blockers':2,'candidate_accepted':False,'CI_1_98_1_envelope_qualified':False,'excluded':['verification/swift-envelope-ci-independent-review/review-round-1/seal.json','verification/swift-envelope-ci-independent-review/review-round-1/seal.sha256'],**{key:False for key in flags}}
write(ROUND/'seal.json',seal)
digest=sha(ROUND/'seal.json')
with (ROUND/'seal.sha256').open('x') as stream:stream.write(digest+'  verification/swift-envelope-ci-independent-review/review-round-1/seal.json\n')
print(json.dumps({'seal_sha256':digest,'member_count':len(members),'member_bytes':seal['total_bytes'],'blockers':2,'clean_host':'78+14/API1+8/21714/32','faults':'31 expected refusals;2 identity failures; compound diagnostic-span false pass'},sort_keys=True))
