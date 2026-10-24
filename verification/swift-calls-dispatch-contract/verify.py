#!/usr/bin/env python3
"""Independent read-only verifier: packet integrity and compiler scope, never acceptance of runtime behavior."""
import argparse,gzip,hashlib,json,tarfile
from pathlib import Path,PurePosixPath
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
BASE='1e89853d56f0ae46720cb0e9d72a4a2a13003f777e1d01f65db154f30782ed9c'
PROBE_NAMES={'pop_checked','typed_i32','call_defined','call_selected','indirect','fetch','local_slot','step','run','complete'}
sha=lambda data:hashlib.sha256(data).hexdigest()
canonical=lambda value:(json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
read=lambda path:json.loads(path.read_text())
def archive(path):
 with tarfile.open(path) as stream:
  members=stream.getmembers();names=[m.name for m in members]
  assert len(names)==len(set(names))
  for member in members:
   name=PurePosixPath(member.name)
   assert member.isfile() and not name.is_absolute() and '..' not in name.parts
  return {member.name:stream.extractfile(member).read() for member in members}
def digest_map(data):return {name:sha(body) for name,body in data.items()}
def headers(data):
 lines=data.decode().splitlines();out=[]
 for index,line in enumerate(lines):
  if not line.startswith('fn '):continue
  end=index
  while not lines[end].rstrip().endswith('{'):end+=1
  header='\n'.join(lines[index:end+1]);identity=header[3:].split('(',1)[0]
  if 'calls_contract_probe' in header or any(identity==name or identity.startswith(name+'::') for name in PROBE_NAMES):
   out.append({'line':index+1,'header':header})
 return out
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--unsealed',action='store_true');parser.add_argument('--live',action='store_true');args=parser.parse_args()
 if not args.unsealed:
  seal=read(HERE/'seal.json')
  actual={str(path.relative_to(HERE)) for path in HERE.rglob('*') if path.is_file() and path!=HERE/'seal.json'}
  assert actual==set(seal['files'])
  for name,digest in seal['files'].items():assert sha((HERE/name).read_bytes())==digest,name
  for name,digest in seal['documents'].items():assert sha((ROOT/name).read_bytes())==digest,name
 receipt=read(HERE/'receipt.json');assert receipt['status']=='ready-for-root-contract-selection'
 assert receipt['runtimeExecutions']==0 and not receipt['accountingAccepted'] and not receipt['nativeAccepted'] and not receipt['gaAccepted']
 inputs=read(HERE/'input-bindings.json');assert len(inputs)==25
 for name,digest in inputs.items():assert sha((HERE/'inputs'/name).read_bytes())==digest,name
 prefix=HERE/'inputs/verification/swift-cleanup-diagnostic-root-integration'
 baseline=archive(prefix/'integrated-source.tar.gz');manifest=read(prefix/'integrated-source-manifest.json')
 assert len(baseline)==128 and digest_map(baseline)==manifest and sha(canonical(manifest))==BASE
 integrated=read(prefix/'integration.json')
 assert integrated['integratedSourceClosure']==BASE and integrated['sourceFiles']==128
 assert integrated['status']=='passed-private-cleanup-diagnostic-integration'
 matrix=read(HERE/'matrix.json');groups=matrix['groups']
 assert matrix['operationVariants']==27 and matrix['runtimeExecutions']==0
 assert [g['id'] for g in groups]==[f'CD{i:02}' for i in range(1,25)]
 assert all(g['status']=='pending' and g['cases'] and g['assertions'] and g['testPrefix']==f"swift_dispatch_cd{i:02}_" for i,g in enumerate(groups,1))
 attempt=HERE/receipt['selectedAttempt'];status=read(attempt/'status.json')
 witness=archive(attempt/'witness-source.tar.gz');wmap=digest_map(witness)
 assert wmap==read(attempt/'witness-manifest.json') and len(witness)==129
 witness_sha=sha(canonical(wmap));assert status['witnessSHA256']==witness_sha==receipt['witnessSHA256']
 assert status['baselineSHA256']==BASE and status['runtimeExecutions']==0 and not status['accountingAccepted']
 assert archive(attempt/'baseline-source.tar.gz')==baseline
 extra='src/experimental_swift_reactor/calls_contract_probe.rs';frame='src/experimental_swift_reactor/frame_operations.rs'
 assert set(witness)-set(baseline)=={extra}
 assert witness[extra]==(HERE/'composition_probe.rs').read_bytes()
 assert witness[frame]==baseline[frame]+b'\n#[path="calls_contract_probe.rs"]\nmod calls_contract_probe;\n'
 assert all(witness[name]==body for name,body in baseline.items() if name!=frame)
 commands=read(attempt/'commands.json');assert len(commands)==17
 negatives={}
 for name in ['view-enter','arguments-truncate','growth-whole-instance','growth-ticket-alias']:
  negative=read(attempt/f'negative-{name}-manifest.json')
  assert set(negative)==set(wmap)
  assert all(digest==wmap[path] for path,digest in negative.items() if path!=extra)
  assert sha((attempt/f'negative-{name}.rs').read_bytes())==negative[extra]
  negatives['negative-'+name]=sha(canonical(negative))
 for row in commands:
  log=gzip.decompress((HERE/row['log']).read_bytes())
  assert sha(log)==row['outputSHA256']
  assert row['sourceUnchanged'] and row['sourceBeforeSHA256']==row['sourceAfterSHA256']
  assert not row['timedOut'] and not row['remainingGroup']
  if row['label'] in negatives:
   assert row['exitCode']!=0 and row['sourceBeforeSHA256']==negatives[row['label']]
   assert b'calls_contract_probe.rs' in log and any(code in log for code in [b'error[E0502]',b'error[E0499]',b'error[E0500]'])
  else:
   assert row['exitCode']==0
   assert row['sourceBeforeSHA256']==(BASE if row['target'] is None else witness_sha)
 artifacts=read(attempt/'mir-artifacts.json')
 expected={feature+'-'+profile+'-'+mode for feature in ['swift','all'] for profile in ['debug','release'] for mode in ['production','unit']}
 assert {row['label'] for row in artifacts}==expected and len(artifacts)==8
 for row in artifacts:
  raw=gzip.decompress((HERE/row['path']).read_bytes())
  assert sha(raw)==row['sha256'] and len(raw)==row['bytes'] and row['sourceSHA256']==witness_sha
  selected=headers(raw);assert selected==row['headers'] and len(selected)==24
  identities={header['header'][3:].split('(',1)[0].removeprefix('calls_contract_probe::') for header in selected}
  assert PROBE_NAMES<=identities
  # A complete raw MIR is retained; promoted bodies must never be silently
  # omitted if this witness later gains one. It has no selected promoted body.
  for line in raw.decode().splitlines():
   if line.startswith('const ') and ('calls_contract_probe' in line or any(line.startswith('const '+name+'::') for name in PROBE_NAMES)):
    raise AssertionError('New promoted body needs an explicit selector: '+line)
 for previous in sorted((HERE/'attempts').iterdir()):
  cleanup=read(previous/'cleanup.json')
  assert cleanup['ownedScratchRemoved'] and cleanup['holderCheckEmpty'] and cleanup['remainingCommandGroups']==0 and cleanup['nativeInstancesCreated']==0
  if args.live:assert not Path(cleanup['scratch']).exists()
 if args.live:
  assert all(sha((ROOT/'vm'/name).read_bytes())==digest for name,digest in manifest.items())
 print(json.dumps({'status':'passed-read-only-contract-packet-verification','sourceFiles':128,'baselineSHA256':BASE,'witnessFiles':129,'witnessSHA256':witness_sha,'commands':17,'positiveCompilerContexts':8,'fullSelectedHeadersPerContext':24,'requiredFreeBodiesPerContext':10,'expectedBorrowRejections':4,'runtimeGroupsPending':24,'runtimeExecutions':0,'liveSourceChecked':args.live,'accountingAccepted':False,'nativeAccepted':False,'gaAccepted':False},sort_keys=True))
if __name__=='__main__':main()
