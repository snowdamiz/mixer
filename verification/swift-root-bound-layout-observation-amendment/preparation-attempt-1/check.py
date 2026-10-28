"""Read-only custody join for the one saved rejected command; no parser replay."""
from pathlib import Path
import hashlib
import sys
import time
from parser import decode,canonical,need,POLICY,BINDINGS,symbol_bindings,validate_span,all_spans

D=Path(__file__).resolve().parent;R=D.parents[1]
O=R/'verification/swift-root-bound-work-storage-layout-probe'
V2=R/'verification/swift-root-bound-work-storage-layout-probe-v2'
V3=R/'verification/swift-root-bound-work-storage-layout-probe-v3'
P=R/'verification/swift-root-bound-work-storage-layout-preaccess'
W=R/'verification/swift-root-bound-layout-warning-classification'

def sha(raw):return hashlib.sha256(raw).hexdigest()
def hashed(path,deadline=None):
    need(path.is_file() and not path.is_symlink(),'regular-nonsymlink-input:'+str(path))
    digest=hashlib.sha256();size=0
    with path.open('rb') as handle:
        while True:
            need(deadline is None or time.monotonic()<deadline,'custody-hash-deadline')
            raw=handle.read(262144)
            if not raw:break
            digest.update(raw);size+=len(raw)
    return {'bytes':size,'sha256':digest.hexdigest()}
def pin(row,base=R,deadline=None):
    path=Path(row['path']);path=path if path.is_absolute() else base/path
    need(hashed(path,deadline)=={k:row[k] for k in ('bytes','sha256')},'input-pin:'+str(path));return path
def sealed(base,name,digest,count,deadline,extra=None):
    need(hashed(base/name,deadline)['sha256']==digest,'seal-digest:'+str(base/name))
    seal=decode((base/name).read_bytes());need(len(seal['members'])==seal['member_count']==count,'seal-count')
    need(sha(canonical(seal['members']))==seal['tree_sha256'],'seal-tree')
    for row in seal['members']:pin(row,base,deadline)
    if extra is not None:
        found=set()
        for p in base.rglob('*'):
            need(time.monotonic()<deadline,'seal-inventory-deadline');need(not p.is_symlink(),'input-symlink')
            if p.is_file():found.add(p.relative_to(base).as_posix())
        need(found=={row['path'] for row in seal['members']}|{name}|set(extra),'closed-sealed-membership')
    return seal

def check(plan_sha=None,deadline=None):
    deadline=time.monotonic()+20 if deadline is None else deadline
    raw=(D/'plan.json').read_bytes();plan=decode(raw)
    if plan_sha is not None:need(sha(raw)==plan_sha,'root-selected-amendment-plan')
    need(plan['status']=='FROZEN_PREPARATION_AWAITING_ROOT_OFFLINE_SAVED_RAW_RELEASE','plan-state')
    for row in plan['scripts']:pin(row,D,deadline)
    for row in plan['inputs']:pin(row,R,deadline)
    pin(plan['policy'],D,deadline)
    names=['plan.json','plan.json.staged','owned-process.json','owned-process.json.staged','receipt.json','receipt.json.staged','stderr','stdout']
    sealed(O,'seal.json','c0e4da5b92f9fc076db21cb59700876bda60efaa7dc4b3c191124b707436fad9',173,deadline,[])
    sealed(V2,'seal.json','76fda3e073db9bb7408275cf5d8eb494cf491e5a9cd0a894ba8cca35171127f8',16,deadline,[])
    sealed(V3,'seal.json','898e88217ab2f04505d09571dbd8748b85cabc3b443a0dde12c47f4c800ed72c',17,deadline,['command/'+n for n in names])
    sealed(P,'terminal-v3-review-seal.json','4e42f67ff992fe7f3c9192b638ea9960eee4d3787bf5eeb40443113f5592760e',5,deadline)
    sealed(W,'seal.json','39976085aa6fd3cebf5c12bb6376358c46b11223df8347b8fb70ef12c20be5ab',9,deadline,[])
    vp=decode((V3/'plan.json').read_bytes());terminal=decode((P/'terminal-v3-review.json').read_bytes())
    need(sha((V3/'plan.json').read_bytes())=='95e3ebb57acc3c5ea9e7baac1f657c05ae36ffc957d86b77b38231f4480f958e','frozen-v3-plan')
    for key,base in [('original_source',Path(vp['original_source']['directory'])),('diagnostic_source',O/'source/vm')]:
        tree=vp[key];need(len(tree['members'])==146 and sha(canonical(tree['members']))==tree['tree_sha256'],'source146-tree')
        found=set()
        for path in base.rglob('*'):
            need(time.monotonic()<deadline and not path.is_symlink(),'source-inventory')
            if path.is_file():found.add(path.relative_to(base).as_posix())
        need(found=={row['path'] for row in tree['members']},'source146-membership')
        for row in tree['members']:pin(row,base,deadline)
    need(vp['original_source']['tree_sha256']==BINDINGS['original_source146_tree']==plan['source146_tree'],'original-source-binding')
    need(vp['diagnostic_source']['tree_sha256']==BINDINGS['diagnostic_source146_tree']==plan['diagnostic146_tree'],'diagnostic-source-binding')
    for name,text in BINDINGS['staged_two_sources'].items():need(Path(name).read_bytes()==text.encode(),'independent-bound-source-text')
    # Reproduce all three frozen source changes without mutating either source.
    before=Path(vp['original_source']['directory'])
    loader='src/experimental_swift_reactor/retained_profile_loader_v1.rs';cache='src/experimental_swift_reactor/cache/initial_profile_v1.rs'
    for name,fragment,anchor in [(loader,'proposed-owner-layout-queries.inc.rs',b'    // OWNER_PROBE_INSERTION'),(cache,'proposed-cache-layout-queries.inc.rs',b'    // Private outer caller candidate; all prior bodies remain exact.')]:
        source=(before/name).read_bytes();need(source.count(anchor)==1,'unique-source-edit-anchor')
        source=source.replace(anchor,(O/fragment).read_bytes()+b'\n'+anchor)
        if name==cache:
            old=b'        Ok(reservation.dispatch_v1(|| run_prepaid_admitted_fixture_v1(fixture, attempt, expected)))'
            need(source.count(old)==1,'unique-actual-closure-edit')
            source=source.replace(old,(O/'proposed-actual-closure-layout-fragment.rs').read_bytes().rstrip(b'\n'))
        need(source==(O/'source/vm'/name).read_bytes(),'exact-three-edit-replay')
    tools=decode((O/'toolchain-manifest.json').read_bytes());need(len(tools['members'])==67 and sha(canonical(tools['members']))==tools['tree_sha256'],'toolchain67-tree')
    for row in tools['members']:pin(row,Path(tools['root']),deadline)
    pin(vp['compiler'],R,deadline);pin(vp['python']['tool'],R,deadline);need(sys.version==vp['python']['version'],'python-version')
    sdk=decode((O/'sdk-path-settings.json').read_bytes());need(str(Path(sdk['requested']).resolve())==sdk['resolved'],'SDK-resolution')
    for row in sdk['settings']:pin(row,R,deadline)
    command=V3/'command';receipt=decode((command/'receipt.json').read_bytes());executed=decode((command/'plan.json').read_bytes())
    need(sorted(p.name for p in command.iterdir())==sorted(names),'saved-command-closed-membership')
    for row in terminal['saved_command_members']:pin(row,command,deadline)
    for name in ['plan.json','owned-process.json','receipt.json']:need((command/name).read_bytes()==(command/(name+'.staged')).read_bytes(),'final-staged-equality')
    for field in ['argv','environment','cwd','bounds','toolchain_version']:need(executed[field]==vp[field],'saved-command-'+field)
    need(executed['plan_sha256']==receipt['plan_sha256']==terminal['plan_sha256']==sha((V3/'plan.json').read_bytes()),'saved-command-plan-join')
    release=R/vp['root_release_required']['path'];need(hashed(release,deadline)['sha256']==receipt['root_release_sha256']==executed['root_release_sha256']=='10b544451522d3474ecb840098f7dbaba28852b8116ee84539dd4d3168507874','original-root-release')
    released=decode(release.read_bytes());need(released['compiler_lane_released'] is True and released['compiler_invocations']==1 and released['plan_sha256']==receipt['plan_sha256'],'original-release-fields')
    need(receipt['compiler_invocations']==receipt['compiler_exit_code']==1 and receipt['accepted_diagnostic_observation'] is False,'preserve-original-rejection')
    need(receipt['posthashes_verified'] is True and receipt['exception'] is None and receipt['elapsed_seconds_including_cleanup_posthashes']<55,'original-posthash-completion')
    need(receipt['ownership']=={'child_started':True,'child_reaped':True,'exact_pid_absent':True,'exact_group_absent':True,'exit_code':1},'original-owned-cleanup')
    need(receipt['build_cleanup']=={'build_existed':True,'removed':True,'inventory':[],'preserved_reason':None} and not (O/'build').exists(),'original-build-cleanup')
    need(not (command/'diagnostic-observation.json').exists(),'original-has-no-accepted-observation')
    need(receipt['failures']==[{'classification':'diagnostic-or-output-rejection','detail':'Rejected: unexpected coded diagnostic: unused_imports'}],'original-error-receipt')
    need(receipt['launch']['deferred_signals']==[] and receipt['publication_cutoff']['pre_cutoff_signal_count']==0,'original-signal-custody')
    owned=decode((command/'owned-process.json').read_bytes());need(owned=={'global_inventory':False,'new_session':True,'pgid':23228,'pid':23228} and receipt['launch']['retained_pid']==23228,'owned-process-record')
    for name in ['stderr','stdout']:
        observed=hashed(command/name,deadline);need(observed=={k:receipt['outputs'][name][k] for k in ['bytes','sha256']},'saved-output-hash')
        need(observed['bytes']==receipt['observed_output_bytes'][name]==receipt['captured_output_bytes'][name],'saved-output-closed-capture')
    need(hashed(command/'stderr',deadline)=={'bytes':292318,'sha256':'05c526210b4c07779c09c33f1944ffaa06d8012c57a57e3ad05f68ee34106635'},'exact-saved-raw')
    proposal=decode((W/'warning-classification-proposal.json').read_bytes())
    need(proposal['required_warning_count']==3 and proposal['required_ordered_record_lines']==[1,2,15] and proposal['original_v3_rejection_overridden'] is False,'warning-classification-scope')
    need([row['record_index']+1 for row in POLICY['warning_records']]==[1,2,15],'literal-warning-order')
    for row,expected in zip(POLICY['warning_records'],proposal['expected_warnings']):
        need(canonical(row['record'])==canonical(expected['exact_record']),'literal-warning-full-object')
        for span in all_spans(row['record']):validate_span(span)
    for row in POLICY['summaries']:
        need(row['record_index'] in [61,62,63] and row['record']['spans']==row['record']['children']==[],'literal-summary-roster')
    need([row['expression'] for row in symbol_bindings()]==[row['expression'] for row in BINDINGS['closure_queries']],'full-expression-symbol-join')
    need(plan['execution']['actual_saved_raw_parser_calls']==plan['execution']['compiler_invocations']==plan['execution']['child_workloads']==0,'preparation-only-state')
    return plan
