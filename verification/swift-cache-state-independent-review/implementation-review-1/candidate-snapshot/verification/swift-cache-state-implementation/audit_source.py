#!/usr/bin/env python3
"""Exact-input custody, source accounting index and immutable-prefix audit."""
import hashlib,json,pathlib,re,subprocess
from run_host import ROOT,REPO,sha
pack=REPO/'verification/swift-envelope-ci-pack'
manifest=json.loads((pack/'manifest.json').read_text())
assert len(manifest['members'])==86
for m in manifest['members']:
 p=pack/m['path'];assert p.stat().st_size==m['bytes'] and sha(p)==m['sha256'],m['path']
assert sha(pack/'manifest.json')=='4800e90fa39b81d0e6514afa087a77b93f838204883974df7fbbec4c69a21b9a'
bindings=[]
def bind(p,kind,copied=None):
 p=REPO/p
 row={'path':str(p.relative_to(REPO)),'bytes':p.stat().st_size,'sha256':sha(p),'kind':kind}
 if copied:
  q=ROOT/copied;row['owned_copy']=copied;row['owned_copy_sha256']=sha(q)
 bindings.append(row)
for n in ['analyzer.rs','envelope.rs']:
 original=pack/'source/library'/n;new=ROOT/'source/library'/n
 assert new.read_bytes().startswith(original.read_bytes()),n
 bind(str(original.relative_to(REPO)),'unchanged immutable source prefix','source/library/'+n)
for source,target in [('source/producer/tests/fixture_tests.rs','source/tests/fixture_tests.rs'),('source/producer/tests/envelope_tests.rs','source/tests/envelope_tests.rs'),('source/producer/tests/correction_tests.rs','source/tests/correction_tests.rs'),('source/producer/tests/selected_tests.rs','source/tests/selected_tests.rs'),('source/producer/focused_controls.rs','source/focused_controls.rs'),('source/producer/private_io_tests.rs','source/regression/private_io_tests.rs'),('source/producer/inputs/oracle-425.bin','source/inputs/oracle-425.bin'),('source/producer/inputs/oracle-budget-425.bin','source/inputs/oracle-budget-425.bin'),('source/independent/tests/envelope_tests.rs','source/regression/independent/envelope_tests.rs'),('source/independent/tests/caller_cases.rs','source/regression/independent/caller_cases.rs')]:
 assert (pack/source).read_bytes()==(ROOT/target).read_bytes()
 bind(str((pack/source).relative_to(REPO)),'unchanged copied regression input',target)
original=pack/'source/producer/independent_tests.rs';new=ROOT/'source/regression/independent_tests.rs'
assert original.read_text().replace('#[path = "inputs/framing.rs"]','#[path = "../library/analyzer.rs"]')==new.read_text()
bind(str(original.relative_to(REPO)),'test source with only product import path redirected','source/regression/independent_tests.rs')
for p in ['docs/swift-semantic-adapter-prerequisite.md','docs/swift-semantic-adapter-terminal-correction.md','docs/swift-semantic-adapter-terminal-review.md','docs/swift-cache-state-implementation-review-plan.md','verification/swift-semantic-adapter-prerequisite/contract.json','verification/swift-semantic-adapter-prerequisite/source-seams.json','verification/swift-semantic-adapter-root-review/implementation-selection.json','verification/swift-semantic-adapter-root-review/public-getter-selection.json','verification/swift-semantic-adapter-root-review/combined-contract-acceptance.json','verification/swift-cache-state-independent-review/preaccess/actual-file-and-api-plan.json','verification/swift-cache-state-independent-review/preaccess/budget-boundary-plan.json','verification/swift-cache-state-independent-review/preaccess/proof-obligations.json']:
 bind(p,'accepted contract or permitted obligation plan; no independent oracle/test implementation access')
for p in sorted((REPO/'verification/swift-semantic-adapter-prerequisite/inputs').glob('2[3-6]-*')):bind(str(p.relative_to(REPO)),'copied emission source authority only; never an executable harness')
seams=json.loads((REPO/'verification/swift-semantic-adapter-prerequisite/source-seams.json').read_text())
for seam in seams['seams']:
 p=REPO/'verification/swift-semantic-adapter-prerequisite'/seam['snapshot']
 assert sha(p)==seam['source_sha256']
 actual=''.join(p.read_text().splitlines(keepends=True)[seam['first_line']-1:seam['last_line']])
 assert actual==seam['excerpt_utf8'],seam['name']
 assert hashlib.sha256(actual.encode()).hexdigest()==seam['excerpt_sha256']
for p in sorted((pack/'api').glob('*.rs')):
 target=ROOT/'api/inherited'/p.name
 assert target.read_bytes()==p.read_bytes()
 bind(str(p.relative_to(REPO)),'unchanged original API regression input','api/inherited/'+p.name)
(ROOT/'proofs/input-bindings.json').write_text(json.dumps({'accepted_pack_manifest_sha256':sha(pack/'manifest.json'),'accepted_pack_members_verified':86,'bindings':bindings,'no_Patch_Skip_code_or_dependency':True},indent=2)+'\n')
index=[]
for p in sorted((ROOT/'source/library').glob('*.rs')):
 lines=p.read_text().splitlines()
 functions=[]
 for i,l in enumerate(lines):
  m=re.match(r'\s*(?:pub\s+)?(?:const\s+)?fn\s+(\w+)',l)
  if m:functions.append({'name':m[1],'line':i+1})
 index.append({'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p),'functions':functions})
(ROOT/'proofs/source-index.json').write_text(json.dumps({'sources':index,'range_proof':'proofs/source-accounting.md','function_index_only_not_semantic_authorization':True},indent=2)+'\n')
context=subprocess.run(['git','rev-parse','HEAD'],cwd=REPO,capture_output=True,text=True,check=True,timeout=5).stdout.strip()
(ROOT/'proofs/source-audit.json').write_text(json.dumps({'context_revision_only':context,'old_source_prefixes_unchanged':True,'all_86_immutable_input_hashes_verified':True,'source_sha256':{r['path']:r['sha256']for r in index},'native_runtime_or_capture_started':False,'old_pack_unchanged':True,'independent_candidate_acceptance':False},indent=2)+'\n')
print('SOURCE_AUDIT old prefixes exact; all86 input members verified; new closure bound')
