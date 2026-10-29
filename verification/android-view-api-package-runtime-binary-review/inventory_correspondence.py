"""Narrow data-only reconciliation of emitted DEX class inventory."""
import sys,types,json,hashlib,struct
from pathlib import Path
HERE=Path(__file__).resolve().parent

def ident(b):return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}

def main():
    gb=(HERE/'guarded_inspector.py').read_bytes()
    assert ident(gb)=={'bytes':5958,'sha256':'7c4cb8714869601dc2d7747f1c6c06a476b840a37c4cd71c151a0bc16361ab9b'}
    g=types.ModuleType('_inventory_guard');exec(compile(gb,str(HERE/'guarded_inspector.py'),'exec',dont_inherit=True),g.__dict__);guards=g.install_guards()
    emitted=HERE/'local/emitted-001';b=(emitted/'dex/classes.dex').read_bytes()
    assert len(b)==414640 and hashlib.sha256(b).hexdigest()=='b8645ab41e1799502ff6e1ea0d09fa6378d8a4b94fda1a9ef27fd06f326d8fe1'
    u32=lambda a:struct.unpack_from('<I',b,a)[0]
    def leb(at):
        n=0
        for shift in range(0,35,7):
            value=b[at];at+=1;n|=(value&127)<<shift
            if value<128:return n,at
        raise ValueError('ULEB bound')
    strings=[]
    for i in range(u32(56)):
        size,at=leb(u32(u32(60)+4*i));end=b.index(0,at);strings.append(b[at:end].replace(b'\xc0\x80',b'\0').decode('utf-8','surrogatepass'))
    types_=[strings[u32(u32(68)+4*i)] for i in range(u32(64))]
    dex={types_[u32(u32(100)+32*i)][1:-1]:None if u32(u32(100)+32*i+16)==0xffffffff else strings[u32(u32(100)+32*i+16)] for i in range(u32(96))}
    sdk={str(p.relative_to(emitted/'sdk-classes'))[:-6]:ident(p.read_bytes()) for p in (emitted/'sdk-classes').rglob('*.class')}
    host={str(p.relative_to(emitted/'host-classes'))[:-6]:ident(p.read_bytes()) for p in (emitted/'host-classes').rglob('*.class')}
    extras=sorted(set(dex)-set(sdk));missing=sorted(set(sdk)-set(dex));namespace={}
    for name in dex:
        key='/'.join(name.split('/')[:3]);namespace[key]=namespace.get(key,0)+1
    product={n for n in sdk if n.startswith('dev/mixer/android/') and not n.startswith('dev/mixer/android/NativeBridge')}
    common_product=[n for n in sorted(product) if n in host and host[n]==sdk[n]]
    out={'schema':1,'status':'data-only-inventory-correspondence','command':['/opt/homebrew/bin/python3','-I','-B','-S',str(HERE/'inventory_correspondence.py')],'source':ident((HERE/'inventory_correspondence.py').read_bytes()),'guard_source':ident(gb),'guards_installed_before_binary_reads':guards['installed_before_subject_import'],'dex':ident(b),'dex_classes':len(dex),'sdk_classes':len(sdk),'dex_class_namespace_counts':namespace,'sdk_classes_present_in_dex':len(set(sdk)&set(dex)),'sdk_classes_absent_from_dex':missing,'extra_dex_classes':[{'owner':n,'source_file':dex[n]} for n in extras],'product_classes':len(product),'host_sdk_byte_identical_product_classes':len(common_product),'host_sdk_different_product_classes':[n for n in sorted(product) if n not in common_product],'limitations':['Class inventory only; no ART/D8/product execution or general synthetic semantic proof.','SourceFile metadata for newly emitted DEX classes is data, not provenance authority.']}
    (HERE/'inventory-correspondence.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k not in ('extra_dex_classes','command','source','guard_source','limitations','host_sdk_different_product_classes')}));print('EXTRAS',json.dumps(out['extra_dex_classes'][:10]));print('PRODUCT_DIFFERENCES',len(out['host_sdk_different_product_classes']))

if __name__=='__main__':main()
