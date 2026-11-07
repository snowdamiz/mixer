#!/usr/bin/env python3
"""Finite fixture differential input only; no product or source authority."""
import importlib.util
import json
from pathlib import Path
import struct
import sys

BASE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('envelope_fixture_oracle', BASE/'inputs/fsm-model.py')
model = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = model
spec.loader.exec_module(model)

def event(kind, state):
    f=34 if kind==1 else state.function
    w=[state.accepted+1,kind,state.phase,0 if kind in (12,13) else state.operation+1 if kind==1 else state.active_op,state.work+1,state.instructions+2,f,100,7,2,model.MAX,model.MAX,0,0,0,0]
    if kind==1:w[7:10]=[model.MAX]*3
    elif kind==3:w[15]=f&511
    elif kind==4:w[14:16]=[model.MAX,f&511]
    elif kind==5:w[13:16]=[8,16,64]
    elif kind in (6,7,8):w[10],w[13]=1,8
    elif kind in (9,10):w[13]=8
    elif kind==11:w[10:16]=[1,2,3,int(state.state==10),8,1]
    elif kind==12:w[6:16]=[72,200,model.MAX,4,1,2,3,8,0,0]
    elif kind==13:w[2],w[6:10],w[13]=4,[model.MAX]*4,4
    elif kind==14:w[3],w[6:10],w[13:16]=0 if state.state==0 else state.active_op,[model.MAX]*4,[2,1,2]
    return w

def main():
    data=bytearray(); count=0
    for stage in range(11):
        for phase in (0,4,5):
            for latch in (0,1,2):
                state=model.State(accepted=5,work=9,instructions=10,operation=7,phase=phase,mask=1|(1<<phase),expected=33,state=stage,active_op=7,function=34,terminal=int(latch==2),failed=int(latch==1))
                for kind in range(1,15):
                    base=event(kind,state)
                    variants=[base]
                    if phase==0 and latch==0:
                        for cell in range(16):
                            for value in (0,1,(1<<32)-1,1<<32,model.MAX-1,model.MAX):
                                w=base.copy();w[cell]=value;variants.append(w)
                    for w in variants:
                        result=model.observe(state,w,128)
                        s=result.state;status=1 if result.reason=='Observed' else 2
                        reply=[status,model.REASONS[result.reason],s.accepted,s.state,s.phase,s.mask,s.operation,s.active_op,s.function,s.failed,s.terminal,s.work,s.instructions,result.steps,0,0]
                        fields=[getattr(state,k) for k in model.CELLS]+w+reply
                        data.extend(struct.pack('<44Q',*fields));count+=1
    (BASE/'inputs/oracle.bin').write_bytes(data)
    result=dict(cases=count,bytes=len(data),record_bytes=352,scope='copied frozen finite model differential oracle; not source applicability or semantic replay')
    (BASE/'inputs/oracle.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))

if __name__=='__main__':main()
