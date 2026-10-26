#!/usr/bin/env python3
"""Exact compiled identity + immutable semantic policy + fresh typed execution certificate."""
from pathlib import Path
import argparse,json,hashlib,sys
from classfile import parse
from structured_rows import validate,need
D=Path(__file__).resolve().parent
APPROVED_BINDING_SHA256='ca028fbcea1379dddb7c375d46c5af51c9c2274706ad2146e68bad38794a5a65'
REFERENCE_OBLIGATIONS_SHA256='e682c9f702a6559256819a2f8f11c6cda02e1388074faafca727bba0f0b779dd'
def decode(p):
 def pairs(items):
  out={}
  for k,v in items:
   if k in out:raise ValueError('duplicate JSON key '+k)
   out[k]=v
  return out
 return json.loads(p.read_bytes(),object_pairs_hook=pairs)
def identity(p):
 need(p.is_file() and not p.is_symlink(),'nonregular input '+str(p));b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def check(a):
 need(identity(D/'approved-policy-binding.json')['sha256']==APPROVED_BINDING_SHA256,'altered approved policy/context binding source closure');need(identity(D/'reference-obligations.json')['sha256']==REFERENCE_OBLIGATIONS_SHA256,'altered reference-obligations source closure');approved=decode(D/'approved-policy-binding.json');need(identity(a.policy)['sha256']==approved['policy_sha256'],'foreign semantic policy');need(approved.get('root_selected') is True,'semantic policy remains draft; no qualified producer/map accepted');policy=decode(a.policy);reference=decode(D/'reference-obligations.json');need(policy.get('schema')=='mixer.android.semantic-boundary-policy.v2','policy schema');need(policy.get('source_pair')=='mixer.android-source-pair.5','source-pair policy')
 sources=policy.get('product_sources');need(sources==reference['exact16_source_map'],'foreign/omitted exact16 source identity')
 for name,wanted in sources.items():need(identity(a.source_root/name)==wanted,'selected source mismatch '+name)
 need(type(policy.get('exact_input_connection_descriptors')) is list and len(policy['exact_input_connection_descriptors'])==38 and set(policy['exact_input_connection_descriptors'])==set(reference['exact38_descriptors']),'exact SDK descriptor set mismatch')
 historical=policy.get('historical_dispositions');need(type(historical) is list and len(historical)==189 and {r.get('historical_id') for r in historical}==set(reference['historical189_ids']),'independent policy missing/duplicate historical189 disposition')
 need(type(policy.get('v1_baselines')) is list and len(policy['v1_baselines'])==5 and len(set(policy['v1_baselines']))==5,'independent policy missing exact five V1 IDs')
 parsed={};classes={}
 for p in sorted(a.classes.rglob('*.class')):
  need(not p.is_symlink(),'symlink class');c=parse(p.read_bytes())
  if c['source_file'] in sources:need(c['class'] not in parsed,'duplicate class identity');parsed[c['class']]=c;classes[str(p.relative_to(a.classes))]=identity(p)
 contextid=digest({'source_map':sources,'class_map':classes});need(contextid in approved['approved_context_map_hashes'],'unreviewed compiled context');need(identity(a.map)['sha256']==approved['approved_context_map_hashes'][contextid],'foreign exact context-map hash; no coherent caller/row substitution');context=decode(a.map);need(context.get('schema')=='mixer.android.compiled-boundary-context.v2' and context.get('context_id')==contextid and context.get('class_map')==classes,'unknown/foreign class context; no remap waiver');need(context.get('policy_sha256')==approved['policy_sha256'],'context foreign semantic policy')
 need(context.get('identity_review_status')=='reviewed-exact-context','unreviewed exact compiler context')
 bindings=context.get('boundaries');need(type(bindings) is list,'context bindings list')
 for b in bindings:
  call=b.get('caller',{});cl=parsed.get(call.get('class'));need(cl is not None,'missing emitted caller class');need(call.get('source_sha256')==sources[cl['source_file']]['sha256'] and call.get('class_sha256')==classes[cl['class']+'.class']['sha256'],'foreign source/class hash');methods=[m for m in cl['methods'] if m['name']==call.get('method') and m['descriptor']==call.get('descriptor')];need(len(methods)==1,'wrong method/descriptor');ins=[i for i in methods[0]['instructions'] if i['bci']==call.get('bci')];need(len(ins)==1 and 0xb6<=ins[0]['opcode']<=0xb9 and ins[0]['mnemonic']==call.get('opcode') and ins[0].get('target')==call.get('callee'),'wrong BCI/opcode/callee')
 matrix=decode(a.matrix);need(matrix.get('schema')=='mixer.android.compiled-boundary-results.v2' and matrix.get('context_id')==contextid and matrix.get('policy_sha256')==approved['policy_sha256'] and matrix.get('class_map')==classes and matrix.get('product_sources')==sources,'foreign/stale execution certificate');summary=validate(policy,context,matrix)
 # Every reported product frame is checked at an actual instruction boundary in the exact emitted method.
 for row in matrix['rows']:
  for f in row['production_frames']:
   c=parsed.get(f['class']);need(c is not None,'foreign production frame class');ms=[m for m in c['methods'] if m['name']==f['method'] and m['descriptor']==f['descriptor']];need(len(ms)==1 and any(i['bci']==f['bci'] for i in ms[0]['instructions']),'foreign frame descriptor/BCI')
 return {'status':'passed-exact-host-qualified-matrix','context_id':contextid,'policy_sha256':approved['policy_sha256'],**summary,'scope':'fresh typed host execution certificate; no native/OTA/GA authority'}
def main():
 p=argparse.ArgumentParser();p.add_argument('--policy',required=True,type=Path);p.add_argument('--map',required=True,type=Path);p.add_argument('--source-root',required=True,type=Path);p.add_argument('--classes',required=True,type=Path);p.add_argument('--matrix',required=True,type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
 try:r=check(a);code=0
 except (ValueError,KeyError,TypeError,AssertionError,OSError) as e:r={'status':'refused','reason':str(e),'native_OTA_GA_authorized':False};code=2
 s=json.dumps(r,indent=2)+'\n'
 if a.output:a.output.write_text(s)
 sys.stdout.write(s);raise SystemExit(code)
if __name__=='__main__':main()
