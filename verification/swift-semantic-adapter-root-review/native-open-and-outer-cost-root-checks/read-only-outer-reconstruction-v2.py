import importlib.util,json,sys,collections
from pathlib import Path
p=Path(sys.argv[1])
s=importlib.util.spec_from_file_location("frozen_outer_review",p)
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def compare(name,value):
    old=json.loads((p.parent/name).read_bytes())
    if name=="assertions.json":
        assert old["count"]==value["count"]==1450
        assert collections.Counter(old["passed"])==collections.Counter(value["passed"]),name
    elif name=="native-layout-reconstruction.json":
        for obj in (old,value):
            obj["normalized_conflicts"]={k:sorted(v,key=lambda x:json.dumps(x,sort_keys=True)) for k,v in obj["normalized_conflicts"].items()}
        assert old==value,name
    else:
        assert old==value,name
m.out=compare
m.main()
