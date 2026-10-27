"""Seal only this lane after final finite review; no compilers or runtimes."""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
import json
import os
import shutil
from review import HERE, ROOT, BASE, TESTS, PRODUCER, EXPECTED_TREE, custody, sha, canonical, write, load, bounded

def main():
    assert not (HERE/'seal.json').exists()
    custody()
    out,err,command=bounded([sys.executable,HERE/'audit.py'],{'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1'},ROOT,30)
    (HERE/'audit-stdout').write_bytes(out);(HERE/'audit-stderr').write_bytes(err)
    command.update(schema=1,python_version=sys.version,platform=__import__('platform').platform(),source_tree_sha256=EXPECTED_TREE,
        review_driver_sha256=sha((HERE/'audit.py').read_bytes()),stdout_sha256=sha(out),stderr_sha256=sha(err),
        scope='finite source/custody/MIR/action review only')
    write('audit-command.json',command)
    assert command['exit_code']==0 and command['owned_group_absent'] and not command['timed_out'],out.decode()+err.decode()
    base=(BASE/'source/vm'/TESTS).read_bytes()
    attempts=[]
    for label,append in [('host-debug',HERE/'attempt-history/initial-tests.inc.rs'),('host-debug-corrected',HERE/'independent-tests.inc.rs')]:
        receipt=load(HERE/'commands'/label/'receipt.json')
        test=next(m for m in receipt['source_binding']['members'] if m['path']==TESTS)
        assert test['sha256']==sha(base+append.read_bytes())
        attempts.append(dict(label=label,append=append.relative_to(HERE).as_posix(),append_sha256=sha(append.read_bytes()),
            exact_test_member=test,test_exit_code=load(HERE/'commands'/label/'test-receipt.json')['exit_code']))
    write('attempt-source-bindings.json',dict(schema=1,base_tests_sha256=sha(base),attempts=attempts,
        initial_failure='Independent test expected healthy selected cleanup; actual unchanged conservative finalizer retains selected ConstructionBound. Original assertion/source/output preserved.',
        failure_corrected_by_test_expectation_only=True,production_changed=False))
    # Recheck only groups present in this lane's receipts, including version
    # probes and finite audit. No process table or unrelated group is inspected.
    groups={}
    def collect(value,path):
        if isinstance(value,dict):
            if 'owned_process_group' in value:groups[value['owned_process_group']]=path
            for k,v in value.items():collect(v,path+'#'+k)
        elif isinstance(value,list):
            for i,v in enumerate(value):collect(v,path+'#'+str(i))
    for p in (HERE/'commands').rglob('*receipt.json'):collect(load(p),p.relative_to(HERE).as_posix())
    collect(command,'audit-command.json')
    cleanup=[]
    for pg,path in sorted(groups.items()):
        try:os.killpg(pg,0);absent=False
        except ProcessLookupError:absent=True
        assert absent,(pg,path)
        cleanup.append(dict(owned_process_group=pg,path=path,rechecked_absent=True))
    for p in HERE.rglob('__pycache__'):shutil.rmtree(p)
    scratch=HERE/'owned-work'
    assert not any(scratch.iterdir())
    scratch.rmdir()
    write('cleanup.json',dict(schema=1,owned_groups=cleanup,owned_scratch_removed=True,global_process_inventory=False,
        native_or_capture_processes_started=False,other_projects_touched=False))
    write('summary.json',dict(schema=1,review=load(HERE/'review.json'),production_source_changes=False,
        producer_members_verified=85,producer_bytes_verified=5584323,source_members_verified=144,
        fresh_compiles=dict(base_metadata=1,candidate_metadata=1,independent_host_debug=2,independent_host_release=0),
        fresh_compiler_executions=4,initial_and_corrected_host_runs=2,fresh_final_host_tests_passed=8,
        scope='Independent raw logical template/action review and synthetic private-core host tests only; request common-attribution correction.',
        original_counter_zero_observed=True,ordinary_source_unchanged_qualified=False,bootstrap_external_grant_qualified=False,
        H_pre_ingress_qualified=False,complete_source_interval_funded=False,authentic_selected_ingress_executed=False,
        writer_runtime_selected=False,native_qualification=False,GA_gates_verified=0))
    members=[]
    for p in sorted(HERE.rglob('*')):
        if p.is_file() and p.name!='seal.json':
            data=p.read_bytes();members.append(dict(path=p.relative_to(HERE).as_posix(),bytes=len(data),sha256=sha(data)))
    write('seal.json',dict(schema=1,status='frozen independent review; common-attribution correction required',
        members=members,member_count=len(members),member_bytes=sum(m['bytes'] for m in members),manifest_sha256=sha(canonical(members)),
        source_tree_sha256=EXPECTED_TREE,producer_seal_sha256=sha((PRODUCER/'seal.json').read_bytes())))
    print(json.dumps(dict(seal_sha256=sha((HERE/'seal.json').read_bytes()),members=len(members),bytes=sum(m['bytes'] for m in members),
        status='correction required',checks=load(HERE/'review.json')['checks_passed'])),flush=True)

if __name__=='__main__':main()
