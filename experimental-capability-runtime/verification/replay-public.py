#!/usr/bin/env python3
"""Implementer replay of the unchanged independent public harness, not new review."""
from pathlib import Path
import argparse, hashlib, json, os, re, subprocess, time
ROOT=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser();p.add_argument('--freeze',required=True);p.add_argument('--name',required=True);a=p.parse_args()
assert re.fullmatch(r'[a-z0-9-]{1,64}',a.name)
out=ROOT/'experimental-capability-runtime/verification'/a.name;out.mkdir(exist_ok=False)
owner_path=ROOT/'experimental-capability-runtime/verification'/a.freeze/'receipt.json';owner=json.loads(owner_path.read_text())
base=ROOT/'experimental-capability-runtime/.build'/a.name;source=base/'source';source.mkdir(parents=True,exist_ok=False)
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
inputs={}
for name,digest in owner['source'].items():
 original=Path(owner['frozenSourceExport'])/name;assert sha(original)==digest
 target=source/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(original.read_bytes());target.chmod(0o444);inputs[name]=digest
harness=ROOT/'verification/capability-bridge-review'
for path in [harness/'Package.swift',*sorted((harness/'PublicHarness').rglob('*'))]:
 if not path.is_file():continue
 name=str(path.relative_to(ROOT));target=source/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(path.read_bytes());target.chmod(0o444);inputs[name]=sha(path)
manifest=''.join(digest+'  '+name+'\n' for name,digest in sorted(inputs.items()));(out/'source-manifest.sha256').write_text(manifest)
stage=Path(owner['stageRoot'])/'host'
for name,digest in owner['nativeArtifacts']['host'].items():assert sha(Path(owner['stageRoot'])/name)==digest
command=['swift','test','--package-path',str(source/'verification/capability-bridge-review'),'--scratch-path',str(base/'debug'),'-Xcc','-I'+str(stage/'include'),'-Xlinker','-L'+str(stage/'lib'),'-Xswiftc','-warnings-as-errors']
env={'DEVELOPER_DIR':'/Applications/Xcode.app/Contents/Developer'}
began=time.monotonic();result=subprocess.run(command,cwd=source,env=os.environ|env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180)
log=out/'public-debug.log';log.write_bytes(result.stdout)
swift_counts=[int(n) for n in re.findall(rb'Test run with (\d+) tests? in \d+ suites? passed',result.stdout)]
xctest_counts=[int(n) for n in re.findall(rb'Executed (\d+) tests?, with 0 failures',result.stdout)]
passed=result.returncode==0 and bool(xctest_counts) and all(n==10 for n in xctest_counts)
record={'status':'passed' if passed else 'failed','scope':'Implementer replay of unchanged independent public API harness; not a new independent review','baseOwnerReceipt':str(owner_path.relative_to(ROOT)),'baseOwnerManifestSHA256':owner['sourceManifestSHA256'],'source':inputs,'sourceManifestSHA256':hashlib.sha256(manifest.encode()).hexdigest(),'command':command,'cwd':str(source),'environment':env,'exitCode':result.returncode,'passedTests':xctest_counts[-1] if passed else None,'swiftTestingCounts':swift_counts,'xctestCounts':xctest_counts,'expectedTests':10,'elapsedSeconds':time.monotonic()-began,'logSHA256':sha(log),'nativeArtifacts':owner['nativeArtifacts']['host'],'driverSHA256':sha(Path(__file__)),'frozenCopyUnchanged':all(sha(source/name)==digest for name,digest in inputs.items()),'harnessUnchanged':all(sha(ROOT/name)==digest for name,digest in inputs.items() if name.startswith('verification/capability-bridge-review/')),'limitations':['Local Xcode27.1/Swift6.3.3; pinnedCI Xcode26.3 not installed','No devices, new independent review, release or activation qualification']}
(out/'receipt.json').write_text(json.dumps(record,indent=2)+'\n');print(result.stdout.decode(errors='replace')[-13000:]);raise SystemExit(0 if record['status']=='passed' and record['frozenCopyUnchanged'] and record['harnessUnchanged'] else 1)
