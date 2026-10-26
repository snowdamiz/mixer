#!/usr/bin/env python3
"""Freeze bounded source/design inputs. Never import, compile, or execute VM code."""
from pathlib import Path
import datetime, difflib, hashlib, json, platform, subprocess, sys, tarfile
ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PRODUCER = ROOT / 'verification/swift-cache-state-profile-adapter'
COMPLETION = ROOT / 'verification/swift-ordered-retention-diagnostic-completion'
EXPECTED_SEAL = '472dc4fcffbca9718c9b7c47ced3586170ffd9ab1dbf7185b07e3b4cd2ff87a3'
def sha(data): return hashlib.sha256(data).hexdigest()
def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + '\n')
def tree(rows):
    return sha(''.join(f"{r['path']}\t{r['bytes']}\t{r['sha256']}\n" for r in sorted(rows,key=lambda r:r['path'])).encode())
def run(argv):
    p = subprocess.run(argv, cwd=ROOT, text=True, capture_output=True, timeout=15)
    return {'argv':argv,'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
def main():
    if (OUT/'input-manifest.json').exists(): raise SystemExit('already frozen; do not overwrite inputs')
    members=[]
    def freeze(path, relative=None):
        raw=path.read_bytes(); relative=relative or str(path.relative_to(ROOT)); dest=OUT/'inputs'/relative
        dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
        members.append({'path':str(path.relative_to(ROOT)),'snapshot':str(dest.relative_to(OUT)),'bytes':len(raw),'sha256':sha(raw)})
        return raw
    sealraw=freeze(PRODUCER/'seal.json'); assert sha(sealraw)==EXPECTED_SEAL
    seal=json.loads(sealraw); assert seal['member_count']==len(seal['members'])==481
    lookup={r['path']:r for r in seal['members']}
    source=[]
    for r in seal['members']:
        if r['path'].startswith('source/'):
            raw=(PRODUCER/r['path']).read_bytes();assert len(raw)==r['bytes'] and sha(raw)==r['sha256']
            source.append({'path':r['path'][len('source/vm/'):], 'bytes':len(raw), 'sha256':sha(raw)})
    source_by_path={r['path']:r for r in source}
    relevant=['src/experimental/swift.rs','src/experimental/cache/borrowed.rs','src/experimental_swift_reactor/cache.rs','src/experimental_swift_reactor/control.rs','src/experimental_swift_reactor/cache_tests.rs','src/experimental_swift_reactor/mod.rs','src/experimental_swift_reactor/diagnostic_profile.rs','src/experimental_swift_reactor/diagnostic_profile_tests.rs']
    for p in relevant: freeze(PRODUCER/'source/vm'/p)
    for p in ['ACCOUNTING.md','accounting.json']:
        raw=freeze(PRODUCER/p);r=lookup[p];assert sha(raw)==r['sha256'] and len(raw)==r['bytes']
    for p in [
        'AGENTS.md','PLAN.md','mixer-product-plan.md',
        'docs/swift-semantic-adapter-prerequisite.md','docs/swift-semantic-adapter-contract-review.md',
        'docs/swift-semantic-adapter-terminal-correction.md','docs/swift-ordered-retention-diagnostic-design.md',
        'docs/swift-ordered-retention-analyzer.md','docs/swift-ordered-retention-analyzer-library.md',
        'docs/swift-ordered-retention-analyzer-fsm-contract.md',
        'verification/swift-cache-state-next-integration-preparation/source-review.md',
        'verification/swift-cache-state-next-integration-preparation/proposed-contract.md',
        'verification/swift-cache-state-next-integration-preparation/input-manifest.json',
        'verification/swift-semantic-adapter-root-review/profile-adapter-implementation-selection.json',
        'verification/swift-semantic-adapter-root-review/profile-adapter-protocol-amendment.md',
        'verification/swift-semantic-adapter-root-review/profile-adapter-bridge-compiler-amendment.md',
        'verification/swift-cache-state-ci/pack/source/library/analyzer.rs',
        'verification/swift-cache-state-ci/pack/source/library/cache_state.rs',
        'verification/swift-cache-state-ci/pack/inventories/bindings.json']:
        freeze(ROOT/p)
    old=json.loads(freeze(COMPLETION/'candidate-manifest.json'))
    archive=freeze(COMPLETION/'candidate-source.tar.gz')
    canonical=[]; comparison=[]; archive_members=[]
    with tarfile.open(COMPLETION/'candidate-source.tar.gz','r:gz') as t:
        files={m.name:m for m in t.getmembers() if m.isfile()}
        assert len(files)==len(old)==132 and set(files)==set(old)
        for p, expected in sorted(old.items()):
            raw=t.extractfile(files[p]).read(); assert sha(raw)==expected
            archive_members.append({'path':p,'bytes':len(raw),'sha256':sha(raw)})
            cur=freeze(ROOT/'vm'/p); c={'path':p,'bytes':len(cur),'sha256':sha(cur)};canonical.append(c)
            row=source_by_path.get(p)
            comparison.append({'path':p,'completion_sha256':expected,'canonical_sha256':c['sha256'],'row_candidate_sha256':None if row is None else row['sha256'],'completion_equal_canonical':expected==c['sha256'],'row_equal_canonical':None if row is None else row['sha256']==c['sha256']})
            if p in relevant:
                dest=OUT/'inputs/completion-source'/p;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
                members.append({'path':'archive:'+p,'snapshot':str(dest.relative_to(OUT)),'bytes':len(raw),'sha256':sha(raw)})
            if expected!=c['sha256']:
                diff='\n'.join(difflib.unified_diff(raw.decode().splitlines(),cur.decode().splitlines(),fromfile='completion/'+p,tofile='canonical/'+p,lineterm=''))+'\n'
                q=OUT/'source-diffs'/Path(p).with_suffix('.diff');q.parent.mkdir(parents=True,exist_ok=True);q.write_text(diff)
    dump(OUT/'closure-comparison.json',{'schema':1,'scope':'byte identity only; no mixed-closure equivalence or implementation acceptance','completion_members':archive_members,'canonical_members':canonical,'row_source_members':source,'canonical_tree_sha256':tree(canonical),'completion_tree_sha256':tree(archive_members),'row_source_tree_sha256':tree(source),'comparisons':comparison,'completion_changed':[r['path'] for r in comparison if not r['completion_equal_canonical']],'row_changed':[r['path'] for r in comparison if r['row_equal_canonical'] is False],'row_missing':[r['path'] for r in comparison if r['row_equal_canonical'] is None],'row_added':sorted(set(source_by_path)-set(old))})
    commands=[run(['git','rev-parse','HEAD']),run(['git','rev-parse','HEAD^{tree}']),run([sys.executable,'--version'])]
    dump(OUT/'environment.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'python_executable':sys.executable,'python_executable_sha256':sha(Path(sys.executable).resolve().read_bytes()),'python':sys.version,'platform':platform.platform(),'commands':commands,'no_VM_compile_or_execution':True,'no_native_capture_UI_or_process_inventory':True,'git_read_only':True})
    dump(OUT/'input-manifest.json',{'schema':1,'members':members,'tree_sha256':tree(members),'tree_definition':'SHA256 of sorted original-path TAB bytes TAB sha256 LF rows','producer_seal_sha256':EXPECTED_SEAL,'producer_seal_members_claimed':481,'producer_source_members_individually_verified':len(source),'producer_non_source_artifacts_not_accessed':True,'source_revision':'context only; exact bytes above are authority for this offline proposal'})
    print(json.dumps({'inputs':len(members),'canonical_members':len(canonical),'producer_source_members':len(source),'completion_members':len(archive_members),'diff_files':4,'scope':'source freeze and byte comparison only'},sort_keys=True))
if __name__=='__main__':main()
