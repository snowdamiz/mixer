import importlib.util,json,sys
from pathlib import Path
p=Path(sys.argv[1])
s=importlib.util.spec_from_file_location("frozen_outer_review",p)
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def compare(name,value):
    assert (p.parent/name).read_text()==json.dumps(value,indent=2,sort_keys=True)+"\n",name
m.out=compare
m.main()
