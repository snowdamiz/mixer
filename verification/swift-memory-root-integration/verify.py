#!/usr/bin/env python3
"""Verify frozen inputs and integrated normalized source, without starting runtimes."""
import argparse,hashlib,json,pathlib,tarfile
HERE=pathlib.Path(__file__).resolve().parent; ROOT=HERE.parents[1]
sha=lambda b:hashlib.sha256(b).hexdigest()
enc=lambda x:(json.dumps(x,sort_keys=True,indent=2)+"\n").encode()
def main():
 p=argparse.ArgumentParser();p.add_argument('--live',action='store_true');args=p.parse_args()
 seal=json.loads((HERE/'seal.json').read_text())
 for name,digest in seal['bindings'].items():assert sha((ROOT/name).read_bytes())==digest,name
 receipt=json.loads((HERE/'acceptance.json').read_text())
 for group in [receipt['bindings'],json.loads((HERE/'accepted-input-bindings.json').read_text())]:
  for name,digest in group.items():assert sha((ROOT/name).read_bytes())==digest,name
 integration=json.loads((HERE/'integration.json').read_text());assert integration['status']=='passed-private-memory-integration'
 assert len(integration['appliedFiles'])==8 and integration['cleanup']['ownedScratchRemoved']
 expected=json.loads((HERE/'integrated-source-manifest.json').read_text())
 assert len(expected)==123 and sha(enc(expected))==integration['integratedSourceClosure']==receipt['integratedSourceClosure']
 candidate=ROOT/'verification/swift-memory-promoted-correction'
 reviewed=json.loads((candidate/'candidate-source-manifest.json').read_text())
 baseline=json.loads((candidate/'baseline-source-manifest.json').read_text())
 with tarfile.open(candidate/'candidate-source.tar.gz')as archive:
  members=archive.getmembers();assert len(members)==123
  assert all(m.isfile()and m.name.startswith('vm/')and'..'not in pathlib.PurePosixPath(m.name).parts for m in members)
  bodies={m.name.removeprefix('vm/'):archive.extractfile(m).read()for m in members}
 assert {n:sha(b)for n,b in bodies.items()}==reviewed
 assert sha(enc(reviewed))==receipt['reviewedSourceClosure']
 name='src/experimental/execution/mod.rs';lines=bodies[name].splitlines(keepends=True)
 assert lines[1138]==lines[1139]==b'    \n';lines[1138]=lines[1139]=b'\n';bodies[name]=b''.join(lines)
 assert {n:sha(b)for n,b in bodies.items()}==expected
 assert set(integration['appliedFiles'])=={'vm/'+n for n,d in expected.items()if d!=baseline.get(n)}
 for command in integration['commands']:
  assert command['exitCode']==0 and sha((HERE/command['log']).read_bytes())==command['sha256']
 for log,count in [('integrated-memory-frame-value-control.log',62),('integrated-frozen.log',16)]:
  assert f'test result: ok. {count} passed; 0 failed; 0 ignored;'in(HERE/log).read_text()
 review=json.loads((ROOT/'verification/swift-memory-promoted-review/receipt.json').read_text())
 assert review['independentReviewAccepted']and not review['blockingFindings']and review['positiveFields']==4800
 assert receipt['rootAccepted']and receipt['liveIntegrated']and not receipt['gaAccepted']
 if args.live:
  vm=ROOT/'vm';paths=[vm/'Cargo.toml',vm/'Cargo.lock']+[f for d in ['src','tests','include']for f in(vm/d).rglob('*')if f.is_file()]
  assert {str(f.relative_to(vm)):sha(f.read_bytes())for f in paths}==expected
 print(json.dumps({'verified':True,'upstreamBindings':receipt['upstreamBindings'],'rootBindings':len(receipt['bindings']),'sourceFiles':123,'freshFocused':62,'freshFrozen':16,'ciSwiftClippy':'passed','liveChecked':args.live,'gaAccepted':False}))
if __name__=='__main__':main()
