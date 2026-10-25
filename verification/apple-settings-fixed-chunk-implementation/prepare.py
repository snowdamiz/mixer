"""Copy only root-selected immutable archives; derive two format endpoints."""
import hashlib,json,pathlib,shutil,tarfile
BASE=pathlib.Path(__file__).resolve().parent
ROOT=BASE.parents[1]
sha=lambda b:hashlib.sha256(b).hexdigest()

def main():
 expected={
 'verification/apple-settings-fixed-chunk-root-selection/selection.json':'99edd321744935dc9c6c1c3ccebe28706759e270100b72319f58a0338fee73e7',
 'verification/apple-settings-chunk-deadline-diagnosis/handoff.json':'019746fbd6344209c69ffde35a7a0933378943c280bbc3a69147b2afb532c40b'}
 inputs=BASE/'inputs';inputs.mkdir(exist_ok=True)
 for name,digest in expected.items():
  p=ROOT/name;assert sha(p.read_bytes())==digest,name
  if name.endswith('handoff.json'):
   for member,row in json.loads(p.read_bytes())['members'].items():
    q=ROOT/member;assert q.is_file() and not q.is_symlink() and sha(q.read_bytes())==row['sha256'] and q.stat().st_size==row['bytes'],member
  shutil.copyfile(p,inputs/p.name)
 archives=[('verification/apple-settings-instrumented-runtime-preparation/runtime-sources.tar.gz','selected',32,'765bd6b2caf703a65bf2f7d91e716f65c7b6cee6091a530e5106a96835dab13c'),('verification/apple-settings-instrumented-native-build/attempt-1/accepted-sources.tar.gz','accepted',40,'82b88c3ee0d55b3cf10930904f0f2eaed6d44b368659c9b2665f58cd28e764a9')]
 frozen={}
 for name,prefix,count,digest in archives:
  raw=(ROOT/name).read_bytes();assert sha(raw)==digest
  shutil.copyfile(ROOT/name,inputs/(prefix+'-sources.tar.gz'))
  with tarfile.open(inputs/(prefix+'-sources.tar.gz')) as archive:
   members=[m for m in archive.getmembers() if m.isfile()];assert len(members)==count and all(m.isfile() and m.name.startswith(prefix+'/') and '..' not in pathlib.PurePosixPath(m.name).parts for m in members)
   for m in members:
    data=archive.extractfile(m).read();out=BASE/'sources'/m.name;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(data);frozen[m.name]={'sha256':sha(data),'bytes':len(data)}
 endpoint='selected/inputs/runtime/verification/apple-toggle-keyboard-focus-v9-preparation/settings_telemetry.py'
 p=BASE/'sources'/endpoint;s=p.read_text()
 changes=[('CHUNK = 3072','CHUNK = 4992'),("set(value) == {'kind', 'case', 'uptime'} and value['case']", "set(value) == {'kind', 'case', 'uptime', 'chunkBytes'} and type(value['chunkBytes']) is int and value['chunkBytes'] == CHUNK and value['case']"),("'diagnosticOnly': True}\n        require(self.start_host", "'diagnosticOnly': True, 'chunkBytes': CHUNK}\n        require(self.start_host"),("integer(value['index'], 0, 651)","integer(value['index'], 0, 400)"),("len(value['data']) <= 4096","len(value['data']) <= 6656")]
 for before,after in changes:assert s.count(before)==1,(before,s.count(before));s=s.replace(before,after)
 p.write_text(s)
 endpoint2='accepted/harness/UITests/ToggleUITests.swift';p=BASE/'sources'/endpoint2;s=p.read_text()
 changes=[('import Foundation\n','import Foundation\nimport CoreFoundation\n'),('    let fixedCase =', '    private let chunkBytes = 4992\n    let fixedCase ='),('JSONSerialization.data(withJSONObject: ["settingsDiagnostic": record], options: [.sortedKeys])','JSONSerialization.data(withJSONObject: ["settingsDiagnostic": record], options: [.sortedKeys, .withoutEscapingSlashes])'),('["kind": "start", "case": fixedCase, "uptime": initial]','["kind": "start", "case": fixedCase, "uptime": initial, "chunkBytes": chunkBytes]'),('guard let token = result["generation"] as? String, let remaining = result["remainingSessionSeconds"] as? Double else { throw Failure.bridge }','guard let format = result["chunkBytes"] as? NSNumber,\n              CFGetTypeID(format) != CFBooleanGetTypeID(),\n              ["s", "i", "l", "q", "S", "I", "L", "Q"].contains(String(cString: format.objCType)),\n              format.intValue == chunkBytes,\n              let token = result["generation"] as? String, let remaining = result["remainingSessionSeconds"] as? Double else { throw Failure.bridge }'),('(payload.count + 3071) / 3072','(payload.count + chunkBytes - 1) / chunkBytes'),('index * 3072..<min(payload.count, (index + 1) * 3072)','index * chunkBytes..<min(payload.count, (index + 1) * chunkBytes)')]
 for before,after in changes:assert s.count(before)==1,(before,s.count(before));s=s.replace(before,after)
 p.write_text(s)
 fixture_names=['fixtures.py','test_v9.py','test_persistence.py']
 originals=BASE/'fixture-inputs';originals.mkdir(exist_ok=True)
 fixture_bindings={}
 for name in fixture_names:
  raw=(ROOT/'verification/apple-toggle-keyboard-focus-v9-preparation'/name).read_bytes();(originals/name).write_bytes(raw);fixture_bindings[name]={'sha256':sha(raw),'bytes':len(raw)}
 bindings={'schema':1,'sourceRevision':'ee390cbf56ba388a21c7d28c884dbed5fd7282fe','inputs':expected,'archives':[{'path':name,'prefix':prefix,'files':count,'sha256':digest} for name,prefix,count,digest in archives],'frozenFiles':frozen,'derivativeFiles':{name:{'sha256':sha((BASE/'sources'/name).read_bytes()),'bytes':(BASE/'sources'/name).stat().st_size} for name in frozen},'changedEndpoints':[endpoint,endpoint2],'unchangedSourceFiles':70,'fixtureInputBindings':fixture_bindings}
 assert [name for name in frozen if frozen[name]!=bindings['derivativeFiles'][name]]==[endpoint,endpoint2]
 (BASE/'source-bindings.json').write_text(json.dumps(bindings,sort_keys=True,indent=2)+'\n')
 print(json.dumps({'archivesVerified':2,'frozenMembers':72,'changedEndpoints':2,'unchangedSourceFiles':70,'diagnosisMembersVerified':31}))
if __name__=='__main__':main()
