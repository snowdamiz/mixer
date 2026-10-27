"""Decode raw compiler layouts independently; never imports a producer module."""
from pathlib import Path
import hashlib, json, re, struct, collections

HERE=Path(__file__).resolve().parent
P=HERE.parents[1]/"swift-guarded-snapshot-owner-storage-closure"
read=lambda p:json.loads(p.read_text())


def decode(path):
    s=path.read_text();m=re.search(r'constant \[(\d+) x i8\] c"(.*?)"',s)
    assert m
    b=bytearray();i=0
    while i<len(m[2]):
        if m[2][i]=="\\":b.append(int(m[2][i+1:i+3],16));i+=3
        else:b.append(ord(m[2][i]));i+=1
    assert len(b)==int(m[1]) and len(b)%16==0
    return [struct.unpack_from("<QQ",b,i) for i in range(0,len(b),16)]


def short(t):
    t=re.sub(r"\b(?:[a-z_][a-zA-Z0-9_]*::)+(?=[A-Z])","",t)
    t=t.replace("'static","'_")
    t=re.sub(r"&\s*'_[ ]*","&",t)
    return re.sub(r"\s+","",t)


def base(t,layouts):
    if t in layouts:return layouts[t]
    if t.startswith("&"):
        x=t[1:].strip().removeprefix("mut ")
        return (16 if x=="str" or (x.startswith("[") and ";" not in x) or x.startswith("dyn ") else 8,8)
    primitives={"()":(0,1),"!":(0,1),"bool":(1,1),"u8":(1,1),"i8":(1,1),"u16":(2,2),"i16":(2,2),"u32":(4,4),"i32":(4,4),"u64":(8,8),"i64":(8,8),"usize":(8,8),"isize":(8,8),"u128":(16,16),"i128":(16,16)}
    if t in primitives:return primitives[t]
    if t.startswith(("fn(","fn (")):return (0,1) if re.search(r"\{.*\}$",t) else (8,8)
    m=re.fullmatch(r"\[(.*); (\d+)\]",t)
    if m:
        size,align=base(m[1],layouts);return(size*int(m[2]),align)
    raise KeyError(t)


def main():
    unit_requests=read(P/"unit-layout-requests.json")
    assert not unit_requests["control"]
    initial=decode(P/"MIXER_OWNER_UNIT_INITIAL.llvm")
    assert len(initial)==len(unit_requests["initial"])
    unit=dict(zip(unit_requests["initial"],initial))
    comp=read(P/"completion-layout-requests.json")
    prod_comp=decode(P/"MIXER_OWNER_COMPLETION_PRODUCTION.llvm")
    unit_comp=decode(P/"MIXER_OWNER_COMPLETION_UNIT.llvm")
    assert prod_comp==unit_comp==[(40,8),(2640,8),(32,8),(16,8)]
    unit.update(zip(comp,unit_comp))
    claimed_unit={r["compiler_type"]:(r["bytes"],r["alignment"]) for r in read(P/"unit-type-layouts.json")}
    assert unit==claimed_unit and len(unit)==219
    extra=read(P/"extra-layout-requests.json")
    prod_extra=decode(P/"MIXER_OWNER_EXTRA_LAYOUTS_V1.llvm")
    assert len(extra)==len(prod_extra)==40
    prod=dict(zip((r["compiler_type"] for r in extra),prod_extra))
    prod.update(zip(comp,prod_comp))
    assert prod=={r["compiler_type"]:(r["bytes"],r["alignment"]) for r in read(P/"extra-type-layouts.json")}
    stdout=(P/"commands/actual-monomorphic-layouts/stdout").read_text()
    rawlines={m[1]:(int(m[2]),int(m[3])) for m in re.finditer(r"(?m)^print-type-size type: `(.*)`: (\d+) bytes, alignment: (\d+) bytes$",stdout)}
    base_layouts={**rawlines,**prod}
    variants=0;routes=collections.Counter()
    inv=read(P/"inventory.json")
    for role in inv["roles"]:
        for a in role["actual_variants"]:
            variants+=1;p=a["production"];u=a["unit"]
            if "raw_line" in p:
                assert p["raw_line"] in stdout
                assert rawlines[p["actual_identity"]]==(p["bytes"],p["alignment"])
                routes["actual raw compiler type line"]+=1
            elif p["evidence"].endswith(".llvm"):
                assert prod[p["compiler_type"]]==(p["bytes"],p["alignment"])
                routes["decoded production LLVM"]+=1
            else:
                assert base(a["actual_type"],base_layouts)==(p["bytes"],p["alignment"])
                routes["target base/reference/function-item/actual-array rule"]+=1
            if u:
                assert unit[u["compiler_type"]]==(u["bytes"],u["alignment"])
                assert short(a["actual_type"])==short(u["compiler_type"])
            assert a["bytes"]==max(p["bytes"],u["bytes"] if u else 0)
    # Every actual closure capture is a reference. No owned cfg-dependent WASI
    # or cache value is captured, so the layout cannot grow in the unit context.
    captures=read(P/"closure-layout-custody.json")["actual_capture_debug_projections"]
    assert len(captures)==18
    for c in captures:
        for d in c["capture_debug_projections"]:
            assert re.search(r"\.\d+: &",d),d
    result=dict(schema=1,status="all claimed layout provenance decoded and checked; no floor selected",raw_unit_actual_types=len(unit),raw_production_extra_types=len(prod),actual_generic_role_variants=variants,provenance_routes=dict(routes),actual_reference_only_closure_templates=len(captures),completion_tuple_layouts=prod_comp,source_tree_sha256="575b55d3391729749039dc2badccc9107449cb2c9a021d8ef67282c39b2e1896",compiler_reproduction="fresh exact-source production+unit MIR; raw producer layout outputs independently decoded; no new type shim executed",acceptance=False)
    (HERE/"layout-provenance.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result))


if __name__=="__main__":main()
