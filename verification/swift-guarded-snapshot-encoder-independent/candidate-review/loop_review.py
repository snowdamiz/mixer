import json,math,sys
import run_review as r
sys.path.insert(0,str(r.PRE))
from wire_oracle import CAPS,WORDS,HEADER,MAX_IMAGE
def review(lengths,label):
 offsets=[];at=HEADER
 for length in lengths:offsets.append(at);at+=length
 max_steps=max_words=max_probes=0
 for base in range(0,at,4096):
  end=min(base+4096,at);chunks=0;visits=0
  if base<HEADER and end>0:chunks+=1
  for sid,(start,size)in enumerate(zip(offsets,lengths)):
   lo=max(base,start);hi=min(end,start+size)
   if lo>=hi:continue
   if sid==0:chunks+=1
   else:visits+=(hi-start+7)//8-(lo-start)//8
  steps=chunks+visits;probes=visits*9+(1 if base<offsets[0]+lengths[0]and end>offsets[0]else 0)
  assert visits<=513 and steps<=515 and probes<=4635
  max_steps=max(max_steps,steps);max_words=max(max_words,visits);max_probes=max(max_probes,probes)
 return {'label':label,'extent':at,'blocks':(at+4095)//4096,'max_progress_iterations':max_steps,'max_record_word_visits':max_words,'max_directory_probes_upper':max_probes}
results=[]
for path in sorted((r.HERE/'runs').glob('*/actual.mixsnb02')):
 import struct
 image=path.read_bytes();lengths=[struct.unpack_from('<Q',image,1600+64*n+56)[0]for n in range(9)]
 results.append(review(lengths,str(path.parent.name)))
for alignment in range(8):
 lengths=[CAPS[0]-alignment]+[CAPS[n]*WORDS[n]*8 for n in range(1,9)]
 results.append(review(lengths,'synthetic-structural-cap-source-minus-'+str(alignment)))
assert results[-8]['extent']==MAX_IMAGE
r.save(r.HERE/'loop-review.json',{'scope':'independent structural arithmetic over exact actual directories and synthetic cap envelopes; no genuine cap-fixture or original-control work grant','bounds':{'progress_iterations':515,'record_word_visits':513,'directory_probes':4635,'record_fields_per_visit':5,'spans_per_visit':2,'type_index_per_visit':1,'output_bytes':4096},'cases':results,'proof':'Every iteration advances. Header and source each use at most one chunk. All metadata sections have whole8byte words and one common global alignment, so a4096byte window visits at most513 words; section changes do not add a progress iteration. Each record_word checks at most5logical fields,2spans and1type index, and the fixed directory search probes at most9entries. Setup loops have fixed input-independent ceilings and do not scan source/metadata records.'})
print('loop-review: pass',len(results),'directory cases')
