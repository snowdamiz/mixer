#!/usr/bin/env python3
"""Verify an independent review evidence packet; integrity is not root acceptance."""
import argparse,hashlib,json,pathlib,re,subprocess,tarfile
ROOT=pathlib.Path(__file__).resolve().parents[2]
OUT=pathlib.Path(__file__).resolve().parent
PROD=ROOT/'verification/hosted-artifact-admission-implementation'
DOC=ROOT/'docs/hosted-artifact-admission-review.md'
BASE='4586bb901b980e9beeca5f7bb826f8b62140a3b4'
def sha(b):return hashlib.sha256(b).hexdigest()
def digest(p):return sha(p.read_bytes())
def archive(path,want,files):
 assert digest(path)==want,path
 with tarfile.open(path,'r:gz') as t:
  members=t.getmembers();assert len(members)==len(files) and {m.name for m in members}==set(files)
  data={}
  for m in members:
   assert m.isfile() and not pathlib.PurePosixPath(m.name).is_absolute() and '..' not in pathlib.PurePosixPath(m.name).parts
   b=t.extractfile(m).read();assert sha(b)==files[m.name],m.name;data[m.name]=b
 return data

def validate():
 subprocess.run(['python3',str(PROD/'verify.py')],cwd=ROOT,check=True,capture_output=True)
 producer=json.loads((PROD/'seal.json').read_text());assert producer['packetSHA256']=='e21fb9d656e99d5c8ce47c3e42ece7470408850c8005fec68e93a69718f02ef9'
 freeze=json.loads((ROOT/'verification/hosted-artifact-admission-contract/freeze.json').read_text())
 for name,want in freeze['files'].items():
  assert digest(ROOT/name)==want,name
  if name.startswith('services/') or name.endswith('artifact_cbor.ex'):
   assert sha(subprocess.check_output(['git','show',f'{BASE}:{name}'],cwd=ROOT))==want,name
 summary=[]
 for name,count,oracle_count in [('run-1',119,60),('run-2',316,257)]:
  run=OUT/name;r=json.loads((run/'receipt.json').read_text());assert r['status']=='passed' and r['failure'] is None and r['baseRevision']==BASE
  assert r['sourceTreeSHA256']=='b893b73c8a3d7a978369b2af3121fe0054b2b5ec69d6f3fe48c659b498098433'
  inputs=r['sourceInputs'];assert len(inputs)==91 and sha(json.dumps(inputs,sort_keys=True,separators=(',',':')).encode())==r['sourceTreeSHA256']
  data=archive(run/'source.tar.gz',r['sourceArchiveSHA256'],inputs)
  overlay={str(p.relative_to(PROD/'overlay')):p.read_bytes() for p in (PROD/'overlay').rglob('*') if p.is_file()};assert len(overlay)==4
  for path,b in data.items():
   if path in overlay:assert b==overlay[path],path
   else:assert b==subprocess.check_output(['git','show',f'{BASE}:{path}'],cwd=ROOT),path
  lock=data['hosted/mix.lock'].decode()
  deps={m.group(1):(m.group(2),m.group(3)) for line in lock.splitlines() if (m:=re.fullmatch(r'  "([^\"]+)": \{:hex, :[^,]+, "([^\"]+)".*"([0-9a-f]{64})"\},',line))}
  assert len(deps)==20 and {d['name']:(d['version'],d['archiveSHA256']) for d in r['dependencies']}==deps
  for path,want in r['reviewHelpers'].items():assert digest(run/'helpers'/pathlib.Path(path).name)==want
  assert r['cleanup']=={'isolatedSourceRemoved':True,'ephemeralPrivateKeysPersisted':False,'existingProcessesAndDevicesTouched':False}
  assert not pathlib.Path(r['scratchPath']).exists()
  for c in r['commands']:assert c['exitCode']==0 and digest(run/c['output'])==c['outputSHA256'],c['label']
  go=json.loads((run/'original-go.json').read_text());ex=json.loads((run/'elixir-results.json').read_text());assert go==ex
  assert len(go['results'])==208 and all(c['accepted']==c['expected'] for c in go['results']) and go['assignmentCasesOutOfScope']==36
  assert go['fixtureFileSHA256']==inputs['services/protocol/testdata/signed-release-v3.json'] and go['corpusFileSHA256']==inputs['services/protocol/testdata/release-v3-cases.json']
  index=json.loads((run/'input-archive.json').read_text());originals=archive(run/'inputs.tar.gz',index['archiveSHA256'],index['files'])
  assert not (run/'inputs').exists() and index['cleanup']['looseOriginalInputsRemovedAfterVerifiedLosslessArchival']
  for path,b in originals.items():assert pathlib.Path(path).name.split('.')[0]==sha(b)
  cases=[json.loads(line) for line in (run/'cases.jsonl').read_text().splitlines()];assert len(cases)==count and len({c['name'] for c in cases})==count
  for c in cases:
   b=originals[c['input']];assert sha(b)==c['inputSHA256'] and len(b)==c['inputBytes']
   assert sha(originals[c['payload']])==c['payloadSHA256']
   for key in ['hostETF','rootsETF','nowETF']:assert c[key] in originals
   assert c['result']['accepted']==c['expected'] and c['result']['kind'] not in ['exception','throw_or_exit','unexpected_result']
   if not c['expected']:assert c['result']['kind']=='closed_error'
  oracles=json.loads((run/'independent-go-results.json').read_text());signed={c['name']:c for c in cases if c['go']}
  assert len(oracles)==len(signed)==oracle_count
  for c in oracles:
   expected=signed[c['name']];assert expected['mode']=='signed' and c['inputSHA256']==expected['inputSHA256'] and c['accepted']==c['expected']==expected['expected']==expected['result']['accepted']
  rechecks=json.loads((run/'rechecks.json').read_text());assert len(rechecks)==15
  for c in rechecks:
   assert c['result']['accepted']==c['expected'] and c['result']['kind'] in ['ok','closed_error']
   for key in ['checkedETF','hostETF','rootsETF']:assert c[key] in originals
  obs=json.loads((run/'independent-observations.json').read_text())['observations'];assert len(obs)==8
  assert obs[0]['inputBytes']==6291456 and obs[0]['result']['accepted']
  assert obs[1]['inputBytes']==6291457 and not obs[1]['result']['accepted']
  for c in obs:assert sha(originals[c['input']])==c['inputSHA256'] and len(originals[c['input']])==c['inputBytes']
  hosted=json.loads((run/'hosted/receipt.json').read_text());assert hosted['status']=='passed'
  archive(run/'hosted/source.tar.gz',hosted['source_archive_sha256'],hosted['inputs'])
  assert all(inputs[n]==h for n,h in hosted['inputs'].items())
  assert hosted['cleanup']=={'postgres_stopped':True,'scratch_removed':True}
  for c in hosted['commands']:assert c['exit_code']==c.get('expected_exit_code',0) and digest(run/'hosted'/c['log'])==c['sha256'],c['label']
  assert 'Result: 44 passed' in (run/'hosted/tests.log').read_text()
  summary.append({'run':name,'authoredCases':count,'identicalInputGoOracleCases':oracle_count,'originalComparisons':208,'rechecks':15,'hostedTests':44,'productionReleaseCompiled':True})
 traces=json.loads((OUT/'run-2/allocation-call-traces.json').read_text())['traces'];assert len(traces)==6
 assert traces[0]['result']['accepted'] and traces[0]['calls']['Base.decode64/2']==2
 assert all(c['calls']=={} and not c['result']['accepted'] for c in traces[1:4])
 assert all(c['calls'].get('Base.decode64/2',0)==0 and not c['result']['accepted'] for c in traces[4:])
 final_index=json.loads((OUT/'run-2/input-archive.json').read_text());originals=archive(OUT/'run-2/inputs.tar.gz',final_index['archiveSHA256'],final_index['files'])
 for c in traces:assert sha(originals[c['input']])==c['inputSHA256'] and len(originals[c['input']])==c['inputBytes']
 assert 'No actionable defect' in DOC.read_text()
 return {'status':'passed','recommendation':'accept-component-overlay-root-decision-pending','runs':summary,'findings':[],'liveProductApplied':False,'cleanupVerified':True}

def packet():
 files={str(DOC.relative_to(ROOT)):digest(DOC)}
 files.update({str(p.relative_to(ROOT)):digest(p) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='seal.json' and '__pycache__' not in p.parts})
 return files
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--seal',action='store_true');args=ap.parse_args();result=validate()
 if args.seal:
  assert not (OUT/'seal.json').exists(),'review packet seal is immutable'
  (OUT/'packet-verification.log').write_text(json.dumps(result,sort_keys=True)+'\n')
  files=packet();seal={'schema':1,'status':'independently-reviewed-component-acceptance-recommended-root-decision-pending','baseRevision':BASE,'sourceTreeSHA256':'b893b73c8a3d7a978369b2af3121fe0054b2b5ec69d6f3fe48c659b498098433','producerPacketSHA256':'e21fb9d656e99d5c8ce47c3e42ece7470408850c8005fec68e93a69718f02ef9','files':files,'packetSHA256':sha(json.dumps(files,sort_keys=True,separators=(',',':')).encode())}
  (OUT/'seal.json').write_text(json.dumps(seal,indent=2)+'\n')
 else:
  seal=json.loads((OUT/'seal.json').read_text());files=packet();assert files==seal['files'];assert sha(json.dumps(files,sort_keys=True,separators=(',',':')).encode())==seal['packetSHA256']
 print(json.dumps(result,sort_keys=True))
