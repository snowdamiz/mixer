#!/usr/bin/env python3
"""Read-only fail-closed exact-source/class/descriptor/BCI evidence gate, format v1."""
from pathlib import Path
import argparse,json,hashlib,sys
from classfile import parse
D=Path(__file__).resolve().parent
SCHEMA='mixer.android.compiled-boundaries.v1';RESULT='mixer.android.compiled-boundary-results.v1'
def decode(p):
 def pairs(items):
  out={}
  for k,v in items:
   if k in out:raise ValueError('duplicate JSON key '+k)
   out[k]=v
  return out
 return json.loads(p.read_bytes(),object_pairs_hook=pairs)
def identity(p):
 if p.is_symlink() or not p.is_file():raise ValueError('nonregular input '+str(p))
 b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def check(args):
 spec=decode(args.map);reference=decode(D/'reference-obligations.json')
 if spec.get('schema')!=SCHEMA or spec.get('source_pair')!='mixer.android-source-pair.5' or spec.get('qualification_status')!='qualified':raise ValueError('missing/stale/unqualified source-pair5 map')
 source_map=spec.get('product_sources')
 if source_map!=reference['exact16_source_map']:raise ValueError('foreign/omitted product source identity')
 for name,wanted in source_map.items():
  if '/' in name or name in ('.','..') or not name.endswith('.java'):raise ValueError('invalid selected source name')
  if identity(args.source_root/name)!=wanted:raise ValueError('source mismatch '+name)
 actualclasses={};parsed={}
 for p in sorted(args.classes.rglob('*.class')):
  if p.is_symlink():raise ValueError('symlink emitted class')
  c=parse(p.read_bytes())
  if c['source_file'] in source_map:
   rel=str(p.relative_to(args.classes));actualclasses[rel]=identity(p);parsed[c['class']]=c
 contextid=digest({'source_map':source_map,'class_map':actualclasses});contexts=spec.get('contexts',[])
 selected=[c for c in contexts if c.get('context_id')==contextid]
 if len(selected)!=1:raise ValueError('absent or duplicate exact compiler/class context '+contextid)
 context=selected[0]
 if context.get('qualification_status')!='qualified' or context.get('class_map')!=actualclasses:raise ValueError('unqualified/foreign emitted class map')
 if set(spec.get('exact_input_connection_descriptors',[]))!=set(reference['exact38_descriptors']) or len(spec.get('exact_input_connection_descriptors',[]))!=38:raise ValueError('InputConnection descriptor set mismatch')
 dispositions=spec.get('historical_dispositions',[])
 if len(dispositions)!=len(reference['historical189_ids']) or {r.get('historical_id') for r in dispositions}!=set(reference['historical189_ids']):raise ValueError('missing/duplicate historical189 disposition')
 if any(r.get('status') not in ('retained','replaced','removed-with-refusal') or not r.get('reason') or not r.get('boundary_ids') for r in dispositions):raise ValueError('unqualified historical semantic disposition')
 boundaries=context.get('boundaries',[]);byid={r.get('id'):r for r in boundaries}
 if None in byid or len(byid)!=len(boundaries) or not boundaries:raise ValueError('empty/duplicate active boundary IDs')
 tags=set(t for b in boundaries for t in b.get('subjects',[]))
 if not set(reference['mandatory_subjects'])<=tags:raise ValueError('omitted direct/field/lifecycle/cleanup/replacement/membership subject')
 for b in boundaries:
  caller=b.get('caller',{});cl=parsed.get(caller.get('class'))
  if cl is None:raise ValueError('absent caller class')
  source=cl['source_file'];p=args.classes/(cl['class']+'.class')
  if caller.get('class_sha256')!=identity(p)['sha256'] or caller.get('source_sha256')!=source_map[source]['sha256']:raise ValueError('foreign source/class hash')
  ms=[m for m in cl['methods'] if m['name']==caller.get('method') and m['descriptor']==caller.get('descriptor')]
  if len(ms)!=1:raise ValueError('wrong caller/overload descriptor')
  ins=[i for i in ms[0]['instructions'] if i['bci']==caller.get('bci')]
  if len(ins)!=1 or not 0xb6<=ins[0]['opcode']<=0xba or ins[0]['mnemonic']!=caller.get('opcode') or ins[0].get('target')!=caller.get('callee'):raise ValueError('wrong BCI/opcode/callee')
  if not b.get('required_states') or len(set(b['required_states']))!=len(b['required_states']):raise ValueError('missing/duplicate required state obligations')
  if b.get('evidence_kind')!='executable-host-qualified':raise ValueError('source-only/native-pending boundary overclaim')
 if any(bid not in byid for d in dispositions for bid in d['boundary_ids']):raise ValueError('historical disposition references absent active boundary')
 v1=spec.get('v1_baselines',[])
 if len(v1)!=5 or len(set(v1))!=5 or any(v not in byid for v in v1):raise ValueError('missing separate exact five V1 positives')
 result=decode(args.matrix)
 if result.get('schema')!=RESULT or result.get('context_id')!=contextid or result.get('status')!='passed' or result.get('product_sources')!=source_map or result.get('class_map')!=actualclasses:raise ValueError('stale/foreign/failed matrix context')
 expected={(b['id'],s) for b in boundaries for s in b['required_states']};actual=set()
 for row in result.get('rows',[]):
  key=(row.get('boundary_id'),row.get('state'))
  if key in actual or key not in expected:raise ValueError('duplicate/unknown matrix row')
  actual.add(key);b=byid[key[0]]
  if row.get('status')!='passed' or row.get('evidence_kind')!='executed-host' or row.get('hit',0)<=0 or row.get('caller')!=b['caller']:raise ValueError('unexecuted/zero-hit/wrong-caller matrix row')
  if row.get('expected')!=row.get('observed'):raise ValueError('state expected/observed mismatch')
  if not row.get('original_authority') or not row.get('receiver_identity') or not row.get('production_frames') or not row.get('native_event_jni_sequence') or not row.get('cleanup_fatal_disposition'):raise ValueError('missing authority/frame/sequence/failure-state subject')
  if row.get('unsupported_successor_authority',False):raise ValueError('unsupported successor authority claim')
 if actual!=expected:raise ValueError('incomplete active state coverage')
 return {'status':'passed-exact-host-qualified-matrix','context_id':contextid,'boundaries':len(boundaries),'states':len(actual),'historical_V2_dispositions':len(dispositions),'separate_V1_positive_sites':5,'scope':'Host controlled-leaf source/class/state join only; native/OTA/GA remain separate'}
def main():
 p=argparse.ArgumentParser();p.add_argument('--map',type=Path,required=True);p.add_argument('--source-root',type=Path,required=True);p.add_argument('--classes',type=Path,required=True);p.add_argument('--matrix',type=Path,required=True);p.add_argument('--output',type=Path);args=p.parse_args()
 try:receipt=check(args);code=0
 except (ValueError,KeyError,TypeError,AssertionError,OSError) as e:receipt={'status':'refused','reason':str(e),'native_OTA_GA_authorized':False};code=2
 text=json.dumps(receipt,indent=2)+'\n'
 if args.output:args.output.write_text(text)
 sys.stdout.write(text);raise SystemExit(code)
if __name__=='__main__':main()
