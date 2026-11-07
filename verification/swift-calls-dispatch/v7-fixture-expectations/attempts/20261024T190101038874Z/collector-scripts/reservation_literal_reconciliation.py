import collect as c
import final_accounting_report as f
import json,difflib
stage=f.read(c.HERE/'preinstall-v5-query-bindings.json');result=[]
for cfg,oldq in stage.items():
 q=f.read(c.HERE/f'exact-query-{cfg}.json');assert q['sourceClosure']==f.read(c.HERE/'candidate-final-source.json')['sourceClosure']
 a={(r['path'],r['promoted']):r for r in f.rawquery(oldq)if r['kind']=='body'};b={(r['path'],r['promoted']):r for r in f.rawquery(q)if r['kind']=='body'};assert set(a)==set(b)
 prior=f.read(c.HERE/f'paired-layout-baseline-{cfg}.json')['totals']['frame']
 def frame(query):
  cs=f.classes(f.rawquery(query));unit=cfg.endswith('-unit');return prior+cs['CallsActivePositions']['layout']['bytes']+cs['NeverActivePositions']['layout']['bytes']+cs['CallsKindActivePositions']['layout']['bytes']+1664+(4176 if unit else 0)
 oldbound=frame(oldq);bound=frame(q);assert bound==f.read(c.HERE/f'paired-layout-candidate-{cfg}.json')['totals']['frame']
 for k in a:
  old=f.semantic(a[k]['mir']);new=f.semantic(b[k]['mir']);equal=old==new
  if not equal:
   assert k[0].endswith('::prepare_growth')and k[1]is None,(cfg,k,'non-formula runtime drift')
   needle=f'const {oldbound}_usize';replacement=f'const {bound}_usize';assert old.count(needle)==2,(cfg,k,oldbound,bound)
   assert old.replace(needle,replacement)==new,(cfg,k,'drift beyond actual reservation literals')
   diff=''.join(difflib.unified_diff(a[k]['mir'].splitlines(True),b[k]['mir'].splitlines(True),fromfile='preinstall-actual',tofile='final-actual'))
   c.save(c.HERE/('reservation-literal-'+cfg+'.diff'),diff.encode())
  result.append({'config':cfg,'body':k[0],'promoted':k[1],'preinstallQuery':oldq,'finalQuery':q,'rawPreinstallSHA256':c.sha(a[k]['mir'].encode()),'rawFinalSHA256':c.sha(b[k]['mir'].encode()),'normalizedPreinstallSHA256':c.sha(old.encode()),'normalizedFinalSHA256':c.sha(new.encode()),'normalizedEqual':equal,'onlyExplicitReservationLiteralChange':not equal,'preinstallFrameFormula':oldbound,'finalFrameFormula':bound,'finalActualLiteralsRetained':True,'normalization':'Compiler comments/source coordinates and allocation display indices only; no type/opcode/literal erased. Changed reservation literals separately checked against actual compiled classes and old/new original additive formula.'})
c.save(c.HERE/'reservation-literal-reconciliation.json',result)
print('All preinstall/final runtime bodies reconciled; only explicitly proved reservation literals may differ')
