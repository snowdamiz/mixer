"""Retained preparation observations; no qualifying proof from this helper."""
from common import *
import difflib
def main():
 m,t,s=accepted_modules();tables=source_tables();texts=mir_texts()
 result=[]
 for i,text in enumerate(texts):
  blocks,coverage=s.parse_mir(text)
  counts=collections.Counter('fn' if b.startswith('fn ') else 'alloc' if b.startswith('alloc') else 'standalone' if '\n' not in b else 'other' for b in blocks)
  result.append({'tree':TREES[i],'counts':dict(counts),'coverage':coverage,'query_headers':[b.splitlines()[0] for b in blocks if any(x in b.splitlines()[0] for x in ('query_v1','compiles_v1'))]})
 deltas=[]
 for i,(a,b) in enumerate(zip(tables,tables[1:])):
  changed=[p for p in a if a[p]!=b[p]]
  deltas.append({'from':TREES[i],'to':TREES[i+1],'changed':changed,'profile_diff':''.join(difflib.unified_diff(a[PROFILE].decode().splitlines(True),b[PROFILE].decode().splitlines(True)))})
 save('preparation-observations.json',{'MIR':result,'source_deltas':deltas})
 print(json.dumps({'MIR':result,'source_changed':[(x['from'],x['changed']) for x in deltas]},indent=2))
if __name__=='__main__':main()
