#!/usr/bin/env python3
"""Prepare an exact delivery allowlist; does not stage, commit or push."""
from pathlib import Path
import hashlib, json, os, stat, subprocess, datetime
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
BASE='7b6048642b42e4900cccff4e14aa0fe8949ab35e'
SEALS={
 'verification/swift-current-attribution-runtime-review/seal.json':'158aa5a24d150b05b05bd71325fe31821d3c8276766e63258d87e7fc0b4f2e8b',
 'verification/apple-passive-lifecycle-generic-build/handoff.json':'5b23f406d3781bccc59f1e181c2588c6df7af16435b375c4cc0bd197d559a8c1',
 'verification/apple-passive-lifecycle-sendable-correction/handoff.json':'207821bc258c351b1767932ad7b2e85dd7f621f3ad7e56054bcb3cfdcf87ed88',
 'verification/apple-passive-sendable-review/handoff.json':'859892145e06424104de36370c5811fb47dedacf34a6a0546e8f796b9fb3e2e1',
 'verification/apple-passive-lifecycle-runtime-preparation/handoff.json':'88ab5fbfe323510fbdf356c2f5effb6844ea2aeb3fec6758d8f88071ba30fc1f',
 'verification/apple-passive-runtime-review/handoff.json':'7e6f32973d6cb8980b2b26699724811cfad6cc5adca00a884c30d39a602a037e',
 'verification/swift-current-attribution-preparation-review/seal.json':'d4eff30cc7c48accf8c93621e0810ec94a68ee282699fed9a1aaf772071ac3b6',
 'verification/swift-attribution-schema-correction/seal.json':'c00ce1412238f08f176d7983b882c25891cbafd6570c0e489dc4733875935c20',
 'verification/swift-current-attribution-runtime/result-seal.json':'46449fdf0a02fd6c10140803eea197505540f70616f8f0e27174da68ea9619ba',
}
selected={}
def add(path, expected=None):
 p=ROOT/path;s=p.lstat()
 assert stat.S_ISREG(s.st_mode) and not p.is_symlink(),path
 assert s.st_size<100_000_000,path
 h=hashlib.sha256(p.read_bytes()).hexdigest()
 if expected is not None:assert h==expected,(path,h,expected)
 selected[str(p.relative_to(ROOT))]={'sha256':h,'bytes':s.st_size}
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==BASE
assert not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).strip()
for path,expected in SEALS.items():
 add(path,expected);p=ROOT/path;j=json.loads(p.read_text())
 if 'members' in j:
  for name,member in j['members'].items():add(name,member['sha256'])
 else:
  for name,h in j['files'].items():add(str((p.parent/name).relative_to(ROOT)),h)
  for name,h in j.get('externalFiles',{}).items():add(name,h)
for path in ['PLAN.md','STATUS.md','work-graph.json','gates/ga.json']:
 add(path)
for folder in ['verification/current-diagnostic-corrections-root-review','verification/github-ci-7b604864','verification/console-brand-current-check']:
 for p in sorted((ROOT/folder).iterdir()):
  if p.is_file():add(str(p.relative_to(ROOT)))
for name,key,field in [('work-graph.json','packages','state'),('gates/ga.json','gates','status')]:
 prior=json.loads(subprocess.check_output(['git','show',f'{BASE}:{name}'],cwd=ROOT,text=True))
 now=json.loads((ROOT/name).read_text())
 assert [(x['id'],x[field],x.get('reviewer')) for x in prior[key]]==[(x['id'],x[field],x.get('reviewer')) for x in now[key]]
for row in json.loads((ROOT/'verification/github-ci-7b604864/receipt.json').read_text())['observations']:
 assert row['status']=='completed' and row['conclusion']=='success'
 assert all(x['conclusion']=='success' and x['skipped']==0 for x in row['jobs'])
add(str(Path(__file__).resolve().relative_to(ROOT)))
manifest={'schema':1,'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'baseRevision':BASE,'seals':SEALS,'files':dict(sorted(selected.items())),'scope':'Accepted generic iOS correction and host preparation; corrected Swift supplementary schema and one failed full diagnostic; terminal previous CI; branding recheck. Active retention implementation is excluded. Gate states/reviewers unchanged.'}
(OUT/'selection.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
paths=sorted([*selected,str((OUT/'selection.json').relative_to(ROOT))])
(OUT/'paths.nul').write_bytes(b''.join(os.fsencode(x)+b'\0' for x in paths))
print(json.dumps({'selectedFiles':len(paths),'selectedBytes':sum(x['bytes'] for x in selected.values()),'sealedPackets':len(SEALS),'gateStatesUnchanged':True,'previousCITerminalSuccess':True}))
