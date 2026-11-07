#!/usr/bin/env python3
"""Closed compiled identity auditor. Compiled/observed identity never grants behavior credit."""
from pathlib import Path
import json,hashlib,collections,copy,gzip,zipfile,sys,datetime
from classfile import parse
D=Path(__file__).resolve().parent

def ident(p):b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2)+'\n')
def stable(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def categories(source,cls,method):
 out=[]
 if source=='NativeEditorConnectionV2.java':out.append('direct-editor')
 if source=='NativeAppearanceViewsV2.java':
  if any(s in cls for s in ('$NativeField','$FieldPreservation','$EditorLease','$Record','$Mutation')):out.append('field-authority')
 if any(s in cls+method for s in ('Preservation','preservation','editorLoss','LossObservation')):out.append('field-preservation')
 if any(s in cls+method for s in ('Replacement','replacement')):out.append('replacement-event')
 if any(s in cls+method for s in ('PreservationMembership','Membership','membership')):out.append('membership')
 if any(s in method for s in ('Focus','Visibility','Attached','Detached','Resume','Pause','loss','Loss','lifecycle')):out.append('lifecycle')
 if any(s in cls+method for s in ('leanup','leanup','drain','Drain','retire','Retire','close','Close','finish','Finish','failed','Failure','failure','scrub','Scrub')):out.append('cleanup-failure')
 if source=='NativeRenderer.java':out.append('renderer')
 if not out:out.append('selected-product-support')
 return sorted(set(out))
def inventory(mode, E=None):
 E=E if E is not None else D/'runs'/mode;classes=[];sources={p.name:p for p in (D/'inputs/accepted/source').glob('*.java')};rows=[]
 for p in sorted((E/'classes/dev/mixer/android').glob('*.class')):
  c=parse(p.read_bytes())
  if c['source_file'] not in sources:continue
  source=sources[c['source_file']];c['file']=str(p.relative_to(D));c['file_identity']=ident(p);c['source']=str(source.relative_to(D));c['source_identity']=ident(source);lines=source.read_text().splitlines();classes.append(c)
  for m in c['methods']:
   for i in m['instructions']:
    if not 0xb6<=i['opcode']<=0xba:continue
    identity={'source':c['source'],'source_sha256':c['source_identity']['sha256'],'class':c['class'],'class_sha256':c['file_identity']['sha256'],'method':m['name'],'descriptor':m['descriptor'],'bci':i['bci'],'opcode':i['mnemonic'],'target':i['target']}
    rows.append({'id':'site-'+stable(identity)[:32],**identity,'source_line':i['line'],'source_line_text':lines[i['line']-1] if i['line'] and i['line']<=len(lines) else None,'synthetic_method':bool(m['access']&0x1000),'bootstrap':i.get('bootstrap'),'categories':categories(c['source_file'],c['class'],m['name']),'evidence_kind':'compiled-identity-only','behavior_state_coverage':'pending-site-specific-qualification'})
 assert set(c['source_file'] for c in classes)==set(sources),('omitted product source',set(sources)-set(c['source_file'] for c in classes))
 return {'schema':1,'mode':mode,'product_tree':json.loads((D/'inputs/accepted/source-verification.json').read_bytes())['product_tree'],'source_map':{k:ident(v) for k,v in sorted(sources.items())},'classes':classes,'rows':rows}
def validate_map(actual,oracle):
 assert actual['source_map']==oracle['source_map'],'foreign source map'
 assert actual['product_tree']==oracle['product_tree'],'foreign product tree'
 assert len({r['id'] for r in actual['rows']})==len(actual['rows']),'duplicate id'
 assert {r['id'] for r in actual['rows']}=={r['id'] for r in oracle['rows']},'missing/extra active id'
 originals={r['id']:r for r in oracle['rows']}
 for r in actual['rows']:assert r==originals[r['id']],'identity/claim mismatch'
 assert actual['classes']==oracle['classes'],'foreign/missing emitted classes'
def descriptors(cross):
 jar=Path('/opt/homebrew/share/android-commandlinetools/platforms/android-37.0/android.jar')
 with zipfile.ZipFile(jar) as z:inputc=parse(z.read('android/view/inputmethod/InputConnection.class'))
 expected={m['name']+m['descriptor'] for m in inputc['methods'] if not m['access']&0x0008 and m['name'] not in ('<init>','<clinit>')};assert len(expected)==38
 # Independent authored exact set from frozen reviewer shape oracle, not a count-derived SDK selection.
 text=(D/'inputs/accepted/tests/DescriptorClosure.java').read_text();start=text.index('Set.of(');end=text.index('\n    );',start);import re
 authored=set(re.findall(r'"([^"]+)"',text[start:end]));assert authored==expected,('SDK38 exact descriptor set drift',authored^expected)
 byclass={c['class']:c for c in cross['classes']};resolution=[];current='dev/mixer/android/NativeEditorConnectionV2$Api34';visited=[]
 while current!='java/lang/Object':
  assert current.startswith('dev/mixer/android/NativeEditorConnectionV2$') and current not in visited;visited.append(current);current=byclass[current]['super']
 for key in sorted(expected):
  matches=[(name,m) for name in visited for m in byclass[name]['methods'] if m['name']+m['descriptor']==key]
  assert len(matches)==1,(key,matches)
  name,m=matches[0];assert not m['access']&0x0400 and m['access']&1 and m['instructions'];calls=[i for i in m['instructions'] if 0xb6<=i['opcode']<=0xba]
  closure=[];todo=[(name,m)];seen=set()
  while todo:
   cl,mm=todo.pop();mk=(cl,mm['name'],mm['descriptor'])
   if mk in seen:continue
   seen.add(mk)
   for i in mm['instructions']:
    if 0xb6<=i['opcode']<=0xba:
     t=i['target'];closure.append({'caller':cl,'method':mm['name'],'descriptor':mm['descriptor'],'bci':i['bci'],'target':t})
     if i.get('bootstrap'):
      for a in i['bootstrap']['arguments']:
       if a.get('owner') in visited:
        nm=next(v for v in byclass[a['owner']]['methods'] if v['name']==a['name'] and v['descriptor']==a['descriptor']);todo.append((a['owner'],nm))
     if t['owner'] in visited:
      nm=next((v for v in byclass[t['owner']]['methods'] if v['name']==t['name'] and v['descriptor']==t['descriptor']),None)
      if nm:todo.append((t['owner'],nm))
  assert not any('InputConnectionWrapper' in c['target']['owner'] for c in closure)
  resolution.append({'descriptor':key,'declaring_class':name,'class_sha256':byclass[name]['file_identity']['sha256'],'source_sha256':byclass[name]['source_identity']['sha256'],'method_access':m['access'],'dispatch':'concrete-authored-no-default-or-platform-inheritance','compiled_lambda_helper_closure':closure,'execution':'exact host descriptor refusal suite separate; SDK type linkage compilation only'})
 return {'sdk_jar':str(jar),'sdk_jar_identity':ident(jar),'sdk_interface_sha256':hashlib.sha256(zipfile.ZipFile(jar).read('android/view/inputmethod/InputConnection.class')).hexdigest(),'expected_exact_set':sorted(expected),'authored_exact_set_equal':True,'adapter_chain':visited,'resolution':resolution,'runtime_API31_33_34_linkage':'pending native runtime; API-specific class references compiled against SDK37; SDK36 runtime guards unchanged'}
def trace_worker(f):
 inv=json.loads((D/'host-class-inventory.json').read_bytes());index={(r['class'].replace('/','.'),r['method'],r['descriptor'],r['bci']):r for r in inv['rows']};seen={};bad=[];noninvoke=[];v1=set();events=frames=0
 allinstructions={(c['class'].replace('/','.'),m['name'],m['descriptor'],i['bci']):i for c in inv['classes'] for m in c['methods'] for i in m['instructions']}
 op=gzip.open if f.suffix=='.gz' else open
 with op(f,'rt') as stream:
  for line in stream:
   e=json.loads(line);events+=1
   for frame in e['frames']:
    key=(frame['class'],frame['method'],frame['descriptor'],frame['bci']);r=index.get(key)
    if not r:
     if key in allinstructions:noninvoke.append({'sequence':e['sequence'],'frame':frame,'instruction':allinstructions[key]})
     else:bad.append({'file':str(f.relative_to(D)),'sequence':e['sequence'],'frame':frame})
     continue
    frames+=1;s=seen.setdefault(r['id'],{'events':0,'entry':0,'beforeReturn':0,'commands':[f.name.split('.events')[0]],'first':None,'native_methods':set()});s['events']+=1;s[e['phase']]=s.get(e['phase'],0)+1;s['native_methods'].add(e['method'])
    if s['first'] is None:s['first']={'file':str(f.relative_to(D)),'sequence':e['sequence'],'native_method':e['method'],'phase':e['phase'],'authority_snapshot':e['authority'],'full_production_frames':e['frames']}
    if f.name.startswith('v1-original-five') and frame['class']=='dev.mixer.android.NativeRenderer' and frame['method']=='children' and e['method'] in ('ViewGroup.removeViewAt','ViewGroup.addView','MarginLayoutParams.setMarginEnd','View.setLayoutParams'):v1.add(r['id'])
 for s in seen.values():s['native_methods']=sorted(s['native_methods'])
 save(D/'trace-audits'/(f.name+'.json'),{'trace':str(f.relative_to(D)),'events':events,'joined_production_frames':frames,'identity':ident(f),'seen':seen,'bad':bad,'noninvoke_frames':noninvoke,'v1':sorted(v1)})

def observations(inv):
 import subprocess,time
 seen={};counts={};bad=[];v1=set();noninvoke=0;commands=[]
 for f in sorted((D/'runs/host-2').glob('*.events.jsonl*')):
  target=D/'trace-audits'/(f.name+'.json');start=time.monotonic();argv=[sys.executable,str(D/'audit.py'),'trace',str(f)]
  if not target.exists():
   result=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=60,check=False);assert result.returncode==0,(f,result.stderr.decode())
   commands.append({'argv':argv,'exit':result.returncode,'elapsed_seconds':time.monotonic()-start,'stdout':result.stdout.decode(),'stderr':result.stderr.decode(),'reaped':True,'timeout_seconds':60})
  j=json.loads(target.read_bytes());assert j['identity']==ident(f);counts[j['trace']]={k:j[k] for k in ('events','joined_production_frames','identity')};bad.extend(j['bad']);noninvoke+=len(j['noninvoke_frames']);v1.update(j['v1'])
  for sid,v in j['seen'].items():
   if sid not in seen:seen[sid]=v;continue
   dest=seen[sid]
   for key in ('events','entry','beforeReturn'):dest[key]+=v[key]
   dest['commands']=sorted(set(dest['commands']+v['commands']));dest['native_methods']=sorted(set(dest['native_methods']+v['native_methods']))
  print(f.name,j['events'],'events',flush=True)
 save(D/'trace-audit-commands.json',commands)
 assert not bad,('runtime frame not an exact instruction BCI',bad[:5]);assert len(v1)==5,('original V1 controls not five distinct compiled sites',v1)
 result=[{'site_id':sid,**s,'credit':'actual controlled-host invocation identity observed; behavioral assertions remain at command scope; not seven-state site qualification'} for sid,s in sorted(seen.items())]
 return {'trace_files':counts,'observed_sites':result,'v1_five_site_ids':sorted(v1),'unmatched_frames':bad,'non_invocation_initialization_frames':noninvoke,'native_runtime':False}
def historical(inv):
 old=json.loads((D/'inputs/protocol/barrier-map.json').read_bytes())['records'];sourcebyname={Path(k).name:k for k in (r['source'] for r in inv['rows'])};rows=[]
 for r in old:
  name=Path(r['source']).name;text=r['candidates'][0]['text'];source=D/sourcebyname[name];lines=source.read_text().splitlines();found=[i for i,line in enumerate(lines,1) if text in line];targetname=text.split('(')[0].split('.')[-1].split()[-1];possible=[a['id'] for a in inv['rows'] if Path(a['source']).name==name and a['source_line'] in found and (a['target']['name']==targetname or targetname.startswith('new '))]
  # Explicit replacements of obsolete forwarding calls; call identities are fresh parsed classfile identities.
  replacements=[]
  if r['baseline'].startswith('introduced:') and 'InputConnection.' in r['baseline']:
   method=r['baseline'].split('.')[-1];replacements=[a['id'] for a in inv['rows'] if 'direct-editor' in a['categories'] and (a['method']==method or a['method'].startswith('lambda$'+method+'$'))]
  rows.append({'historical_id':r['baseline'],'historical_map_identity':ident(D/'inputs/protocol/barrier-map.json'),'historical_source_expression':text,'suggested_current_lines':found,'exact_current_compiled_site_ids':possible,'direct_adapter_replacement_site_ids':replacements,'disposition':'replaced-direct-adapter-identity-proposal' if replacements else 'retained-compiled-identity-proposal' if possible else 'requires-semantic-disposition','review_status':'root-independent-semantic-and-state-review-pending','text_match_grants_behavior_credit':False})
 assert len({r['historical_id'] for r in rows})==189
 return {'old_V2_record_count':len(rows),'introduced_V2_record_count':sum(r['historical_id'].startswith('introduced:') for r in rows),'separate_V1_control_count':5,'records':rows,'all_historical_rows_preserved':True}
def mutations(inv,obs):
 def reject(name,fn):
  x=copy.deepcopy(inv);fn(x)
  try:validate_map(x,inv)
  except AssertionError as e:return {'name':name,'rejected':True,'reason':str(e)}
  raise AssertionError('mutation accepted '+name)
 out=[]
 changes={'foreign-source-hash':lambda x:x['rows'][0].update(source_sha256='0'*64),'foreign-class-hash':lambda x:x['rows'][0].update(class_sha256='0'*64),'wrong-method-descriptor':lambda x:x['rows'][0].update(descriptor='(Ljava/lang/Foreign;)V'),'between-instructions-bci':lambda x:x['rows'][0].update(bci=x['rows'][0]['bci']+1),'bci-zero-substitution':lambda x:x['rows'][0].update(bci=0),'wrong-caller-class':lambda x:x['rows'][0].update(**{'class':'dev/mixer/android/Foreign'}),'wrong-caller-method':lambda x:x['rows'][0].update(method='foreign'),'wrong-opcode':lambda x:x['rows'][0].update(opcode='invokestatic' if x['rows'][0]['opcode']!='invokestatic' else 'invokeinterface'),'wrong-callee':lambda x:x['rows'][0]['target'].update(name='foreign'),'missing-active-id':lambda x:x['rows'].pop(),'duplicate-active-id':lambda x:x['rows'].append(copy.deepcopy(x['rows'][0])),'missing-emitted-class':lambda x:x['classes'].pop(),'remove-direct-editor-subject':lambda x:x.update(rows=[r for r in x['rows'] if 'direct-editor' not in r['categories']]),'remove-field-subject':lambda x:x.update(rows=[r for r in x['rows'] if 'field-preservation' not in r['categories']]),'remove-membership-subject':lambda x:x.update(rows=[r for r in x['rows'] if 'membership' not in r['categories']]),'stale-historical-row':lambda x:x['rows'][0].update(id='NativeRenderer:L101:C57:1'),'source-only-overclaim':lambda x:x['rows'][0].update(evidence_kind='executed-seven-state-qualified'),'unsupported-successor-overclaim':lambda x:x['rows'][0].update(behavior_state_coverage='successor-authorized')}
 for name,fn in changes.items():out.append(reject(name,fn))
 oracle={r['id']:r for r in inv['rows']};sample=next(o for o in obs['observed_sites'] if sum(a['class']==oracle[o['site_id']]['class'] and a['method']==oracle[o['site_id']]['method'] and a['descriptor']==oracle[o['site_id']]['descriptor'] for a in inv['rows'])>1);r=oracle[sample['site_id']];neighbor=next(a for a in inv['rows'] if a['class']==r['class'] and a['method']==r['method'] and a['descriptor']==r['descriptor'] and a['bci']!=r['bci'])
 def validate_evidence(row):
  assert row==sample,'evidence caller/neighbor/phase/hit/state claim changed';assert row['events']>0
 for name,field,value in [('zero-hit','events',0),('wrong-caller-row','site_id','site-foreign'),('neighbor-hook-substitution','site_id',neighbor['id']),('unrun-complete-state-coverage','credit','seven-state-qualified')]:
  x=copy.deepcopy(sample);x[field]=value
  try:validate_evidence(x)
  except AssertionError as e:out.append({'name':name,'rejected':True,'reason':str(e),'neighbor_site_id':neighbor['id'] if 'neighbor' in name else None})
  else:raise AssertionError('evidence mutation accepted')
 return {'controls':out,'scope':'integrity rejection only; does not prove behavioral correctness or authorize OTA','every_control_rejected':all(v['rejected'] for v in out)}
def main():
 host=inventory('host-2');cross=inventory('cross-1');save(D/'host-class-inventory.json',host);save(D/'sdk-class-inventory.json',cross);validate_map(host,inventory('host-2'));validate_map(cross,inventory('cross-1'));desc=descriptors(cross);save(D/'exact-descriptor-set.json',desc);obs=observations(host);save(D/'observed-callers.json',obs);history=historical(host);save(D/'historical-dispositions.json',history);controls=mutations(host,obs);save(D/'integrity-mutation-controls.json',controls)
 observed={r['site_id'] for r in obs['observed_sites']};categories_count=collections.Counter(c for r in host['rows'] for c in r['categories']);observed_count=collections.Counter(c for r in host['rows'] if r['id'] in observed for c in r['categories'])
 save(D/'audit-receipt.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'compiled-inventory-and-observed-caller-identity-pass; full-site-state-qualification-pending','host_classes':len(host['classes']),'host_invocation_sites':len(host['rows']),'sdk_classes':len(cross['classes']),'sdk_invocation_sites':len(cross['rows']),'source_members':len(host['source_map']),'observed_host_invocation_sites':len(observed),'unobserved_host_invocation_sites':len(host['rows'])-len(observed),'categories_compiled':dict(categories_count),'categories_observed':dict(observed_count),'exact_sdk_descriptors':len(desc['expected_exact_set']),'v1_separate_positive_sites':len(obs['v1_five_site_ids']),'historical_V2_records':len(history['records']),'historical_semantic_dispositions_pending':sum(r['disposition']=='requires-semantic-disposition' for r in history['records']),'integrity_mutations_rejected':len(controls['controls']),'native_runtime_OTA_GA_accepted':False,'limits':['Observed compiled frames are not full executable per-boundary seven-state matrix','New membership allocation-failure remains source/bytecode only without exact OOME injection','Separate new independent state review and missing historical semantic dispositions remain pending','No native ART, IME, UI, device, accessibility/OEM or API-specific linkage execution','No Swift/JNI app compilation, CLI profile integration, immutable FieldLog, public V2 or GA qualification']})
 print(json.dumps(json.loads((D/'audit-receipt.json').read_bytes()),indent=2))
if __name__=='__main__':
 if len(sys.argv)>1 and sys.argv[1]=='trace':trace_worker(Path(sys.argv[2]))
 else:main()
