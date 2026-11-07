#!/usr/bin/env python3
"""Fresh finite evaluations of separately derived selected425 model only."""
from pathlib import Path
import hashlib,importlib.util,json,struct,sys
P=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 original=(P/'inputs/fsm-model.py').read_bytes();derived=(P/'inputs/fsm-model-425.py').read_bytes()
 assert derived==original.replace(b'RECORD_DEBIT = 128',b'RECORD_DEBIT = 425')
 spec=importlib.util.spec_from_file_location('selected425_fixture_model',P/'inputs/fsm-model-425.py')
 m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
 assert m.RECORD_DEBIT==425
 raw=(P/'inputs/oracle.bin').read_bytes();assert len(raw)==16170*352
 data=bytearray();cases=[]
 for i in range(16170):
  fields=struct.unpack_from('<44Q',raw,i*352)
  state=m.State(**dict(zip(m.CELLS,fields[:12])));w=fields[12:28]
  r=m.observe(state,w,425);s=r.state;assert s is not None
  out=[1 if r.reason=='Observed' else 2,m.REASONS[r.reason],s.accepted,s.state,s.phase,s.mask,s.operation,s.active_op,s.function,s.failed,s.terminal,s.work,s.instructions,r.steps,0,0]
  old=list(fields[28:]);assert out[:13]==old[:13] and out[14:]==old[14:] and old[13]==128 and out[13]==425
  assert not r.fullReplayAccepted and not r.storedPrefixValidated and not r.semanticMetricsValid
  data.extend(struct.pack('<44Q',*fields[:28],*out));cases.append((state,w))
 (P/'inputs/oracle-425.bin').write_bytes(data)
 # Original exhaustive ordering contains one base plus96 field mutations only
 # in phase0/latch0. Walk that pinned ordering rather than rewriting fixtures.
 boundary=bytearray();position=0;seeds=0
 for stage in range(11):
  for phase in (0,4,5):
   for latch in (0,1,2):
    for kind in range(1,15):
     state,w=cases[position];assert(state.state,state.phase,state.failed,state.terminal,w[1])==(stage,phase,int(latch==1),int(latch==2),kind)
     position+=97 if phase==0 and latch==0 else 1;seeds+=1
     for credits in (0,424,425,426):
      r=m.observe(state,w,credits);s=r.state;assert s is not None
      out=[1 if r.reason=='Observed' else 2,m.REASONS[r.reason],s.accepted,s.state,s.phase,s.mask,s.operation,s.active_op,s.function,s.failed,s.terminal,s.work,s.instructions,r.steps,0,0]
      boundary.extend(struct.pack('<45Q',*[getattr(state,k)for k in m.CELLS],*w,credits,*out))
 assert position==16170 and seeds==1386 and len(boundary)==5544*360
 (P/'inputs/oracle-budget-425.bin').write_bytes(boundary)
 result={'schema':1,'model_original_sha256':sha(P/'inputs/fsm-model.py'),'model_derived_sha256':sha(P/'inputs/fsm-model-425.py'),'model_delta':'Exactly RECORD_DEBIT=128 ->425; historical model unchanged','source_original_oracle_sha256':sha(P/'inputs/oracle.bin'),'fresh_selected_source_oracle':{'path':'inputs/oracle-425.bin','sha256':sha(P/'inputs/oracle-425.bin'),'cases':16170,'record_bytes':352,'bytes':len(data),'compared_to_historical':'Same state/record and reason/state fields; only reply debit128->425. All outcomes freshly evaluated using derived selected model.'},'fresh_budget_matrix':{'path':'inputs/oracle-budget-425.bin','sha256':sha(P/'inputs/oracle-budget-425.bin'),'cases':5544,'record_bytes':360,'bytes':len(boundary),'seed_states_records':1386,'credits':[0,424,425,426]},'total_model_evaluations':21714,'authority':'Finite synthetic fixture differential test only; no source applicability, semantic replay, release, real binding, target/native or CPU authority'}
 (P/'inputs/oracle-425.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
