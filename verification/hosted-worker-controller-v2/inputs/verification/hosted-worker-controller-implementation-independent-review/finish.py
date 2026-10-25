#!/usr/bin/env python3
import gzip,hashlib,io,json,platform,shutil,subprocess,tarfile
from datetime import datetime,timezone
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent.parent
PRODUCER=ROOT/'verification/hosted-worker-controller-implementation'
REPORT=ROOT/'docs/hosted-worker-controller-implementation-independent-review.md'

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def record(p):return {'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p)}
def dump(name,value):(HERE/name).write_text(json.dumps(value,indent=2)+'\n')
def main():
    bindings=json.loads((HERE/'bindings.json').read_text());scratch=Path(bindings['scratch'])
    assert scratch.name.startswith('mixer-controller-independent-') and scratch.is_dir()
    producer=json.loads((PRODUCER/'receipt.json').read_text())
    assert sha(PRODUCER/'receipt.json')==bindings['receipt_sha256']
    assert sha(PRODUCER/'source-snapshot.tar.gz')==bindings['archive_sha256']
    source=json.loads((PRODUCER/'source-manifest.json').read_text())
    for e in source['files']+producer['artifacts']:
        p=ROOT/e['path'];assert p.stat().st_size==e['bytes'] and sha(p)==e['sha256'],str(p)
    scratch_product=[]
    for e in source['files']:
        if e['path'].startswith(('hosted-worker-controller/src/','hosted-worker-controller/dist/src/')):
            p=scratch/e['path'];assert p.stat().st_size==e['bytes'] and sha(p)==e['sha256'],str(p);scratch_product.append(e)
    dependency=json.loads((PRODUCER/'dependency-files.json').read_text())
    for e in dependency['files']:
        p=scratch/e['path'];assert p.stat().st_size==e['bytes'] and sha(p)==e['sha256'],str(p)
    tools=[]
    for argv in [['python3','--version'],['sw_vers'],[str(scratch/'hosted-worker-controller/node_modules/@cloudflare/workerd-darwin-arm64/bin/workerd'),'--version']]:
        r=subprocess.run(argv,capture_output=True,text=True);assert r.returncode==0
        tools.append({'argv':argv,'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
    reports=[json.loads((HERE/name).read_text()) for name in ['producer-replay-report.json','regression-attempt-1-report.json','regression-report.json','noncooperative-report.json']]
    assert reports[0]['status']=='passed' and len(reports[0]['results'])==28
    assert reports[1]['status']=='failed' and sum(x['status']=='failed' for x in reports[1]['results'])==2
    assert reports[2]['status']=='failed' and sum(x['status']=='failed' for x in reports[2]['results'])==3
    assert reports[3]['status']=='passed'
    storage=[e['persist'] for r in reports for e in r['cleanup'] if 'persist' in e]
    assert all(not Path(p).exists() for p in storage)
    binary=str(scratch/'hosted-worker-controller/node_modules/@cloudflare/workerd-darwin-arm64/bin/workerd')
    ps=subprocess.run(['/bin/ps','-axo','pid=,ppid=,comm='],capture_output=True,text=True);assert ps.returncode==0
    matching=[]
    for line in ps.stdout.splitlines():
        parts=line.strip().split(None,2)
        if len(parts)==3 and parts[2]==binary:matching.append({'pid':int(parts[0]),'ppid':int(parts[1]),'executable':parts[2]})
    assert not matching,'owned workerd remains; do not remove its storage'
    for src,dst in [('source-snapshot.tar.gz','reviewed-source-snapshot.tar.gz'),('receipt.json','reviewed-producer-receipt.json'),('source-manifest.json','reviewed-source-manifest.json'),('dependency-files.json','reviewed-dependency-files.json')]:shutil.copyfile(PRODUCER/src,HERE/dst)
    attempt=json.loads((HERE/'independent-regressions-attempt-1.command.json').read_text())
    relocated=[]
    for stream in ['stdout','stderr']:
        p=HERE/('independent-regressions-attempt-1.'+stream)
        assert sha(p)==attempt[stream]['sha256'];relocated.append({'original':attempt[stream],'preserved':record(p)})
    dump('attempt-1-relocation-bindings.json',{'source':record(HERE/'regressions-attempt-1.mjs'),'command':record(HERE/'independent-regressions-attempt-1.command.json'),'relocated_outputs':relocated,'report':record(HERE/'regression-attempt-1-report.json')})
    dump('post-run-bindings.json',{'status':'passed','producer_receipt_unchanged':True,'producer_artifacts_and_source_unchanged':True,'scratch_product_source_and_compiled_records':len(scratch_product),'scratch_dependency_files':len(dependency['files']),'tools':tools,'fixture_modifications_product_source':False})
    shutil.rmtree(scratch)
    cleanup={'status':'passed','test_cleanup_actions':sum(len(r['cleanup']) for r in reports),'storage_paths_checked':len(storage),'distinct_storage_paths':len(set(storage)),'all_owned_storage_absent':True,'owned_workerd_process_scan_argv':ps.args,'matching_owned_workerd':matching,'owned_scratch':str(scratch),'scratch_removed':not scratch.exists(),'other_processes_modified':False,'native_instances_started':0,'provider_cloud_calls':0}
    dump('cleanup.json',cleanup)
    fixtures=sorted([p for p in HERE.iterdir() if p.suffix in {'.py','.mjs','.ts'}]+[REPORT,HERE/'README.md'])
    archive=HERE/'review-fixtures.tar.gz'
    with archive.open('wb') as target,gzip.GzipFile(filename='',fileobj=target,mode='wb',mtime=0) as compressed:
        with tarfile.open(fileobj=compressed,mode='w') as tar:
            for p in fixtures:
                raw=p.read_bytes();entry=tarfile.TarInfo(str(p.relative_to(ROOT)));entry.size=len(raw);entry.mode=0o644;entry.mtime=0;tar.addfile(entry,io.BytesIO(raw))
    artifacts=[record(p) for p in sorted(HERE.iterdir()) if p.is_file() and p.name not in {'receipt.json','snapshot-check.json'}]+[record(REPORT)]
    receipt={'schema':1,'created_at':datetime.now(timezone.utc).isoformat(),'status':'rejected-two-correctness-findings','scope':'independent-per-operation-Worker-SQLite-DO-development-source-review-only','findings':[{'id':'R1','priority':'P1','summary':'final claim grant ignores superseding guard','source':'hosted-worker-controller/src/engine.ts:219-223','failing_cases':['claim-final-authority-epoch-owner-transfer','claim-final-authority-revision-advance']},{'id':'R2','priority':'P1','summary':'later qualified effect/claim clock samples do not advance durable clock history','source':'hosted-worker-controller/src/engine.ts:14-18','failing_cases':['later-effect-clock-sample-must-fence-rollback-before-claim']}],'reviewed_producer_receipt_sha256':bindings['receipt_sha256'],'reviewed_source_tree_sha256':bindings['source_tree_sha256'],'reviewed_source_archive':record(HERE/'reviewed-source-snapshot.tar.gz'),'review_fixture_archive':record(archive),'platform':platform.platform(),'tools':bindings['tools']+tools,'frozen_dependency_entries':58,'dependency_installs':0,'dependency_install_scripts_executed':0,'producer_groups_passed':28,'unique_independent_regression_groups':8,'independent_groups_passed':5,'independent_groups_failed':3,'producer_failures_repaired':False,'commands':[record(p) for p in sorted(HERE.glob('*.command.json'))],'artifacts':artifacts,'cleanup':cleanup,'not_verified':producer['not_verified']+['GA','physical-phone-matrix'],'no_git_inspected':True,'no_shared_files_changed':True,'source_revision':'explicit SHA-256 source tree; no Git inspected'}
    dump('receipt.json',receipt)
    print(json.dumps({'status':receipt['status'],'findings':2,'failed_cases':3,'producer_groups_passed':28,'artifacts':len(artifacts),'cleanup':cleanup,'receipt_sha256':sha(HERE/'receipt.json')}))
if __name__=='__main__':main()
