from pathlib import Path
import gzip,json,re,sys
sys.dont_write_bytecode=True
import shapes
R=Path(__file__).resolve().parents[2]; V=R/'verification'; B=V/'swift-guarded-snapshot-funding-implementation/source/vm'; O=V/'swift-guarded-snapshot-host-composition/overlay/vm'
m=json.loads((V/'swift-guarded-snapshot-leaf-shell-cost/source-manifest.json').read_text());src={r['path']:((O/r['path']) if (O/r['path']).exists() else B/r['path']).read_bytes() for r in m['members']}; S=shapes.SourceShapes(src)
s=gzip.decompress((V/'swift-guarded-snapshot-loader-work-source146/whole-source146.mir.gz').read_bytes()).decode()
patterns=[r'::adopt_body_core_v1',r'::drop_proof_with_wasi\(',r'::finish_owned_cleanup\(',r'::retire_v1\(_1: SnapshotOuterV1',r'^fn construct_snapshot_in_scope_v1',r'^fn construct_snapshot_owned_v1',r'::snapshot_pair_v1\(_1: &accounted::AccountedWasi',r'::usage\(_1: &accounted::AccountedWasi',r'::cleanup\(_1: accounted::AccountedWasi',r'::cleanup\(_1: &mut Option<experimental_swift_reactor::cache::SwiftFunctionCache>',r'::complete\(_1: experimental_swift_reactor::cache::CacheCleanupTail',r'^fn drop_cleanup_return_storage',r'::snapshot_ticket_identity_v1\(',r'::snapshot_ticket_v1\(']
found=[];bad={}
for match in re.finditer(r'^fn .*$',s,re.M):
 h=match[0]
 if any(re.search(p,h) for p in patterns):
  end=re.search(r'^}\n',s[match.start():],re.M); body=s[match.start():match.start()+end.end()];found.append(body)
  arg=h.split('(',1)[1].rsplit(') -> ',1)[0]
  roles=re.findall(r'(_\d+): (.*?)(?=, _\d+:|$)',arg)+re.findall(r'^\s+let (?:mut )?(_\d+): (.*);(?:\s*//[^\n]*)?$',body,re.M)
  for n,t in roles:
   t=re.sub(r'<P as (?:[A-Za-z_]\w*::)*ClosedAdoptionV1>::Failure','SnapshotPreScopeFailureV1',t);t=re.sub(r'<P as (?:[A-Za-z_]\w*::)*ClosedAdoptionV1>::Retirement','Result<(), SwiftRunFailure>',t)
   if t=='T':t='Option<SwiftFunctionCache>'
   try:S.n(t)
   except Exception as e:bad[t]=str(e);S.active=[]
(Path(__file__).parent/'explore.mir').write_text('\n'.join(found));print(len(found),'selected bodies');print(json.dumps(bad,indent=2))
