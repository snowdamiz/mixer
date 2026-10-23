#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,os,subprocess,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];TREE=HERE/'.build/source';FROZEN=ROOT/'verification/ui-native-packet-v1/candidate-2/.build/source'
sha=lambda b:hashlib.sha256(b).hexdigest()
lock=json.loads((ROOT/'verification/ui-native-packet-v1/candidate-2/input-lock.json').read_text());assert not TREE.exists()
for name,digest in lock['files'].items():
 data=(FROZEN/name).read_bytes();assert sha(data)==digest,name
 p=TREE/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
validator=TREE/'sdk/Sources/MixerUI/Validation.swift';original=validator.read_text()
old='        var bytes = 0\n';new=old+'        var reviewMaximumPending = 1\n        defer { print("ui_review_pending_max=\\(reviewMaximumPending)") }\n'
assert original.count(old)==1;derived=original.replace(old,new)
needle='            pending.append(contentsOf: node.children.reversed().map { ($0, depth + 1) })'
assert derived.count(needle)==1;derived=derived.replace(needle,needle+'\n            reviewMaximumPending = max(reviewMaximumPending, pending.count)')
validator.write_text(derived)
probe=HERE/'ReviewPacketTests.swift';(TREE/'sdk/Tests/MixerUITests/ReviewPacketTests.swift').write_bytes(probe.read_bytes())
env=os.environ|{'DEVELOPER_DIR':'/Applications/Xcode.app/Contents/Developer'}
commands=[]
for argv,label in [(['swift','--version'],'swift-version')]+[(['swift','test','--package-path','sdk','--scratch-path',str(HERE/'.build'/mode),'-c',mode,'--filter','review'],'tests-'+mode) for mode in ['debug','release']]:
 start=time.monotonic();p=subprocess.run(argv,cwd=TREE,env=env,capture_output=True,text=True);out=p.stdout+p.stderr;log=label+'.log';(HERE/log).write_text(out)
 commands.append({'argv':argv,'cwd':str(TREE),'environment_overrides':{'DEVELOPER_DIR':env['DEVELOPER_DIR']},'exit_code':p.returncode,'seconds':time.monotonic()-start,'output':log,'output_sha256':sha(out.encode())})
 (HERE/'receipt.json').write_text(json.dumps({'scope':'independent data-only SDK encoder probes; test-only pending-stack observation in isolated unchanged candidate2 copy','input_manifest':lock['files'],'input_tree_sha256':lock['tree_sha256'],'validator_original_sha256':sha(original.encode()),'validator_derived_sha256':sha(derived.encode()),'probe_sha256':sha(probe.read_bytes()),'commands':commands},indent=2)+'\n')
 print(label,p.returncode,out[-3500:],flush=True)
 if p.returncode:raise SystemExit(1)
