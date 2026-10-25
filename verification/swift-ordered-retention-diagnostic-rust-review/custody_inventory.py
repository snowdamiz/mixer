"""Trace only the owned finite capture frame's named Python owners."""
from pathlib import Path
import hashlib, io, json, os, sys, tarfile, types
P=Path(__file__).resolve().parent;F=P.parent/'swift-ordered-retention-diagnostic-rust'
m=types.ModuleType('frozen_finite_custody');m.__file__=str(F/'capture_finite.py');exec(compile((F/'capture_finite.py').read_bytes(),m.__file__,'exec'),m.__dict__)
D=P/'custody-inventory-control';D.mkdir(exist_ok=False);source=D/'input.bin';destination=D/'copy.bin'
fd=os.open(source,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600);initial=m.metadata(os.fstat(fd));raw=(F/'streams/candidate-final-finite/ordered-5.bin').read_bytes();assert os.write(fd,raw)==len(raw);final=m.metadata(os.fstat(fd));os.close(fd)
source.with_suffix('.initial.json').write_text(json.dumps(initial));source.with_suffix('.final.json').write_text(json.dumps(final))
with tarfile.open(F/'raw-fixtures.tar.gz','r:gz') as t:original=t.extractfile('tmp-candidate/candidate-final-finite/ordered-5.original.txt').read()
source.with_suffix('.original.txt').write_bytes(original)
observations=[]
def trace(frame,event,arg):
    if event=='line' and frame.f_code.co_filename==m.__file__ and frame.f_code.co_name=='capture':
        owners={n:{'bytes':sys.getsizeof(v),'closed':v.closed} for n,v in frame.f_locals.items() if isinstance(v,io.FileIO)}
        if len(owners)>=4 and not observations:observations.append({'line':frame.f_lineno,'owners':owners,'actualNamedFileIOOwners':len(owners),'simultaneousOpenDescriptors':sum(not v['closed'] for v in owners.values()),'actualOwnerBytes':sum(v['bytes'] for v in owners.values())})
    return trace
sys.settrace(trace)
try:m.capture(source,destination)
finally:sys.settrace(None)
assert len(observations)==1;observation=observations[0];assert observation['actualNamedFileIOOwners']==4
inventory=m.inventory();charged=inventory['values']['threeFileIOOwners'];assert observation['actualOwnerBytes']>charged
receipt={'scope':'one concrete named-value undercount; not complete Python memory reconciliation','frozenScriptSHA256':hashlib.sha256((F/'capture_finite.py').read_bytes()).hexdigest(),'observation':observation,'chargedFileIOOwnerBytes':charged,'missingNamedFileIOOwnerBytes':observation['actualOwnerBytes']-charged,'producerTotal':inventory['total'],'correctedOnlyForThisItem':inventory['total']+observation['actualOwnerBytes']-charged,'ceiling':inventory['ceiling'],'physicalMemoryClaim':False}
(P/'custody-inventory.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n');print(json.dumps(receipt,indent=2))
