"""Bind repository data read during a fresh import of the reviewed runtime."""
import hashlib
import json
import pathlib

HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1]
read_bytes=pathlib.Path.read_bytes;read_text=pathlib.Path.read_text
reads={}


def capture(path,data):
    path=path.resolve()
    if path.is_relative_to(ROOT):
        reads[str(path.relative_to(ROOT))]=hashlib.sha256(data).hexdigest()


def traced_bytes(path):
    data=read_bytes(path);capture(path,data);return data


def traced_text(path,*args,**kwargs):
    value=read_text(path,*args,**kwargs);capture(path,read_bytes(path));return value


pathlib.Path.read_bytes=traced_bytes;pathlib.Path.read_text=traced_text
try:
    import independent_flow
finally:
    pathlib.Path.read_bytes=read_bytes;pathlib.Path.read_text=read_text
inputs=json.loads(read_bytes(HERE/'review-inputs.json'))
additional={}
for name,value in reads.items():
    if name in inputs:
        assert inputs[name]==value,name
    else:
        additional[name]=value
inputs.update(additional)
result=dict(freshRuntimeImportDataReads=reads,additionalBindingsOutsideProducerSeal=additional,
            nativeExecuted=False,nativeInstancesQueried=False,
            limitation='Current import-data bytes independently bound; no application case executes.')
(HERE/'runtime-import-data-bindings.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
(HERE/'review-inputs.json').write_text(json.dumps(inputs,sort_keys=True,indent=2)+'\n')
print(json.dumps(dict(dataReads=len(reads),additionalBindings=len(additional),totalInputFiles=len(inputs))))
