"""Read-only exact official Rust source fetch, no compiler or dependency changes."""
import json,urllib.request,sys
sys.dont_write_bytecode=True
from custody import HERE,sha
REV='b940084d7eb6a299eb4bfeb8e34901bc051e7ac4'
def main():
 records=[]
 for name in ('library/core/src/num/mod.rs','library/core/src/macros/mod.rs'):
  url=f'https://raw.githubusercontent.com/rust-lang/rust/{REV}/{name}'
  with urllib.request.urlopen(url,timeout=20) as response:b=response.read()
  dest=HERE/'official-source'/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(b)
  records.append({'path':name,'url':url,'bytes':len(b),'sha256':sha(b),'success':True});print(json.dumps(records[-1]))
 (HERE/'additional-official-source-custody.json').write_text(json.dumps({'schema':1,'revision':REV,'transport':'Python urllib.request; exact raw GitHub rust-lang/rust source URL','members':records},sort_keys=True,indent=2)+'\n')
if __name__=='__main__':main()
