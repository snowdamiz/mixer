"""Materialize only the frozen compiler candidate and correct selected ingress."""
from pathlib import Path
import hashlib,json,shutil,difflib
HERE=Path(__file__).resolve().parent
REPO=HERE.parent.parent
BASE=HERE.parent/'swift-guarded-snapshot-composition-source-preparation'
def sha(b):return hashlib.sha256(b).hexdigest()
def members(root):
    return [{'path':p.relative_to(root).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(root.rglob('*')) if p.is_file()]
def main():
    seal=BASE/'seal.json'
    assert sha(seal.read_bytes())=='bf17889754e7ef436fababcf8b96f5109285f982bcc48258a0b9e204a95b1751'
    before=json.loads((BASE/'source-manifest.json').read_text())['members']
    assert members(BASE/'source/vm')==before and len(before)==144
    evidence=HERE.parent/'swift-guarded-snapshot-composition-independent/candidate-review/bypass-evidence.json'
    assert sha(evidence.read_bytes())=='9d9a84a970e2c7c2417c9ac5c8a297e353074cfce8499c1fb211638a3d123608'
    target=HERE/'source/vm';assert not target.exists();shutil.copytree(BASE/'source/vm',target)
    patches={}
    def change(name,old,new):
        path=target/name;text=path.read_text();assert text.count(old)==1,(name,old)
        path.write_text(text.replace(old,new));patches.setdefault(name,[]).append({'old':old,'new':new})
    control='src/experimental_swift_reactor/control.rs'
    change(control,'pub(super) struct SnapshotRunV1 { scope:SnapshotScopeV1,outer:SnapshotOuterV1 }', '''/// A single-use borrow of the actual selected scope's owners. Only this module
/// can mint it; callers cannot substitute a different control or cache slot.
pub(super) struct SnapshotScopeBorrowV1<'a> {
    cache:&'a mut Option<super::cache::SwiftFunctionCache>,
    control:&'a mut RuntimeControl,
    wasi:Option<&'a AccountedWasi>,
    adopted:AdoptedProof,
}
impl<'a> SnapshotScopeBorrowV1<'a> {
    pub(super) fn into_parts(self)->(&'a mut Option<super::cache::SwiftFunctionCache>,&'a mut RuntimeControl,Option<&'a AccountedWasi>,AdoptedProof){
        let Self {cache,control,wasi,adopted}=self;
        (cache,control,wasi,adopted)
    }
}
pub(super) struct SnapshotRunV1 { scope:SnapshotScopeV1,outer:SnapshotOuterV1 }''')
    change(control,'''        let outer=super::cache::construct_snapshot_in_scope_v1(
            &mut self.cache,&mut self.control,self.wasi.as_ref(),adopted,claims,rows,snapshot);''','''        let owners=SnapshotScopeBorrowV1 {
            cache:&mut self.cache,control:&mut self.control,wasi:self.wasi.as_ref(),adopted,
        };
        let outer=super::cache::construct_snapshot_in_scope_v1(owners,claims,rows,snapshot);''')
    change('src/experimental_swift_reactor/cache.rs','''pub(super) fn construct_snapshot_in_scope_v1(cache:&mut Option<SwiftFunctionCache>,control:&mut RuntimeControl,wasi:Option<&AccountedWasi>,adopted:AdoptedProof,claims:&SnapshotClaimsV1,rows:&mut std::fs::File,snapshot:&mut std::fs::File)->SnapshotOuterV1{
    initial_profile_v1::construct_snapshot_owned_v1(cache,control,wasi,adopted,claims,rows,snapshot)
}''','''pub(super) fn construct_snapshot_in_scope_v1(owners:super::control::SnapshotScopeBorrowV1<'_>,claims:&SnapshotClaimsV1,rows:&mut std::fs::File,snapshot:&mut std::fs::File)->SnapshotOuterV1{
    initial_profile_v1::construct_snapshot_owned_v1(owners,claims,rows,snapshot)
}''')
    change('src/experimental_swift_reactor/cache/initial_profile_v1.rs','''pub(super) fn construct_snapshot_owned_v1(cache:&mut Option<SwiftFunctionCache>,control:&mut RuntimeControl,wasi:Option<&AccountedWasi>,adopted:AdoptedProof,claims:&UnverifiedProfileDigestBytesV1,rows:&mut File,snapshot:&mut File)->SnapshotOuterV1{
    construct_profile_core_v1(cache,control,wasi,adopted,&selected_initial_profile_v1(),claims,rows,SnapshotBranchV1{output:snapshot})
}''','''pub(super) fn construct_snapshot_owned_v1(owners:super::super::control::SnapshotScopeBorrowV1<'_>,claims:&UnverifiedProfileDigestBytesV1,rows:&mut File,snapshot:&mut File)->SnapshotOuterV1{
    let (cache,control,wasi,adopted)=owners.into_parts();
    construct_profile_core_v1(cache,control,wasi,adopted,&selected_initial_profile_v1(),claims,rows,SnapshotBranchV1{output:snapshot})
}''')
    after=members(target);assert len(after)==144
    changes=[]
    for name in patches:
        changes.extend(difflib.unified_diff((BASE/'source/vm'/name).read_text().splitlines(True),(target/name).read_text().splitlines(True),fromfile='frozen/'+name,tofile='corrected/'+name))
    (HERE/'source-delta.patch').write_text(''.join(changes))
    (HERE/'source-manifest.json').write_text(json.dumps({'schema':1,'members':after,'source_tree_sha256':sha(json.dumps(after,sort_keys=True,separators=(',',':')).encode())},indent=2)+'\n')
    (HERE/'preparation.json').write_text(json.dumps({'schema':1,'base_seal_sha256':sha(seal.read_bytes()),'base_source_tree_sha256':sha(json.dumps(before,sort_keys=True,separators=(',',':')).encode()),'bypass_evidence_sha256':sha(evidence.read_bytes()),'exact_replacements':patches,'source_members':144,'runtime_executed':False,'storage_and_work_delta_pending':True},indent=2)+'\n')
    print(json.dumps({'source_members':len(after),'changed_files':list(patches),'source_tree_sha256':sha(json.dumps(after,sort_keys=True,separators=(',',':')).encode())}))
if __name__=='__main__':main()
