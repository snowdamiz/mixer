import json
import run_review as r
base=r.REPO/'verification/swift-guarded-snapshot-export-preparation/inputs/accepted-source/vm'
def read(path,root):return (root/path).read_text()
old=r.manifest(base);new=r.manifest(r.CANDIDATE/'source/vm')
assert old['member_count']==new['member_count']==144
assert new['tree_sha256']=='447719d8fef2928674d9d196266408ca72c70ce152cf0251807d2c3bcd7e7c43'
before={v['path']:v for v in old['members']};after={v['path']:v for v in new['members']}
assert before.keys()==after.keys()
changes=[{'path':k,'before':before[k],'after':after[k]}for k in before if before[k]!=after[k]]
path='src/experimental_swift_reactor/cache/initial_profile_v1.rs'
a=read(path,base);b=read(path,r.CANDIDATE/'source/vm')
def section(text,start,end):return text.split(start,1)[1].split(end,1)[0]
assert section(a,'enum InitialProfileConstructionOutcomeV1 {','\n#[repr(C)]')==section(b,'enum InitialProfileConstructionOutcomeV1 {','\n#[repr(C)]')
hook='    #[cfg(any(test,mixer_snapshot_encoder_host))]\n    snapshot_encoder_host::observe_v2(&initial);\n'
assert b.count(hook)==1
assert section(a,'fn construct_with_initial_profile_v1(','\nfn write_initial_profile_rows_v1')==section(b.replace(hook,''),'fn construct_with_initial_profile_v1(','\nfn write_initial_profile_rows_v1')
assert b.count('let initial=InitialProfileBorrowV1 { cache,control,wasi,scalars };')==1
unchanged=['src/experimental_swift_reactor/control.rs','src/experimental_swift_reactor/diagnostic_profile.rs','src/experimental_swift_reactor/cache/initial_profile_v1/header.rs','src/experimental_swift_reactor/cache/initial_profile_v1/selected.rs','src/experimental/metadata.rs','src/experimental_wasi/descriptor.rs']
for name in unchanged:assert(base/name).read_bytes()==(r.CANDIDATE/'source/vm'/name).read_bytes()
encoder=(r.CANDIDATE/'host/encoder.rs').read_bytes()
assert encoder in (r.CANDIDATE/'source/vm/src/experimental/swift.rs').read_bytes()
assert encoder in (r.SOURCE/'src/experimental/swift.rs').read_bytes()
assert r.manifest(r.SOURCE)==json.loads((r.HERE/'independent-source-manifest.json').read_text())
assert r.manifest(r.SUPPORT)==json.loads((r.HERE/'independent-support-manifest.json').read_text())
r.save(r.HERE/'source-audit.json',{'candidate_source':new,'changes':changes,'original_outcomes_identical':True,'original_constructor_minus_gated_hook_identical':True,'sole_guard_literal_count':1,'unchanged_paths':unchanged,'encoder_exact_candidate_bytes_preserved_in_independent_tree':r.desc(r.CANDIDATE/'host/encoder.rs'),'independent_tree':r.manifest(r.SOURCE),'actual_support_count':r.manifest(r.SUPPORT)['member_count']})
print('source-audit: pass; ten changed candidate source members; encoder unchanged in independent copy')
