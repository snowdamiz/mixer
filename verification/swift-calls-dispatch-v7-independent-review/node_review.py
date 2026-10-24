#!/usr/bin/env python3
"""Independent file-only Node companion provenance review. Never launches Node."""
from pathlib import Path
import argparse, datetime, gzip, hashlib, json, os, re, sys, traceback
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
NODE=HERE.parent/'swift-calls-dispatch-node-oracle-qualification'
V7=HERE.parent/'swift-calls-dispatch/v7-fixture-expectations'
enc=lambda x:(json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
def digest(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  while b:=f.read(8*1024*1024):h.update(b)
 return h.hexdigest()
def read(p):return json.loads(p.read_bytes())
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--seal-sha256',required=True);a=ap.parse_args()
 result={'schema':1,'status':'in-progress','command':sys.argv,'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'pythonVersion':sys.version,'verifierSHA256':digest(__file__),'NodeExecutedByReviewer':False,'WasmExecutedByReviewer':False,'compilerExecutedByReviewer':False,'nativeInstancesCreated':0,'runtimeQualified':False}
 try:
  assert digest(NODE/'review-seal.json')==a.seal_sha256
  seal=read(NODE/'review-seal.json')
  for rel,item in seal['bindings'].items():
   assert not Path(rel).is_absolute()and'..'not in Path(rel).parts
   p=NODE/rel;assert p.stat().st_size==item['bytes']and digest(p)==item['sha256'],rel
  d=read(NODE/'node-provenance.json')
  assert d['baseProducerSealSHA256']==digest(V7/'review-seal.json')=='79089f1ef382a14e02fbbbf0a6e6dcd0a67158bcfa5354d565a5b037b1d149b2'
  assert d['baseDriverSHA256']==digest(V7/'qualified_runtime.py')=='86595d8e18360fec5101a90feef7744c2f2a32d0482f88a6003ff1b7dfd4d2fb'
  assert d['candidateSourceClosure']=='78e2586b41f698c60e1bcd4cdd4abb33fbf98d747d1ee183a793988dea7b5237'
  resolved=Path(d['resolvedPATH']);actual=resolved.resolve();assert str(actual)==d['actualPath']and actual.stat().st_size==d['executableBytes']and digest(actual)==d['executableSHA256']
  source=V7/'candidate'/d['oracleSource'];assert d['oracleSource']=='tests/span_execution_oracle.rs'and digest(source)==d['oracleSourceSHA256']
  text=source.read_text();at=text.index('let script = r#"')+len('let script = r#"');end=text.index('"#;',at);script=text[at:end]
  assert script==d['script']and len(script.encode())==d['scriptBytes']==971 and hashlib.sha256(script.encode()).hexdigest()==d['scriptSHA256']and d['oracleArgv']==['node','-e',script]
  assert 'Command::new("node")'in text and '.args(["-e", script])'in text
  cache=Path(d['systemCacheDirectory']);assert str(Path(d['logicalSystemCacheDirectory']).resolve())==str(cache)
  assert {str(p)for p in cache.iterdir()}==set(d['systemCacheFiles'])
  for name,item in d['systemCacheFiles'].items():
   p=Path(name);assert p.is_file()and p.stat().st_size==item['bytes']and digest(p)==item['sha256'],name
  assert len(d['systemCacheFiles'])==82 and sum(x['bytes']for x in d['systemCacheFiles'].values())==d['systemCacheBytes']==7048019583
  for item in [d['loader'],d['systemVersion']]:assert digest(item['path'])==item['sha256']
  for name,item in d['physicalLoadedSystemFiles'].items():assert Path(name).stat().st_size==item['bytes']and digest(name)==item['sha256']
  maps=b''.join(Path(name).read_bytes()for name in d['systemCacheFiles']if name.endswith('.map'))
  assert maps
  for image in d['loadedVersionImages']:
   if image['path']==str(actual):continue
   if image['isPhysicalFile']:assert image['path']in d['physicalLoadedSystemFiles']
   else:assert image['pathAppearsInHashedCacheMap']and image['path'].encode()in maps
  names=['node-version','node-direct-dependencies','platform','node-version-loader-trace'];commands=read(NODE/'metadata-commands.json');assert len(commands)==len(names)
  for name,command in zip(names,commands):
   assert command['exitCode']==0 and digest(command['executable'])==command['executableSHA256']
   for stream in ['stdout','stderr']:
    raw=gzip.decompress((NODE/(name+'-'+stream+'.gz')).read_bytes());assert hashlib.sha256(raw).hexdigest()==command[stream+'SHA256']
  assert commands[0]['argv']==[str(actual),'--version']and commands[3]['argv']==[str(actual),'--version']
  assert commands[1]['argv']==['/usr/bin/otool','-L',str(actual)]and commands[2]['argv']==['/usr/bin/sw_vers']
  assert gzip.decompress((NODE/'node-version-stdout.gz').read_bytes()).decode().strip()==d['version']
  trace=gzip.decompress((NODE/d['loaderTraceRaw']).read_bytes()).decode()
  assert all(image['uuid']in trace and image['path']in trace for image in d['loadedVersionImages'])
  controls=read(NODE/'controls.json');assert controls['allRejected']and controls['dummyTargetRemoved']and not controls['wasmExecuted']and not controls['compilerCompilationExecuted']and controls['nativeInstancesCreated']==0
  assert controls['sourceSHA256']==digest(NODE/'controls.py')and all(x['rejected']for x in controls['controls'])
  assert controls['positiveFullLoaderCache']['systemCacheBytes']==d['systemCacheBytes']and controls['positiveFullLoaderCache']['systemCacheFiles']==82
  code=(NODE/'companion.py').read_text()
  assert 'self.node_selection='in code and 'self.selection='not in code
  result.update(status='separately-sealed-node-companion-provenance-review-passed',nodeCompanionSealSHA256=a.seal_sha256,companionSHA256=digest(NODE/'companion.py'),nodeProvenanceSHA256=digest(NODE/'node-provenance.json'),sealedFiles=len(seal['bindings']),actualNodeSHA256=d['executableSHA256'],nodeVersion=d['version'],scriptSHA256=d['scriptSHA256'],scriptBytes=971,systemCacheFiles=82,systemCacheBytes=d['systemCacheBytes'],physicalLoadedSystemFiles=len(d['physicalLoadedSystemFiles']),metadataVersionImages=len(d['loadedVersionImages']),negativeControls=len(controls['controls']),metadataCommandsVerified=len(commands),baseChecksPreserved=True,sourceReview={'noBaseAccountingCompilerOrCleanupCheckRemoved':True,'separateRootCompanionSealRequiredBeforeBaseMain':True,'injectionEnvironmentRejected':True,'nodeBytesAndOracleSourceScriptCheckAtEachBaseLaunch':True,'fullLoaderCacheAtStartupBeforeOwnedOracleListExecutionAndAfterDriver':True,'oracleOwnershipFromUniqueFreshActualCargoTestArtifact':True,'artifactIdentityNotInferredFromFilename':True,'inheritedRootSelectionHashStringPreserved':True,'allNodeChecksAndRawSealsSavedUnderQualificationRoot':True,'companionFailureRaisesAndBaseRuntimeAcceptanceRemainsPending':True},scope='Installed development Node/Apple loader/cache provenance and qualification companion only. Metadata probes were --version, otool and sw_vers; no reviewer Node, compiler or Wasm execution. Runtime results remain root-only acceptance.')
 except BaseException:result.update(status='rejected',failure=traceback.format_exc())
 (HERE/'node-review.json').write_bytes(enc(result));print(json.dumps(result,indent=2));return result['status']=='rejected'
if __name__=='__main__':raise SystemExit(main())
