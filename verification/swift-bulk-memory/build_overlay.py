from pathlib import Path
import json,hashlib
HERE=Path(__file__).resolve().parent
enc=lambda x:(json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def manifest(vm):
 paths=[vm/'Cargo.toml',vm/'Cargo.lock']
 for d in ['src','tests','include']:paths+=sorted(p for p in (vm/d).rglob('*') if p.is_file())
 return {str(p.relative_to(vm)):sha(p) for p in paths}
def digest(m):return hashlib.sha256(enc(m)).hexdigest()
def method(s,name):
 a=s.index('fn '+name+'(');b=s.index('{',a);i=b+1;n=1
 while n:n+=(s[i]=='{')-(s[i]=='}');i+=1
 return s[a:i]
