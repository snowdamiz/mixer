"""Record the delivered repair and exact terminal console CI evidence once."""
from datetime import datetime, timezone
import copy
import hashlib
import json
from pathlib import Path
import subprocess

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
COMMIT = '114a2632fd58076574bd5b2444c511861c3b30d4'

def row(path):
    data = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

def save(name, value):
    with (OUT / name).open('x') as stream:
        json.dump(value,stream,indent=2)
        stream.write('\n')

assert not (OUT / 'terminal-console.json').exists(), 'One-shot; do not replay'
receipt = json.loads((OUT / 'receipt.json').read_bytes())
ci = json.loads((OUT / 'ci-jobs-1.stdout').read_bytes())
assert receipt['commit'] == ci['headSha'] == COMMIT and receipt['pushed'] and not receipt['force']
assert receipt['committed_paths'] == 165 and ci['attempt'] == 1
assert ci['conclusion'] == 'success' and len(ci['jobs']) == 1
job = ci['jobs'][0]
assert len(job['steps']) == 9 and all(step['status']=='completed' and step['conclusion']=='success' for step in job['steps'])
checkout = next(step for step in job['steps'] if step['name']=='Run actions/checkout@v4')
seconds = (datetime.fromisoformat(checkout['completedAt']) - datetime.fromisoformat(checkout['startedAt'])).total_seconds()
assert seconds == 6
manifest = json.loads((ROOT / 'verification/ci-console-sparse-checkout/input-manifest.json').read_bytes())
assert not subprocess.check_output(['git','diff','--name-only',receipt['parent'],COMMIT,'--',*[item['path'] for item in manifest['files']]],cwd=ROOT,timeout=10)
terminal = {'schema':1,'commit':COMMIT,'attempt':1,'run_id':ci['databaseId'],'url':ci['url'],
    'conclusion':'success','jobs':1,'steps_passed':9,'steps_skipped':0,'checkout_seconds':seconds,
    'receipt':row(OUT/'ci-jobs-1.command.json'),'output':row(OUT/'ci-jobs-1.stdout'),
    'tested_inputs_match_frozen_55_file_manifest':True,
    'scope':'Unchanged delivered console including first-page return; sparse checkout, Node/BEAM setup, npm install, complete console host tests, typecheck and production build.',
    'active_browser_session_consumer_tested':False,'native_browser_provider_or_GA_accepted':False}
save('terminal-console.json',terminal)
parentdir = ROOT/'verification/github-delivery-console-pagination-owner-contracts'
phoenix=json.loads((parentdir/'ci-jobs-7.stdout').read_bytes())
assert phoenix['headSha']==receipt['parent'] and phoenix['conclusion']=='success' and phoenix['attempt']==1
assert len(phoenix['jobs'])==1 and len(phoenix['jobs'][0]['steps'])==13
assert all(step['conclusion']=='success' for step in phoenix['jobs'][0]['steps'])
engine=json.loads((parentdir/'ci-jobs-8.stdout').read_bytes())
assert engine['headSha']==receipt['parent'] and len(engine['jobs'])==6
assert sum(job['conclusion']=='success' for job in engine['jobs'])==5
delivery={'status':'pushed-console-CI-passed-Engine-pending','commit':COMMIT,'tree':receipt['tree'],
    'paths':165,'pushed':True,'force':False,'receipt':row(OUT/'receipt.json'),
    'terminal_console':row(OUT/'terminal-console.json'),'Engine_observation':row(OUT/'ci-runs-1.stdout'),
    'active_product_lanes_excluded':True,'GA_accepted':False}
w=json.loads((ROOT/'work-graph.json').read_bytes())
g=json.loads((ROOT/'gates/ga.json').read_bytes())
for target in [w['packages'][13],g['gates'][21]]:
    target['ConsoleSparseCheckout'].update({'status':'delivered-and-console-CI-passed','remote_passed':True,'delivery':copy.deepcopy(delivery)})
    target['firstPageReturn']['followup_console_CI']=row(OUT/'terminal-console.json')
    target['latestConsoleCI']='114a2632 Console CI passes all nine steps on attempt one; checkout takes six seconds. Complete host tests, typecheck and production build pass for the unchanged delivered console. Active browser-session implementation and browser/provider operation are not qualified.'
    old=target['firstPageReturn']['delivery']
    old['status']='pushed-original-Console-cancelled-Phoenix-passed-Engine-five-of-six-passed'
    old['Phoenix_terminal']={'observation':row(parentdir/'ci-jobs-7.stdout'),'attempt':1,'steps_passed':13,'steps_skipped':0}
    old['Engine_latest']=row(parentdir/'ci-jobs-8.stdout')
    for item in old['CI']['runs']:
        if item['databaseId']==phoenix['databaseId']:
            item.update({'status':'completed','conclusion':'success'})
        if item['databaseId']==engine['databaseId']:
            item.update({'status':engine['status'],'conclusion':engine['conclusion']})
w['packages'][13]['nextImplementation']='Finish and independently review the strict frontend browser-session consumer, then deliver its validated source. Continue Engine CI observation. Real session/cookie endpoints, backend lifecycle/provider admission and stopped callback independent acceptance remain pending.'
c=w['packages'][7]['fixtureCacheStateContractCandidate']
assert c==g['gates'][1]['fixtureCacheStateContractCandidate']
c['guarded_snapshot_actual_owner_selection_console_delivery']=copy.deepcopy(w['packages'][13]['firstPageReturn']['delivery'])
c['console_sparse_checkout_IR01_delivery']=copy.deepcopy(delivery)
b=c['scalar_cursor_host_acceptance']['real_profile_adapter_preparation']['next_header_preparation']['retained_profile_composition_preparation']['real_binding_preparation']['real_profile_loader_binding']['next_adoption_lane']['guarded_snapshot_export_contract_review']['composition_source_preparation']['bootstrap_host_boundary']
b['actual_owner_Rust_selection']['correction'].update({'status':'source-active-targeted-command-roster-selected-waiting-for-console-compiler-lane',
    'queued_command_budget':{'compiler_invocations':9,'filtered_host_runs':2,'each_seconds_max':55,'lane_released':False,
        'scope':'Production metadata/MIR, Debug and opt2 test builds/runs, six precise missing Clone/borrow/static/privacy compiler subcases. Original IR01 witness unchanged; no native or blind full-matrix replay.'}})
g['gates'][1]['fixtureCacheStateContractCandidate']=copy.deepcopy(c)
for name,data in [('work-graph.json',w),('gates/ga.json',g)]:
    (ROOT/name).write_text(json.dumps(data,indent=2)+'\n')
for name in ['PLAN.md','STATUS.md']:
    path=ROOT/name
    text=path.read_text()
    old='The checkout-only sparse repair has root acceptance after exact verification of all 55 committed input files; remote validation awaits delivery. Phoenix and Engine workflows remain pending.'
    new='The checkout-only sparse repair is pushed as `114a2632` with 165 selected paths. Console CI passes all nine steps on attempt one, with a six-second checkout and unchanged runtime pins, tests and build commands. The preceding b231f3d Phoenix run passes all thirteen steps; five of its six Engine jobs pass and the remaining Swift job is still running. New Engine CI remains pending.'
    assert text.count(old)==1
    path.write_text(text.replace(old,new))
for path,sha in receipt['protected_work_unchanged'].items():
    assert row(ROOT/path)['sha256']==sha
assert not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,timeout=10)
subprocess.run(['git','diff','--check','--','PLAN.md','STATUS.md','work-graph.json','gates/ga.json'],cwd=ROOT,timeout=10,check=True)
save('terminal-console-metadata.json',{'at':datetime.now(timezone.utc).isoformat(),'script':row(Path(__file__).resolve()),
    'delivery':delivery,'metadata':[row(ROOT/p) for p in ['PLAN.md','STATUS.md','work-graph.json','gates/ga.json']],
    'protected_work_unchanged':True,'GA_verified':0})
print(json.dumps({'commit':COMMIT,'Console_CI_passed':True,'checkout_seconds':seconds,'parent_Phoenix_passed':True,'Engine_pending':True}))
