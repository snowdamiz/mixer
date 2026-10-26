"""Supplement independent manual source review with exact bytecode/custody checks."""
from pathlib import Path
import hashlib,json,re,difflib,datetime
D=Path(__file__).resolve().parent;OLD=D.parent/'preaccess/old-source'
def ident(p):b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def mapping(p):return {str(q.relative_to(p)):ident(q) for q in sorted(p.rglob('*')) if q.is_file()}
def method_source(s,signature):
 start=s.index(signature);opening=s.index('{',start);depth=0
 for i in range(opening,len(s)):
  if s[i]=='{':depth+=1
  if s[i]=='}':
   depth-=1
   if depth==0:return s[start:i+1]
 raise AssertionError(signature)
def bytecode_method(text,prefix):
 lines=text.splitlines();a=next(i for i,l in enumerate(lines) if l.startswith(prefix));b=next((i for i in range(a+1,len(lines)) if (lines[i].startswith('  ') and not lines[i].startswith('    ') and lines[i].strip()) or lines[i]=='}'),len(lines))
 selected=lines[a:b];instructions=[]
 for l in selected:
  m=re.match(r'\s+(\d+):\s+(\S+)(.*)',l)
  if m:instructions.append({'offset':int(m[1]),'op':m[2],'rest':m[3].strip(),'raw':l})
 return selected,instructions
source=(D/'frozen/source/NativeRenderer.java').read_text();old=(OLD/'source/NativeRenderer.java').read_text()
assert method_source(source,'public void fieldPreservationBegin(')==method_source(old,'public void fieldPreservationBegin(')
assert method_source(source,'void finishV2(').split('// No call, allocation, throwing guard, reporter, getter or callback below this boundary.')[1]==method_source(old,'void finishV2(').split('// No call, allocation, throwing guard, reporter, getter or callback below this boundary.')[1]
assert source.count('new NativeState(')==1 and source.count('new PreservationMembership(')==1
assert len(re.findall(r'state\.membership\s*=',source))==1
save(D/'independent-source-delta.json',{'changed_product_files':[p.name for p in (D/'frozen/source').glob('*.java') if p.read_bytes()!=(OLD/'source'/p.name).read_bytes()],'begin_entire_method_byte_identical':True,'healthy_finish_entire_tail_source_byte_identical':True,'NativeState_constructor_callsite_count':1,'PreservationMembership_constructor_callsite_count':1,'membership_publication_assignment_count':1,'source_digest':ident(D/'frozen/source/NativeRenderer.java'),'ui_bound_source':ident(D/'frozen/source/UiPacket.java'),'manual_review':'review.md records semantic ownership/bounds/failure reasoning; these source checks alone are not OTA authorization'})
proof={};helpers={'  private boolean preservationMembershipV2(':[], '  private boolean fieldPreservationCapturedV2(':[], '  private boolean preservationProvenanceV2(':['fieldPreservationCapturedV2'], '  boolean fieldPreservationIdentityV2(':['fieldPreservationCapturedV2','preservationMembershipV2'], '  private boolean preservationCohortV2(':['preservationMembershipV2'], '  private boolean preservationFailureFundedV2(':['preservationMembershipV2']}
for label,path in [('host',D/'runs/controls-1/completion-bytecode.stdout'),('cross',D/'runs/cross-1/completion-bytecode.stdout')]:
 text=path.read_text();out={'disassembly':ident(path),'tails':{},'scalar_helpers':{}}
 for name,prefix,marker in [('finish','  void finishV2(','.completion:I'),('Begin','  public void fieldPreservationBegin(','.entered:Z')]:
  lines,inst=bytecode_method(text,prefix)
  writes=[i for i,x in enumerate(inst) if x['op']=='putfield' and marker in x['rest']]
  assert writes;start=writes[0]-2;tail=inst[start:];assert tail[0]['op']=='aload_2' and tail[1]['op']=='iconst_1'
  first=tail[0]['offset'];last=tail[-1]['offset'];assert first==(391 if name=='finish' else 266)
  assert len(tail)==(121 if name=='finish' else 31)
  for x in tail:
   assert not(x['op'].startswith('invoke') or x['op'] in ('new','newarray','anewarray','multianewarray','athrow','monitorenter','monitorexit')),x
   if x['op'].startswith('if') or x['op'] in ('goto','goto_w'):assert first<=int(x['rest'].split()[0])<=last,x
  target=D/(label+'-'+name+'-tail.bytecode');target.write_text('\n'.join(x['raw'] for x in tail)+'\n')
  if name=='finish':
   puts=[x['rest'].split('// Field ')[1] for x in tail if x['op']=='putfield'];assert puts[-4].endswith('heldPreservations:I') and puts[-3].endswith('outstandingFieldPreservations:I') and puts[-2].endswith('outstandingEditorNativeCalls:I') and puts[-1].endswith('.completion:I'),puts[-6:]
  out['tails'][name]={'offset':first,'instructions':len(tail),'tail':ident(target),'no_invocation_allocation_explicit_throw_monitor_or_external_branch':True,'count_last':True}
 for prefix,allowed in helpers.items():
  lines,inst=bytecode_method(text,prefix);calls=[]
  for x in inst:
   assert x['op'] not in ('new','newarray','anewarray','multianewarray','athrow','monitorenter','monitorexit'),x
   if x['op'].startswith('invoke'):
    m=re.search(r'// Method ([^:]+):',x['rest']);assert m,x;method=m[1].split('.')[-1];assert method in allowed,(prefix,method);calls.append(method)
  out['scalar_helpers'][prefix.strip()]={'instructions':len(inst),'observed_calls':calls,'allowed_calls':allowed}
 lines,inst=bytecode_method(text,'  dev.mixer.android.NativeRenderer$PreservationMembership(')
 assert [x['op'] for x in inst]==['aload_0','invokespecial','aload_0','aload_1','putfield','aload_0','aload_2','putfield','return']
 assert 'java/lang/Object."<init>"' in inst[1]['rest'] and 'Field state:' in inst[4]['rest'] and 'Field scope:' in inst[7]['rest']
 target=D/(label+'-PreservationMembership-constructor.bytecode');target.write_text('\n'.join(lines)+'\n');out['member_constructor']={'only_Object_init_and_final_reference_writes':True,'bytecode':ident(target)}
 proof[label]=out
save(D/'independent-bytecode-proof.json',{'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Actual independently compiled complete product; synchronous source proof only; no OTA/native/asynchronous allocation-fault guarantee','runs':proof})
comparisons={}
producer=D.parents[2]/'verification/android-editor-preservation-membership-correction'
# Artifacts compared only after independent compilation; never imported for execution.
for ours,theirs in [('host-1','host-2'),('cross-1','cross-2')]:
 own=mapping(D/'runs'/ours/'classes');theirmap=json.loads((producer/'runs'/theirs/'class-map.json').read_text());assert own==theirmap
 comparisons[ours]={'producer_run':theirs,'class_files':len(own),'independently_compiled_classes_byte_identical':True}
 if ours=='cross-1':
  dex=mapping(D/'runs'/ours/'dex');assert dex==json.loads((producer/'runs'/theirs/'dex-map.json').read_text());comparisons[ours]['dex_files']=dex
for rel in ('source','host-leaves','tests','cross-source'):
 assert mapping(D/'runs/host-1/inputs'/rel)==mapping(D/'frozen'/rel)
 assert mapping(D/'runs/cross-1/inputs'/rel)==mapping(D/'frozen'/rel)
for p in (D/'independent-controls').glob('*.java'):assert p.read_bytes()==(D/'runs/host-1/independent-controls'/p.name).read_bytes()
save(D/'independent-output-comparison.json',comparisons)
print('PASS exact source identity, independently compiled121/31-instruction tails, scalar helper callgraphs, member constructors and fresh host/cross/dex output comparisons')
