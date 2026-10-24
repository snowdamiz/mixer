"""Install exact typed fields and only root-selected finite numeric exceptions."""
import collect as c
import inventory as v
import json,collections
from pathlib import Path

def main():
 rows=json.loads((c.HERE/'inventory.json').read_text());finite=json.loads((c.HERE/'finite-proposal.json').read_text())
 selection=c.ROOT/'verification/swift-reactor-lifecycle-contract-root-review/finite-position-selection.json'
 assert selection.exists(),'Root finite position selection required before numeric adoption'
 authority=json.loads(selection.read_text())
 assert authority['finiteProposalSHA256']==c.sha((c.HERE/'finite-proposal.json').read_bytes())
 assert authority['positions']==len(finite)
 offsets={(phase,unit):0 for phase in ['active','permanent']for unit in [False,True]}
 numeric=[]
 for row in finite:
  layout=row['layout'];size=layout['bytes'];align=layout['alignment'];assert align>0 and align&(align-1)==0
  key=(row['ownerClass'],row['unitOnly']);start=(offsets[key]+align-1)//align*align;end=start+size;assert end<2**64;offsets[key]=end
  numeric.append(dict(row,relativeOffset=start,exclusiveEnd=end,component=row['ownerClass']+('-unit'if row['unitOnly']else'-production')))
 code=['// Fresh exact compiler positions. Historical V7 structs/rows are untouched.']
 def cls(name,items,override=None):
  body=['#[allow(dead_code)]','pub(super) struct '+name+' {']
  for row in items:
   if row['unitOnly']:body.append('    #[cfg(test)]')
   body.append('    '+row['field']+': '+(override or v.normal(row['mirType']))+',')
  return body+['}']
 for phase in ['active','permanent']:
  title=phase.title();upper=phase.upper()
  typed=[r for r in rows if r['method']=='exact-typed'and r['ownerClass']==phase]
  never=[r for r in rows if r['method']=='exact-inferred-never'and r['ownerClass']==phase]
  code+=cls('Lifecycle'+title+'Positions',typed)
  if never:
   unit_only=all(row['unitOnly']for row in never)
   if unit_only:code+=['#[cfg(test)]']
   code+=cls('LifecycleNever'+title+'Positions<T>',never,'T')
   if unit_only:code+=['#[cfg(test)]']
   code+=[f'const fn accounting_exact_never_{phase}<T>(_: fn() -> T) -> usize {{size_of::<LifecycleNever{title}Positions<T>>()}}',*(['#[cfg(test)]']if unit_only else[]),f'const LIFECYCLE_NEVER_{upper}_BYTES:usize=accounting_exact_never_{phase}(accounting_never_type);']
   if unit_only:code+=['#[cfg(not(test))]',f'const LIFECYCLE_NEVER_{upper}_BYTES:usize=0;']
  else:code+=[f'const LIFECYCLE_NEVER_{upper}_BYTES:usize=0;']
  code += [f'const LIFECYCLE_NUMERIC_{upper}_PRODUCTION_BYTES:usize={offsets[(phase,False)]};','#[cfg(test)]',f'const LIFECYCLE_NUMERIC_{upper}_UNIT_BYTES:usize={offsets[(phase,True)]};','#[cfg(not(test))]',f'const LIFECYCLE_NUMERIC_{upper}_UNIT_BYTES:usize=0;',f'pub(super) const {upper}_BYTES:usize=size_of::<Lifecycle{title}Positions>() + LIFECYCLE_NEVER_{upper}_BYTES + LIFECYCLE_NUMERIC_{upper}_PRODUCTION_BYTES + LIFECYCLE_NUMERIC_{upper}_UNIT_BYTES;']
 if any(r['method']=='exact-inferred-never'for r in rows):code+=['// Type inference witness only; no executable caller is present.','fn accounting_never_type() -> ! {panic!("accounting witness must never execute")}']
 source='\n'.join(code)+'\n';c.save(c.HERE/'positive-positions.rs',source.encode());c.save(c.HERE/'numeric-positions.json',numeric)
 path=c.HERE/'candidate/src/experimental_swift_reactor/lifecycle.rs';text=path.read_text();a=text.index('// LIFECYCLE_ACCOUNTING_BEGIN');b=text.index('// LIFECYCLE_ACCOUNTING_END',a)+len('// LIFECYCLE_ACCOUNTING_END')
 path.write_text(text[:a]+'// LIFECYCLE_ACCOUNTING_BEGIN\n'+source+'// LIFECYCLE_ACCOUNTING_END'+text[b:])
 path=c.HERE/'candidate/src/experimental_swift_reactor/memory_growth_operations.rs';text=path.read_text()
 old='pub(in crate::experimental_swift_reactor::execution) const PERMANENT_BYTES:usize=size_of::<PermanentPositions>();'
 new='pub(in crate::experimental_swift_reactor::execution) const PERMANENT_BYTES:usize=size_of::<PermanentPositions>() + lifecycle::PERMANENT_BYTES;'
 assert old in text or new in text;text=text.replace(old,new)
 old='pub(super) const ACTIVE_BYTES:usize=size_of::<ActivePositions>();';new='pub(super) const ACTIVE_BYTES:usize=size_of::<ActivePositions>() + lifecycle::ACTIVE_BYTES;'
 assert old in text or new in text;text=text.replace(old,new);path.write_text(text)
 c.save(c.HERE/'accounting-installation.json',{'rootSelectionSHA256':c.sha(selection.read_bytes()),'finiteProposalSHA256':c.sha((c.HERE/'finite-proposal.json').read_bytes()),'typedRoles':sum(r['method']=='exact-typed'for r in rows),'neverRoles':sum(r['method']=='exact-inferred-never'for r in rows),'finiteRoles':len(finite),'numericBytes':{phase:{'production':offsets[(phase,False)],'unit':offsets[(phase,True)]}for phase in ['active','permanent']},'sourceClosure':c.sha(c.enc(c.manifest(c.HERE/'candidate'))),'accountingAccepted':False})
 print('Positive additions installed; independent accounting acceptance remains pending')
if __name__=='__main__':main()
