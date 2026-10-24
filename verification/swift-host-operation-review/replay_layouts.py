#!/usr/bin/env python3
from review import *
from audit_packet import parse_layout

def run():
 layouts=json.loads((PACKET/'qualified-accounted-layouts.json').read_text())
 for label in ['baseline','candidate']:
  name='qualified-accounted-metadata-'+label;m=json.loads((PACKET/(name+'-source-manifest.json')).read_text());vm=scratch()/name;vm.mkdir()
  for suffix in ['-source-manifest.json','-source.tar.gz']:shutil.copy2(PACKET/(name+suffix),HERE/(name+suffix))
  with tarfile.open(HERE/(name+'-source.tar.gz'))as t:
   for a in t:
    assert a.isfile()and a.name in m and '..'not in Path(a.name).parts;data=t.extractfile(a).read();assert sha(data)==m[a.name];p=vm/a.name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
  assert manifest(vm)==m
 records=[]
 for x in layouts:
  name='qualified-accounted-'+x['label']+'-'+x['features']+'-'+x['profile']+'-'+('unit'if x['unit']else'production');original=PACKET/'artifacts'/name;d=HERE/'artifacts'/('replay-'+name);d.mkdir(parents=True);identity=json.loads((original/'identity.json').read_text());data=gzip.decompress((original/'executable.gz').read_bytes());assert sha(data)==identity['executableSHA256'];shutil.copy2(original/'executable.gz',d/'executable.gz');shutil.copy2(original/'cargo-artifact.json',d/'producer-cargo-artifact.json')
  exe=scratch()/('replay-'+name);exe.write_bytes(data);exe.chmod(0o700);vm=scratch()/('qualified-accounted-metadata-'+x['label']);args=['--exact','experimental_swift_reactor::execution::frame_operations::host_contract_layout_only','--nocapture','--test-threads=1']if x['unit']else[]
  p,r=command('replay-'+name,[str(exe),*args],cwd=vm,source=vm);assert sha(exe.read_bytes())==identity['executableSHA256']and parse_layout(p.stdout.decode())==x['layout'];row=dict(producerArtifact=name,producerExactExecutablePath=identity['exactExecutablePath'],reviewExactExecutablePath=str(exe),executableBeforeSHA256=sha(data),executableAfterSHA256=sha(exe.read_bytes()),sourceClosure=tree(vm),outputLayoutIdentical=True);save('artifacts/'+d.name+'/identity.json',row);records.append(row)
 save('replayed-layouts.json',dict(contexts=len(records),exactSealedBinaries=True,layouts=records));print('Independent exact-binary layout replays passed 16 contexts',flush=True)
if __name__=='__main__':run()
