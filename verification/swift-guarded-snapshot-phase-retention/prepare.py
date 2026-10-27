"""One-shot isolated retention amendment; frozen inputs remain immutable."""
from pathlib import Path
import difflib, hashlib, json, shutil
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'swift-guarded-snapshot-funding-implementation'
CONTROL='src/experimental_swift_reactor/control.rs'
PROFILE='src/experimental_swift_reactor/cache/initial_profile_v1.rs'
BASE_TREE='7e3e861ca65d8c6359623443d6a7810b878c1029494a0ae557307d35ed43484b'
BASE_SEAL='e006b90b8c9e351e0d4dd504c6de309e2c7970b628fe9fc4f788cb30e77bedf7'
ACCEPT=HERE.parent/'swift-semantic-adapter-root-review/guarded-snapshot-funding-host-acceptance.json'
ACCEPT_SHA='17789ef30bb818f91a928941162029a12c75ca7dddd33e8cfc073ec4950a615f'
RUSTC=Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc')
def sha(b):return hashlib.sha256(b).hexdigest()
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
def members(root):return [dict(path=p.relative_to(root).as_posix(),bytes=p.stat().st_size,sha256=sha(p.read_bytes())) for p in sorted(root.rglob('*')) if p.is_file()]
def write(name,x):(HERE/name).write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def seal(root,want):
 p=root/'seal.json';assert sha(p.read_bytes())==want
 x=json.loads(p.read_text());assert len(x['members'])==x['member_count']
 for r in x['members']:
  q=root/r['path'];assert q.stat().st_size==r['bytes'] and sha(q.read_bytes())==r['sha256'],r['path']
 return dict(path=str(p),sha256=want,members=len(x['members']))
def custody():
 assert sha(ACCEPT.read_bytes())==ACCEPT_SHA
 assert sha((BASE/'seal.json').read_bytes())==BASE_SEAL
 base=members(BASE/'source/vm');assert len(base)==144 and sha(canonical(base))==BASE_TREE
 rows=members(HERE/'source/vm');manifest=json.loads((HERE/'source-manifest.json').read_text());assert rows==manifest['members']
 return dict(source_members=144,source_tree_sha256=sha(canonical(rows)),baseline_source_tree_sha256=BASE_TREE,funding_acceptance_sha256=ACCEPT_SHA,writer_admission_selected=False)
def main():
 assert not (HERE/'seal.json').exists()
 frozen=seal(BASE,BASE_SEAL);assert frozen['members']==225
 review=seal(HERE.parent/'swift-guarded-snapshot-funding-independent','e971c908328ef36e8e5c582fd84d01999c1c4ddce473819b673cfda5ef48a8fc');assert review['members']==25
 assert sha(ACCEPT.read_bytes())==ACCEPT_SHA
 before=members(BASE/'source/vm');assert len(before)==144 and sha(canonical(before))==BASE_TREE
 target=HERE/'source/vm';assert not target.exists();shutil.copytree(BASE/'source/vm',target)
 changes=[]
 def change(name,old,new,reason):
  p=target/name;s=p.read_text();assert s.count(old)==1,(name,old);p.write_text(s.replace(old,new));changes.append(dict(path=name,old=old,new=new,reason=reason))
 old='''        self.reservations.combined.peak=self.reservations.combined.peak.max(combined);
        Ok(previous)
    }
}'''
 new=old.replace('Ok(previous)','Ok(construction)')
 change(CONTROL,old,new,'Return the already computed and committed total; no new expression role or arithmetic.')
 for old,new in [('Admitted {control:&\'c mut RuntimeControl,previous:usize,wasi:','Admitted {control:&\'c mut RuntimeControl,retained:usize,wasi:'),('Self::Admitted{control,previous,wasi}=>control.end_construction_phase_with_wasi(storage,previous,wasi),','Self::Admitted{control,retained,wasi}=>control.end_construction_phase_with_wasi(storage,retained,wasi),'),('let previous=control.snapshot_commit_storage_v1(additional)?;','let retained=control.snapshot_commit_storage_v1(additional)?;'),('Ok::<_,AError>((previous,shape,planning,emission))','Ok::<_,AError>((retained,shape,planning,emission))'),('Ok((previous,shape,planning,emission))=>{','Ok((retained,shape,planning,emission))=>{'),('(SnapshotAccessV1::Admitted{control,previous,wasi},storage)','(SnapshotAccessV1::Admitted{control,retained,wasi},storage)')]:
  change(PROFILE,old,new,'Coherent same-length retention-target rename, preserving existing places/types.')
 after=members(target);assert len(after)==144
 patch=[]
 for name in [PROFILE,CONTROL]:patch.extend(difflib.unified_diff((BASE/'source/vm'/name).read_text().splitlines(True),(target/name).read_text().splitlines(True),fromfile='funding144/'+name,tofile='retention144/'+name))
 (HERE/'source-delta.patch').write_text(''.join(patch))
 shutil.copyfile(BASE/'funding-constants.inc.rs',HERE/'funding-constants.inc.rs')
 write('source-manifest.json',dict(schema=1,members=after,source_tree_sha256=sha(canonical(after))))
 write('preparation.json',dict(schema=1,frozen_funding=frozen,independent_funding=review,acceptance=dict(path=str(ACCEPT),sha256=ACCEPT_SHA),baseline_source_tree_sha256=BASE_TREE,candidate_source_tree_sha256=sha(canonical(after)),exact_replacements=changes,changed_files=[PROFILE,CONTROL],added_runtime_arithmetic=0,added_runtime_locals=0,added_type_fields=0,conservative_charges_retained=True,root_approach_authorized=True,canonical_product_changed=False))
 write('input-lifetime-reports.json',dict(schema=1,reports=[dict(path=str(BASE/name),sha256=sha((BASE/name).read_bytes()),report=json.loads((BASE/name).read_text())) for name in ['lifetime-obligations.json','lifetime-retention-follow-up.json']],limitations=['H pre-ingress and independent harness costs remain unqualified','All source-role charges retained; no last-use or storage reuse credit','WorkAuditPending remains before actual selected A commit','Writer, full funding/work, healthy cleanup, target other than Rust1.99 aarch64 mac, native and GA acceptance remain unqualified']))
 print(json.dumps(custody(),sort_keys=True))
if __name__=='__main__':main()
