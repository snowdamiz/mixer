#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,sys
O=Path(__file__).resolve().parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
c=json.loads((O/'collection.json').read_text())
source_identity=sha(json.dumps(c['sources'],sort_keys=True,separators=(',',':')).encode())
receipt={
 'schema':1,'at':datetime.now(timezone.utc).isoformat(),'python':sys.version,
 'scope':'Frozen source audit, official SDK metadata/interface inspection and finite extracted-source JVM dispatch witnesses only',
 'source_tree_digest':source_identity,'source_tree_digest_definition':'SHA256 of sorted-key compact JSON of ordered collection.json sources list; 22 frozen named inputs',
 'context_head_supplied_by_root_only':'a24011487bfc368512fa52125241d9c46e7cdd3f',
 'canonical_views_sha256':'a217d0b178869f3e5c3fc2d80f30f559a22c76a303195e62bfcb73d3cce91cce',
 'tools':{'Python':c['python'],'javap':(O/'logs/javap-1.stdout.txt').read_text().strip(),'javac':(O/'logs/probe-1.stdout.txt').read_text().strip(),'java':(O/'logs/probe-2.stderr.txt').read_text().strip()},
 'commands':[
 {'command':'python3 verification/android-inputconnection-authority-audit/scripts/collect.py','exit':0,'stdout':'logs/collect.stdout.txt','stderr':'logs/collect.stderr.txt'},
 {'command':'python3 verification/android-inputconnection-authority-audit/scripts/index.py','exit':1,'attempt':1,'stderr':'logs/index-attempt1.stderr.txt','failure':'asserted 39 before official enumeration established 38'},
 {'command':'python3 verification/android-inputconnection-authority-audit/scripts/index.py','exit':1,'attempt':2,'stderr':'logs/index-attempt2.stderr.txt','failure':'asserted 25 before exact override count established 24'},
 {'command':'python3 verification/android-inputconnection-authority-audit/scripts/index.py','exit':0,'stdout':'logs/index.stdout.txt','stderr':'logs/index.stderr.txt'},
 {'command':'python3 verification/android-inputconnection-authority-audit/scripts/probe.py','exit':1,'attempt':1,'stderr':'logs/probe-attempt1-compile.stderr.txt','failure':'SDK jar lacks public platform-internal source annotations'},
 {'command':'python3 verification/android-inputconnection-authority-audit/scripts/probe.py','exit':1,'attempt':2,'stderr':'logs/probe-attempt2-compile.stderr.txt','failure':'javap signatures need Java parameter names in descriptor leaf'},
 {'command':'python3 verification/android-inputconnection-authority-audit/scripts/probe.py','exit':0,'stdout':'logs/probe.stdout.txt','stderr':'logs/probe.stderr.txt','details':'probe-receipt.json'},
 {'command':'python3 verification/android-inputconnection-authority-audit/scripts/extend_official.py','exit':0,'stdout':'logs/extend-official.stdout.txt','stderr':'logs/extend-official.stderr.txt'},
 {'command':'python3 verification/android-inputconnection-authority-audit/scripts/source_index.py','exit':0,'stdout':'logs/source-index.stdout.txt','stderr':'logs/source-index.stderr.txt'},
 {'command':'python3 verification/android-inputconnection-authority-audit/scripts/check.py','exit':0,'stdout':'logs/check.stdout.txt','stderr':'logs/check.stderr.txt'}],
 'navigation_failures':[{'command':'/usr/libexec/java_home','exit':1,'failure':'No registered Java Runtime; existing explicit Homebrew OpenJDK27 used'},{'command':'rg --files core','exit':2,'failure':'No core directory; named native OwnerLifecycleV2 source found directly'}, {'tool':'web open official googlesource wrapper','failure':'Web parser inaccessible; direct official format=TEXT fetch succeeded with original source bytes retained'}],
 'results':{'interface_descriptors':38,'explicit_descriptors':24,'inherited_descriptors':14,'extracted_host_checks':26,'negative_packet_controls':8,'new_restrictions_selected':0,'implementation_changes':0,'native_runtime_or_capture_launches':0},
 'cleanup':'All owned host children reaped by subprocess.run. No native/capture or process inventory; no owned native cleanup required. Other projects untouched.',
 'provenance':'provenance.md; unmodified Apache-2.0 AOSP reference source oracle, exact production spans and finite authored host leaves distinguished. Root dependency registration action recorded, no package installed.',
 'limits':'No Android native effects, classloading/runtime, remote exploit, API28-35/public V2, OTA, published FieldLog, physical matrix, or GA acceptance. Ordered native delegate disposal and asynchronous authority remain required contracts.'}
(O/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
exclude={'seal.json','logs/seal.stdout.txt','logs/seal.stderr.txt','logs/seal-check.stdout.txt','logs/seal-check.stderr.txt'}
members=[]
for p in sorted(O.rglob('*')):
 if not p.is_file():continue
 rel=str(p.relative_to(O))
 if rel in exclude:continue
 b=p.read_bytes();members.append({'path':rel,'bytes':len(b),'sha256':sha(b)})
seal={'schema':1,'scope':'Final finite evidence packet; no product/native/release acceptance','source_tree_digest':source_identity,'members':members,'exclusions':sorted(exclude)}
(O/'seal.json').write_text(json.dumps(seal,indent=2)+'\n')
print(json.dumps({'seal_sha256':sha((O/'seal.json').read_bytes()),'members':len(members),'bytes':sum(x['bytes'] for x in members),'source_tree_digest':source_identity},indent=2))
