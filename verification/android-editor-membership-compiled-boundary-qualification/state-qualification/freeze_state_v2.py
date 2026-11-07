from pathlib import Path
import json,hashlib,shutil,signal,datetime
signal.alarm(60)
Q=Path(__file__).resolve().parents[1];R=Q.parents[1];D=Q/'state-replay-candidate-v2';A=Q/'state-qualification/full-candidate-v1'
assert not D.exists();D.mkdir()
def ident(p):
 h=hashlib.sha256();n=0
 with p.open('rb') as f:
  while b:=f.read(1024*1024):h.update(b);n+=len(b)
 return {'bytes':n,'sha256':h.hexdigest()}
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
summary=[]
for name in ['run-12','run-14','run-16']:
 src=A/name;dst=D/name;shutil.copytree(src,dst);receipt=json.loads((src/'receipt.json').read_bytes());assert receipt['all_commands_passed'] and receipt['cleanup']['all_children_reaped'] and receipt['cleanup']['scratch_removed']
 freeze=json.loads((src/'source-freeze.json').read_bytes());roster=[]
 for row in freeze['sources']:
  original=R/row['path'];candidate=src/original.name
  source=candidate if candidate.exists() and ident(candidate)=={k:row[k] for k in ['bytes','sha256']} else original
  assert ident(source)=={k:row[k] for k in ['bytes','sha256']},row['path']
  target=dst/'source-closure'/original.relative_to(Q);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target);roster.append({'original_path':str(original),'packet_path':str(target.relative_to(D)),**ident(target)})
 save(dst/'closed-source-roster.json',roster);summary.append({'run':name,'commands':len(receipt['commands']),'all_commands_passed':True,'source_roster':ident(dst/'closed-source-roster.json'),'class_map':ident(dst/'class-map.json'),'product209_exact_context1b71':True})
for name in ['run-11','run-13','run-15']:
 src=A/name;dst=D/'retained-correction-history'/name;dst.mkdir(parents=True)
 for f in src.iterdir():
  if f.is_file() and f.suffix in ['.json','.stdout','.stderr','.java','.py']:shutil.copy2(f,dst/f.name)
shutil.copy2(Q/'state-qualification/diagnostics/summary-scan-interruption.json',D/'retained-correction-history/summary-scan-interruption.json')
for source,target in [(Q/'passive-return-probe-v3/descriptor.json','descriptor.json'),(Q/'state-qualification/context17-1/product-context.json','product-context.json'),(Q/'state-qualification/context17-1/legacy189-bindings.json','historical189-current-bindings.json'),(Q/'semantic-review-candidate-v1/active-semantic-obligations.json','original280-semantic-inventory.json'),(Q/'semantic-review-candidate-v1/reference-obligations.json','reference-obligations.json')]:shutil.copy2(source,D/target)
save(D/'evidence-summary.json',{'schema':2,'root_selected':False,'qualification_status':'expanded-host-state-candidate; full-semantic-joins-and-execution-closure-pending','runs':summary,'declared_producer_row_counts':{'historical_callbacks':180*7,'direct_callbacks_and_refusal_states':20*13,'queries':7*12,'close':7,'finite_exact38':107,'five_separate_v1':5,'field_finite':84,'external_unsupported_callbacks':2*2*7},'row_count_scope':'Counts follow the exact frozen producer loops and passing child commands; no independent aggregate row parse claimed here. The raw complete compressed rows are retained.','source16_tree':'a5e4888b96995bf768062bd9c2f1573dc440a4fe22270a205ab5550e79f625e4','selected_whole_host_test_sha256':'9dda45ef21a83183f2f61bc4a8ba864d868acd9be3683a3c147acdfa7668bc3e','passive_v3_seal':ident(Q/'passive-return-probe-v3/seal.json'),'canonical_seven_states':['clean','terminal-at-entry','terminal-before-return','dirty-at-entry','dirty-before-return','ordinary-throw-after-callback','fatal-throw-after-callback'],'limits':['All189 historical dispositions and280 original semanticIDs preserved; observed callback rows do not by themselves discharge all semantic cases.','Exact native TextAttribute commitText/setComposingText nonvoid returns remain uncaptured in v3 and explicitly pending selected v4 review.','Legacy status deliberately retains outcome-review-required; frame observation is not a helper return certificate.','Native return wrappers record original value once; query snapshots copy exact fields/types/order and values at required time.','Every attempt latches cleanliness before later begin; passive evidence faults dirty/refuse without replacing original outcomes.','Actual full frames are reconstructed only from matching original24-prefix plus actual fresh stack; ambiguity/overflow refuses.','External constant unsupported callbacks have source-specific always-unsupported/exception-transparent semantics; authored owner-close target cleanup is reported separately from zero unsupported target forwarding.','No final semantic policy/context/execution closure/bootstrap selection; v5 interpreter review remains unaccepted/pending.','No canonical integration, CI, native, OTA or GA acceptance.']})
(D/'README.md').write_text('Expanded ordinary-Java host state candidate. All222 bounded commands in the three passing runs completed and were reaped with owned scratch removed. Exact selected16 product sources compile to the unchanged209-class JDK17 context1b71; selected migrated whole legacy host test9dda and accepted v3 passive leaves are separately bound in each run source/class closure. Original product/test/assertion bodies are unchanged. Supplementary observers guard passive evidence failures, latch each attempt before reset, copy exact typed mutable content, and retain actual complete product frames. The exact214-command expanded replay includes180 historical subjects with seven callback states,20 direct families,7 queries,close,SET38 finite guards and separate five original V1 sites. Separate84 finite field/lease cases and28 Executor/receiver callback states also pass. Root/independent review, remaining280 semantic outcome joins, two exact native attribute-overload returns and complete trusted execution-closure admission remain pending. This packet cannot authorize a default full-matrix pass. Each run has its exact source roster/class set/raw command logs and compressed rows. Earlier correction failures are retained. No native/UI/capture/process-inventory runtime occurred.\n')
shutil.copy2(__file__,D/'freeze_state_v2.py')
print(D)
