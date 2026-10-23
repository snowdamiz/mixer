#!/usr/bin/env python3
import datetime, gzip, hashlib, json, pathlib, subprocess
ROOT=pathlib.Path(__file__).resolve().parents[2]
HERE=pathlib.Path(__file__).resolve().parent
INPUTS=['verification/swift-guest-next-execution/2026-10-23-retained-tool/receipt.json','verification/swift-reactor-function-diagnostics/2026-10-23-reactor-final-v2/receipt.json','compiler/experiments/profile-budget/functions/evidence/2026-10-23-command-compatibility-v2/receipt.json']
def sha(data):return hashlib.sha256(data).hexdigest()
records=[];bad=[];missing=[];historical=[]
for rel in INPUTS:
 p=ROOT/rel; data=json.loads(p.read_text());records.append({'path':rel,'sha256':sha(p.read_bytes()),'kind':'receipt'})
 manifest=data.get('source_manifest',data.get('sourceManifest',{}))
 for source,expected in manifest.items():
  file=ROOT/source
  if file.exists() and sha(file.read_bytes())==expected:records.append({'path':source,'sha256':expected,'kind':'current-source'});continue
  rev=data.get('revision',data.get('mixer_revision'))
  r=subprocess.run(['git','show',str(rev)+':'+source],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
  if r.returncode==0 and sha(r.stdout)==expected:historical.append({'path':source,'revision':rev,'sha256':expected})
  else:bad.append({'source':source,'receipt':rel,'expected':expected,'reason':'source digest not current or recorded revision'})
 def walk(value):
  if isinstance(value,dict):
   if isinstance(value.get('path'),str) and isinstance(value.get('sha256'),str):
    path=pathlib.Path(value['path']);choices=[path] if path.is_absolute() else [p.parent/path,ROOT/path]
    candidate=next((x for x in choices if x.is_file()),None)
    if candidate is None:missing.append({'receipt':rel,**value})
    elif sha(candidate.read_bytes())!=value['sha256']:bad.append({'path':str(candidate),'receipt':rel,'reason':'artifact or log hash mismatch','expected':value['sha256'],'actual':sha(candidate.read_bytes())})
    else:records.append({'path':str(candidate),'sha256':value['sha256'],'kind':'bound-file'})
   for child in value.values():walk(child)
  elif isinstance(value,list):
   for child in value:walk(child)
 walk(data)
 if 'all_functions' in data:
  f=data['all_functions'];raw=(p.parent/f['path']).read_bytes();assert sha(raw)==f['gzipSHA256'];assert sha(gzip.decompress(raw))==f['rawSHA256'];records.append({'path':str(p.parent/f['path']),'sha256':sha(raw),'kind':'compressed-and-raw-inventory'})
result={'observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'verified':records,'historical_source_bindings':historical,'missing':missing,'mismatch':bad,'scope':'Root receipt binding audit of final command/reactor diagnostics and exact reactor WASI trace. All are non-authorizing development observations; no complete owned validation/execution or release acceptance.'}
(HERE/'audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'verified':len(records),'historical':len(historical),'missing':missing,'mismatch':bad},indent=2))
raise SystemExit(bool(bad))
