#!/usr/bin/env python3
"""Independently reconcile recorded execution bytes, then freeze this review only."""
import ast
from datetime import datetime, timezone
import difflib
import gzip
import hashlib
import json
from pathlib import Path
import platform
import stat
import subprocess
import sys

ROUND=Path(__file__).resolve().parents[1]
OWNED=ROUND.parent
REPO=ROUND.parents[2]
WORK=ROUND/'portable-root'
RUNNER=WORK/'scripts/ci/check-analyzer-envelope.py'
ROOT_RUNNER=REPO/'scripts/ci/check-analyzer-envelope.py'
FLAGS=['storedPrefixValidated','fullReplayAccepted','semanticMetricsValid','GA_qualified']


def demand(ok,text):
    if not ok:raise RuntimeError(text)


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(65536),b''):h.update(block)
    return h.hexdigest()


def record(path):return {'path':path.relative_to(REPO).as_posix(),'bytes':path.stat().st_size,'sha256':sha(path)}


def write(path,value):
    with path.open('x') as stream:json.dump(value,stream,indent=2,sort_keys=True);stream.write('\n')


def executed_names(text):
    done=[];pending=None
    for line in text.splitlines():
        if line.startswith('test ') and ' ... ' in line and not line.startswith('test result:'):
            demand(pending is None,'overlapping method output')
            name,body=line[5:].split(' ... ',1)
            if body=='ok':done.append(name)
            else:pending=name
        elif line=='ok':
            demand(pending is not None,'unowned terminal ok');done.append(pending);pending=None
    demand(pending is None,'unterminated method')
    return done


def audit_retention(folder,receipt):
    retained=json.loads((folder/'retention.json').read_bytes())
    demand(receipt['cleanup']['removed'] and not (folder/'scratch').exists(),'scratch not removed')
    demand(retained['test_files']==receipt['cleanup']['test_files'],'retention cross-record mismatch')
    reports=[];gzip_records=[]
    for name,r in retained['test_files'].items():
        path=folder/r['path'];demand(path.stat().st_size==r['bytes'] and sha(path)==r['sha256'],'retained encoded hash mismatch')
        h=hashlib.sha256();n=0;opener=gzip.open if r['encoding']=='gzip' else open
        with opener(path,'rb') as stream:
            for b in iter(lambda:stream.read(65536),b''):h.update(b);n+=len(b)
        demand(n==r['original_bytes'] and h.hexdigest()==r['original_sha256'],'retention is not lossless')
        if name.startswith('independent-files/') and name.endswith('.report'):reports.append({'name':name,**r})
        if r['encoding']=='gzip':gzip_records.append({'name':name,**r})
    paired=['complete','cap','bad-footer','bad-header','bad-profile','unknown-context','bad-second-record']
    limited=['limited-zero','limited-bad-footer']
    unused=['G-111','G-112','G-113','output-0','output-1','output-2','admission-setup','admission-finish','outer-limit']
    expected=set()
    for case in paired+limited+unused:
        expected.update('independent-files/'+case+'/'+f for f in ('stream.bin','profile.bin','context.bin'))
        for report in (['old.report','new.report'] if case in paired else ['new.report'] if case in limited else ['unused.report']):
            name='independent-files/'+case+'/'+report;expected.add(name)
            demand(retained['test_files'][name]['original_bytes']==(0 if case in unused else 49152),'actual-File report size mismatch')
    demand({name for name in retained['test_files'] if name.startswith('independent-files/')}==expected and len(expected)==79 and len(reports)==25,'actual-File inventory incomplete')
    for lane in ('producer','independent'):demand(retained['compiler_products'][lane+'-tests']['sha256']==receipt['test_binaries'][lane]['sha256'],'product hash cross-record mismatch')
    return {'retained_file_count':len(retained['test_files']),'independent_files':79,'actual_reports':reports,'gzip_records':gzip_records,'compiler_products':retained['compiler_products'],'scratch_removed':True}


audit={'schema':1,'at':datetime.now(timezone.utc).isoformat(),'command':[sys.executable,'-B',str(Path(__file__).resolve())],'python_executable':sys.executable,'python_version':sys.version,'git_version':subprocess.check_output(['git','--version'],cwd=REPO,text=True).strip(),'revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),'committed_tree':subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=REPO,text=True).strip(),'os':platform.platform(),'machine':platform.machine(),'scope':'Independent source/command/raw-output/retention reconciliation, not a semantic/native/GA gate.'}
demand(sha(RUNNER)==sha(ROOT_RUNNER)=='4c56beec330b8118f01be3a6e7460f9857e4b1e8b61f29b4a9bce16fb6c1130c','admitted runner changed')
demand(sha(REPO/'scripts/ci/tests/test_analyzer_envelope_runner.py')=='95adb99fd9f4dff39cf732414e8a287a5f301fe5860aa504e2ba394ccf33a8f1','admitted producer test bytes changed')
for base in (REPO/'verification/swift-envelope-ci-pack',WORK/'verification/swift-envelope-ci-pack'):
    demand(sha(base/'manifest.json')=='4800e90fa39b81d0e6514afa087a77b93f838204883974df7fbbec4c69a21b9a','manifest changed')
    manifest=json.loads((base/'manifest.json').read_bytes());actual=[]
    for p in sorted(base.rglob('*')):
        demand(not p.is_symlink(),'pack link')
        if p.is_file() and p!=base/'manifest.json':actual.append({'path':p.relative_to(base).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)})
    demand(actual==manifest['members'],'pack changed')
audit['live_current_inputs_verified']={'runner_sha256':sha(ROOT_RUNNER),'tests_sha256_hashed_not_loaded':sha(REPO/'scripts/ci/tests/test_analyzer_envelope_runner.py'),'pack_members':86,'pack_manifest_sha256':sha(WORK/'verification/swift-envelope-ci-pack/manifest.json')}
parser_results=[]
for label,opt in [('normal',0),('optimized',1)]:
    result=json.loads((ROUND/('parser-'+label+'.json')).read_bytes())
    demand(result['case_count']==result['passed']==346 and not result['failed'] and result['python_optimization']==opt,'parser controls failed')
    for case in result['cases']:
        path=ROUND/case['input']['path'];demand(path.stat().st_size==case['input']['bytes'] and sha(path)==case['input']['sha256'],'parser input changed')
    parser_results.append({'label':label,'cases':346,'passed':346,'optimization':opt,'report':record(ROUND/('parser-'+label+'.json'))})
audit['pure_parser_controls']=parser_results
baseline=json.loads((ROUND/'response-attempt2-baseline.json').read_bytes())
matrix=json.loads((ROUND/'response-attempt2-matrix.json').read_bytes())
demand(baseline['case_count']==baseline['passed']==1 and not baseline['failed'],'synthetic baseline failed')
demand(matrix['case_count']==matrix['passed']==39 and not matrix['failed'],'synthetic fault controls failed')
demand(all(r['correct_failure_class'] and r['intended_stage_reached'] and r['cleanup_removed'] and r['environment_scrubbed'] and r['raw_streams_verified'] for r in matrix['results']),'synthetic control stage/cleanup mismatch')
invalid=json.loads((ROUND/'response-attempt1-invalid.json').read_bytes());demand(invalid['all_results_excluded_from_acceptance'] and invalid['counted_passes']==0,'invalid fixture attempt not excluded')
audit['synthetic_response_controls']={'valid_baselines':1,'faults_at_intended_stage':39,'baseline_report':record(ROUND/'response-attempt2-baseline.json'),'matrix_report':record(ROUND/'response-attempt2-matrix.json'),'invalid_fixture_attempt':record(ROUND/'response-attempt1-invalid.json'),'excluded_invocations':40,'excluded_counted_passes':0}
receipts={};streams=0;commands=0
for path in sorted((WORK/'runs').glob('*/receipt.json')):
    receipt=json.loads(path.read_bytes());receipts[path.parent.name]=receipt
    for row in receipt['commands']:
        demand(row['child_returned'] and row['owned_group_gone'],'owned command did not return')
        for stream in ('stdout','stderr'):
            r=row[stream];p=path.parent/r['path'];demand(p.stat().st_size==r['bytes'] and sha(p)==r['sha256'],'raw command stream hash mismatch');streams+=1
        commands+=1
    demand(all(receipt[k] is False for k in FLAGS),'scope flag elevated')
    demand(all(p['passed'] for p in receipt['postflight'].values()),'postflight failed')
audit['all_recorded_run_evidence']={'runner_invocations_including_invalid_fixture':len(receipts),'commands':commands,'raw_streams':streams,'owned_command_groups_returned':True,'all_postflight_checks_passed':True}
host=receipts['actual-clean'];host_folder=WORK/'runs/actual-clean'
demand(host['status']=='passed-host-fixture-check' and not host['errors'] and len(host['commands'])==23,'clean host did not pass')
demand(host['rustc']['identity']['release']=='1.99.0' and host['rustc']['identity']['host']=='aarch64-apple-darwin','clean compiler tuple differs')
expected=json.loads((host_folder/'pack/inventories/expected-methods.json').read_bytes());method_results={}
for lane,key in [('producer','producer'),('independent','independent_exact_source')]:
    names=expected[key]['names'];listed=[s[:-6] for s in (host_folder/'commands'/f'{lane}-list.stdout').read_text().splitlines() if s.endswith(': test')]
    text=(host_folder/'commands'/f'{lane}-execute.stdout').read_text();executed=executed_names(text)
    demand(len(listed)==len(set(listed))==len(names) and set(listed)==set(names),'listing differs')
    demand(len(executed)==len(set(executed))==len(names) and set(executed)==set(names),'execution differs')
    summaries=[s for s in text.splitlines() if s.startswith('test result:')]
    demand(len(summaries)==1 and summaries[0].startswith(f'test result: ok. {len(names)} passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in '),'summary differs')
    method_results[lane]={'listed':len(listed),'executed':len(executed),'names':sorted(names)}
producer=(host_folder/'commands/producer-execute.stdout').read_text();layouts=json.loads((host_folder/'pack/inventories/expected-host-layouts.json').read_bytes())
raw=[s.partition('CORRECTED_ACTUAL_COMPLETE_LAYOUTS=')[2] for s in producer.splitlines() if 'CORRECTED_ACTUAL_COMPLETE_LAYOUTS=' in s]
demand(len(raw)==1 and json.loads(raw[0])==[r['bytes'] for r in layouts['layouts']],'fresh layouts differ')
demand(producer.count('ENVELOPE_ORACLE_CASES=16170')==1 and producer.count('CORRECTED_FINITE_BUDGET_CASES=5544')==1,'fresh comparison markers differ')
compile_rows=[r for r in host['commands'] if r['name'].endswith('-compile') or r['name']=='api-positive' or r['name'].startswith('api-negative-')]
demand(len(compile_rows)==12,'compile command count differs')
for row in compile_rows:
    argv=row['argv'];demand(argv.count('-Dwarnings')==1,'warnings policy differs')
    if row['name']=='independent-compile':demand(argv.count('-A')==1 and argv[argv.index('-A')+1]=='non_snake_case' and argv.index('-Dwarnings')<argv.index('-A'),'independent lint scope differs')
    else:demand(not any(s.startswith('-A') for s in argv),'lint allowance leaked')
span_map=json.loads((ROUND/'parser-originals/span-map.json').read_bytes());api_spans={}
for probe in span_map['probes']:
    observed=[]
    for line in (host_folder/'commands'/('api-negative-'+probe['name']+'.stderr')).read_bytes().splitlines():
        d=json.loads(line)
        if d.get('level')=='error' and d.get('code'):
            demand(d['code']['code']==probe['required_code'],'actual API code differs')
            for span in d.get('spans',[]):
                if span.get('is_primary'):
                    data=(host_folder/'pack'/span['file_name']).read_bytes();observed.append({'byte_start':span['byte_start'],'byte_end':span['byte_end'],'source_text_utf8':data[span['byte_start']:span['byte_end']].decode()})
    demand(sorted(observed,key=lambda x:x['byte_start'])==probe['selected_primary_spans'],'fresh actual API spans differ')
    api_spans[probe['name']]=observed
audit['clean_actual_host']={'receipt':record(host_folder/'receipt.json'),'outer_command':record(ROUND/'actual-clean-command.json'),'compiler':host['rustc'],'methods':method_results,'API_positive':host['api']['positive'],'API_negative':api_spans,'comparisons':21714,'layouts':layouts['layouts'],'retention':audit_retention(host_folder,host),'lint_scope_12_invocations_verified':True}
identity=receipts['identity-refusal'];api=receipts['api-refusal-optimized']
demand(identity['status']=='failed' and len(identity['commands'])==5 and 'library-compile' not in [r['name'] for r in identity['commands']] and identity['errors'][0]['message']=='Malformed/duplicate compiler identity field' and identity['cleanup'].get('scratch_created') is False,'identity black-box closure failed')
demand(api['status']=='failed' and len(api['commands'])==14 and api['errors'][0]['message']=='Wrong/duplicate primary API target span','API black-box closure failed')
api_cmd=json.loads((ROUND/'api-refusal-optimized-command.json').read_bytes());demand('-O' in api_cmd['argv'],'API black-box not optimized')
api_version=api['rustc']['version_verbose'];demand(api_version.count('host: ')==1 and api_version.count('release: ')==1,'API interposer identity not independently valid')
altered=[]
for line in (WORK/'runs/api-refusal-optimized/commands/api-negative-private-field.stderr').read_bytes().splitlines():
    d=json.loads(line)
    if d.get('level')=='error' and d.get('code'):
        for span in d['spans']:
            if span['is_primary']:demand(span['byte_start']==0 and span['byte_end']==1,'API fault absent');altered.append([0,1])
demand(altered,'API wrong primary not observed')
audit['separate_blackbox_blocker_closure']={'identity_receipt':record(WORK/'runs/identity-refusal/receipt.json'),'identity_refused_before_compile':True,'API_receipt':record(WORK/'runs/api-refusal-optimized/receipt.json'),'API_valid_identity_wrong_primary_under_O_refused':True,'API_failure_retention':audit_retention(WORK/'runs/api-refusal-optimized',api)}
old_path=OWNED/'review-round-1/portable-root/scripts/ci/check-analyzer-envelope.py'
old=old_path.read_text();new=RUNNER.read_text()
def functions(text):return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(text).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
before,after=functions(old),functions(new);changed=[name for name in before if before[name]!=after.get(name)]
demand(changed==['rustc_identity','verify_negative'] and set(after)-set(before)=={'diagnostic_json'},'unselected function changed')
(ROUND/'runner-change.diff').write_text(''.join(difflib.unified_diff(old.splitlines(keepends=True),new.splitlines(keepends=True),fromfile='rejected-round1-runner',tofile='admitted-corrected-runner')))
audit['prior_fault_control_reuse_basis']={'prior_runner':record(old_path),'changed_existing_functions':changed,'added_functions':['diagnostic_json'],'unchanged_functions':[n for n in before if n not in changed],'scope':'Prior controls are reused only for unchanged functions and identical pack bytes; prior rejected parser results remain rejected.'}
untouched=[]
for name in ['scripts/ci/check-analyzer-framing.py','scripts/ci/tests/test_analyzer_framing_runner.py','.github/workflows/verify.yml']:
    data=subprocess.check_output(['git','show','HEAD:'+name],cwd=REPO);demand((REPO/name).read_bytes()==data,'framing/workflow changed during review')
    untouched.append({'path':name,'sha256':hashlib.sha256(data).hexdigest(),'equal_to_HEAD':True})
audit['unchanged_framing_and_workflow']=untouched
preserved=[]
for relative,digest in [('preaccess-seal.json','07af3bdb40573f9c566987a5c261c6403e9cb61153f4066f1ab35c44e1c1cc3e'),('test-lint-preaccess-supplement/seal.json','04d74cdd7295bf092a072ac64aac83c93f178e37f24f53c9c4a079b60b07a27b'),('compiler-preaccess-supplement/seal.json','f6baf7ff5470c07e28582d93a3d149b71638079a75844d9dfff273a313d2dc7f'),('correction-1-preaccess-supplement/seal.json','c0007bbb86801f9a45fd80dc8d343df1d239b1b9e35b4a4a22a2c2e35b058ef0'),('review-round-1/seal.json','4f4d0da6ff694282ba72ba8dea8cd64ef243fc47703e480dd35eeb7af24e6fbc')]:
    path=OWNED/relative;demand(sha(path)==digest,'prior seal changed')
    if relative!='review-round-1/seal.json':
        for m in json.loads(path.read_bytes())['members']:
            p=REPO/m['path'];demand(p.stat().st_size==m['bytes'] and sha(p)==m['sha256'],'preaccess member changed')
    preserved.append({'path':path.relative_to(REPO).as_posix(),'sha256':digest})
audit['prior_seals_preserved']=preserved
mapping=json.loads((ROUND/'original-52-control-map.json').read_bytes());demand(len(mapping['rows'])==52 and not mapping['counted_52_pass_claim'],'original52 mapping differs')
audit.update({'original_plan_inventory':52,'original_control_map':record(ROUND/'original-52-control-map.json'),'review_status':'scoped-independent-acceptance-recommended-root-authority-retained','remaining_blockers':[],'CI_1_98_1_envelope_qualified':False,'producer_tests_loaded':False,'native_capture_UI_or_unrelated_process_discovery':False,'network_or_installation':False,**{k:False for k in FLAGS}})
write(ROUND/'raw-evidence-audit.json',audit)
members=[]
for p in sorted(ROUND.rglob('*')):
    if p.parent==ROUND and p.name in ('seal.json','seal.sha256'):continue
    mode=p.lstat().st_mode;demand(stat.S_ISDIR(mode) or stat.S_ISREG(mode),'special review artifact')
    if stat.S_ISREG(mode):members.append(record(p))
seal={'schema':1,'at':datetime.now(timezone.utc).isoformat(),'status':audit['review_status'],'member_count':len(members),'total_bytes':sum(m['bytes'] for m in members),'members':members,'tree_hash_encoding':'sha256 UTF-8 JSON members sort_keys=true separators comma/colon','tree_sha256':hashlib.sha256(json.dumps(members,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'runner_sha256':sha(RUNNER),'pack_manifest_sha256':sha(WORK/'verification/swift-envelope-ci-pack/manifest.json'),'pure_parser_cases':{'normal':346,'python_O':346},'actual_blackbox_blocker_refusals':2,'synthetic_response_controls':{'baseline':1,'expected_refusals':39},'invalid_reviewer_fixture_invocations_preserved_excluded':40,'clean_actual_host':{'release':'1.99.0','host':'aarch64-apple-darwin','producer':78,'independent':14,'API_positive':1,'API_negative':8,'comparisons':21714,'layouts':32},'original_plan_inventory':52,'claim_52_passed':False,'remaining_blockers':[],'root_acceptance':False,'CI_1_98_1_envelope_qualified':False,'excluded':['verification/swift-envelope-ci-independent-review/correction-review-1/seal.json','verification/swift-envelope-ci-independent-review/correction-review-1/seal.sha256'],**{k:False for k in FLAGS}}
write(ROUND/'seal.json',seal)
digest=sha(ROUND/'seal.json')
with (ROUND/'seal.sha256').open('x') as stream:stream.write(digest+'  verification/swift-envelope-ci-independent-review/correction-review-1/seal.json\n')
print(json.dumps({'seal_sha256':digest,'members':len(members),'member_bytes':seal['total_bytes'],'status':seal['status'],'blockers':0,'pure_parser':'346 normal+346 -O','response':'1 valid protocol+39 expected refusals;40 invalid fixture invocations excluded','actual_clean':'78+14/API1+8/21714/32'},sort_keys=True))
