#!/usr/bin/env python3
from pathlib import Path
import collections,difflib,gzip,hashlib,io,json,re,tarfile
base=Path(__file__).resolve().parent
out=base/'candidate4-final'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read_manifest(folder):return json.loads((folder/'input-manifest.json').read_text())
a=read_manifest(base/'candidate3-final');b=read_manifest(out)
old={r['path']:r for r in a['files']};new={r['path']:r for r in b['files']}
changed=[n for n in new if new[n]['sha256']!=old[n]['sha256']]
assert changed==['docs/swift-executor-construction.md','vm/src/experimental_swift_reactor/execution.rs'],changed
rel='vm/src/experimental_swift_reactor/execution.rs'
source=(out/'inputs'/rel).read_text();tested=(base/'candidate3-final/inputs'/rel).read_text()
repairs=[('// Keep the original control and accounting tail inline; boxing would allocate\n// while returning a construction failure and change the measured authority.\n#[allow(clippy::large_enum_variant)]\n',1),('// Retain each exact mapped tuple identity in this const-only inventory.\n#[allow(clippy::type_complexity)]\n',4)]
stripped=source
for text,count in repairs:
 assert stripped.count(text)==count,(text,'unexpected annotation count')
 stripped=stripped.replace(text,'')
assert stripped==tested,'Non-annotation/comment source drift'
patch=''.join(difflib.unified_diff(tested.splitlines(True),source.splitlines(True),fromfile='tested-candidate3/'+rel,tofile='final-candidate4/'+rel))
(out/'semantic-bridge.patch').write_text(patch)
classes=json.loads((base/'candidate2-api/positive-accounting-map.json').read_text())['classes']
class_map={(c['scope'],c['field']):c for c in classes}
expected=json.loads((base/'candidate2-api/measurements.json').read_text())
expected_by={(r['name'].rsplit('-',1)[-1]):r for r in expected}
records=[]
commands=json.loads((base/'candidate3-final/commands.json').read_text())
for command in commands:
 if not(command['name'].endswith('-production-layout')or command['name'].endswith('-independent_positive_accounting_probe')):continue
 assert sha(base/'candidate3-final'/command['output'])==command['output_sha256']
 text=(base/'candidate3-final'/command['output']).read_text()
 rows=[{'scope':s,'field':f,'count':int(c),'offset':int(o),'size':int(n),'align':int(al)} for s,f,c,o,n,al in re.findall(r'positiveclass\|([^|]+)\|([^|]+)\|(\d+)\|(\d+)\|(\d+)\|(\d+)',text)]
 totals={s:{'bytes':int(n),'align':int(al)}for s,n,al in re.findall(r'positivetotal\|([^|]+)\|(\d+)\|(\d+)',text)}
 assert len(rows)==len(class_map)==615
 assert len({(r['scope'],r['field'])for r in rows})==615
 for r in rows:assert r['count']==class_map[(r['scope'],r['field'])]['count']
 cfg='production'if command['name'].endswith('production-layout')else'unit'
 assert rows==expected_by[cfg]['classes'],('actual wired field layout differs from proposal',command['name'])
 assert totals==expected_by[cfg]['totals'],('actual wired aggregate differs from proposal',command['name'])
 for scope in totals:
  extent=0
  for r in sorted((r for r in rows if r['scope']==scope),key=lambda r:(r['offset'],r['size'])):
   assert r['offset']%r['align']==0
   assert r['offset']+r['count']*r['size']<=totals[scope]['bytes']
   if r['size']:
    assert r['offset']>=extent,('nonzero field overlap',r)
    extent=r['offset']+r['count']*r['size']
 records.append({'name':command['name'],'cfg':cfg,'cwd':command['cwd'],'derived_source_sha256':command['derived_source_sha256'],'command_output':command['output'],'command_output_sha256':command['output_sha256'],'actual_classes':rows,'actual_totals':totals,'wired_bounds':command['wired_bounds'],'checks':'615 actual class counts, offsets, sizeof and alignof match the frozen proposal exactly; all nonzero arrays nonoverlapping/in-bounds/aligned; every log is an actual product-type probe rather than a duplicated declaration.'})
assert len(records)==8
(out/'qualified-layout-map.json').write_text(json.dumps(records,indent=2)+'\n')
protected=['vm/src/execute.rs','vm/src/lib.rs','vm/src/experimental/mod.rs','vm/src/experimental/execution/mod.rs','vm/src/experimental/execution/borrowed.rs','vm/include/mixer_vm.h','vm/Cargo.toml','vm/Cargo.lock']
first={r['path']:r for r in read_manifest(base)['files']}
for name in protected:assert new[name]['sha256']==first[name]['sha256'],name
proof=(out/'inputs/vm/src/experimental/swift.rs').read_text();original=(base/'inputs/vm/src/experimental/swift.rs').read_text();assert proof.startswith(original)
assert proof[len(original):].startswith('\n// Const-only inventory')
report={'schema':'mixer-swift-construction-independent-source-bridge-v1','status':'PASS','tested_input_manifest_sha256':sha(base/'candidate3-final/input-manifest.json'),'tested_tree_digest':a['tree_digest_sha256'],'final_input_manifest_sha256':sha(out/'input-manifest.json'),'final_tree_digest':b['tree_digest_sha256'],'changed_since_tested':changed,'execution_delta':'Exactly one large_enum_variant and four type_complexity allow attributes, each with the approved comment; removing those exact additions yields byte-for-byte tested execution source. No fields, function bodies, aliases, allocation, exports or algorithms changed.','doc_delta':'Producer narrative records evidence failures and corrected candidate qualification. Not used as a behavioral authority.','protected_legacy_files':{n:new[n]['sha256']for n in protected},'retained_getter_delta':'Original experimental/swift.rs is an exact byte prefix; sole appended const-only private descriptor declarations and size constant. No getter/metadata/type visibility changed.','actual_type_configurations':len(records),'actual_classes_per_configuration':615,'unresolved':[],'final_source_tests':'Tests run on candidate3-final with exactly the same execution bodies/types. No claim that candidate3 commands used candidate4 source hash; semantic bridge is explicit. Producer candidate4 source checks remain separately bound.'}
(out/'source-review.json').write_text(json.dumps(report,indent=2)+'\n')
# Preserve immutable original inputs in small deterministic archives. Build caches
# and copied derived trees remain local; replay uses capture manifests and overlays.
snapshots=base/'snapshots';snapshots.mkdir(exist_ok=True)
for folder,name in [(base,'candidate1'),(base/'candidate2-api','candidate2-api'),(base/'final','candidate2-wired'),(base/'candidate3-final','candidate3-final'),(out,'candidate4-final')]:
 destination=snapshots/(name+'.tar.gz')
 if destination.exists():continue
 with destination.open('wb')as raw:
  with gzip.GzipFile(filename='',fileobj=raw,mode='wb',mtime=0)as compressed:
   with tarfile.open(fileobj=compressed,mode='w')as archive:
    paths=[folder/'input-manifest.json',folder/'input-diff.patch',*(folder/'inputs').rglob('*')]
    for path in sorted(p for p in paths if p.is_file()):
     data=path.read_bytes();info=tarfile.TarInfo(str(path.relative_to(folder)));info.size=len(data);info.mtime=0;info.mode=0o644;archive.addfile(info,io.BytesIO(data))
print(json.dumps({'source_bridge':'PASS','metadata_configurations':len(records),'class_rows_each':615,'test_function_executions':sum(int(r['test_results'][0][1])for r in commands if r.get('test_results')),'source_tree_digest':b['tree_digest_sha256']}))
