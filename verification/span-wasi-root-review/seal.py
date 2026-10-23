#!/usr/bin/env python3
import datetime, hashlib, json, pathlib, re, subprocess
ROOT=pathlib.Path(__file__).resolve().parents[2];HERE=pathlib.Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
combined=HERE/'combined-2/receipt.json';data=json.loads(combined.read_text());assert data['passed'] and len(data['commands'])==9
verified=[]
for row in data['commands']:
 assert row['exit_code']==0 and row['source_stable'];assert row['source_before']==row['source_after']
 log=combined.parent/row['log'];assert sha(log)==row['log_sha256'];verified.append(str(log.relative_to(ROOT)))
 manifest=combined.parent/('source-'+row['source_after']+'.json');assert sha(manifest)==row['source_after']
 for path,digest in json.loads(manifest.read_text()).items():assert sha(ROOT/path)==digest,path
receipts=['verification/span-execution/receipt.json','verification/swift-wasi/evidence/2026-10-23/receipt.json','verification/next-slice-review/span-receipt.json','verification/next-slice-review/span-repaired-receipt.json','verification/next-slice-review/wasi-receipt.json','verification/span-wasi-root-review/combined-1/receipt.json','verification/span-wasi-root-review/combined-2/receipt.json']
review_changes=[]
for rel in ['verification/next-slice-review/span-repaired-receipt.json','verification/next-slice-review/wasi-receipt.json']:
 r=json.loads((ROOT/rel).read_text())
 for cmd in r['commands']:
  assert cmd['exit_code']==0 and cmd['source_stable'];assert sha(ROOT/cmd['log'])==cmd['log_sha256']
  for path,digest in cmd['source_files'].items():
   current=sha(ROOT/path)
   if current!=digest:review_changes.append({'path':path,'review_digest':digest,'current_digest':current})
assert {x['path'] for x in review_changes} <= {'vm/src/float.rs','vm/tests/span_execution.rs'}
w=json.loads((ROOT/'verification/next-slice-review/wasi-receipt.json').read_text());assert w['wasi_lane_exactly_matches_frozen_receipt']
for path,digest in w['wasi_frozen_sources'].items():assert sha(ROOT/path)==digest
counts={}
for label in ['debug','release','debug-oracles','release-oracles']:
 rows=[tuple(map(int,m)) for m in re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;', (combined.parent/(label+'.log')).read_text())]
 counts[label]=dict(zip(['passed','failed','ignored'],map(sum,zip(*rows))))
result={'observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'status':'Reviewed additive host experiments; combined matrix passed','receipts':{p:sha(ROOT/p) for p in receipts},'current_vm_source_manifest':str(manifest.relative_to(ROOT)),'verified_combined_logs':verified,'test_counts':counts,'review_followups':review_changes,'review_followup_scope':'Root removed drop(non-Drop FunctionPin) from its added regression and rustfmt formatted the existing environment wrapper; full combined suite and focused lint/format subsequently pass. Independent constructor regression passed before these nonsemantic cleanups.','resolved_finding':'Constructor consumes and destroys pre-pinned cache before returning failure; no-owner active_pins now zero, attempted remains one. Original failing sources and D/R logs retained in independent review.','capabilities':'Cache-backed exact frozen v1/v2/v3 execution and separate exact34 Preview1 descriptor/dispatch adapter with explicit grants; no connection between WASI and VM admission or execution.','pending':['Additive full Swift policy and complete validator before execution','Aggregate full-reactor execution/cache/stack/RSS measurement','Native ABI/package and signed app integration','Pinned hosted new-feature CI','Physical iOS/Android (disconnected, not attempted)','Immutable published independent FieldLog consumer and product/GA qualification']}
(HERE/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'counts':counts,'review_followup_files':sorted({x['path'] for x in review_changes}),'status':result['status']}))
