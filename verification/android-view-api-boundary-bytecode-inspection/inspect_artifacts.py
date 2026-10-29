"""Finite read-only classfile/DEX evidence, never a Java/ART loader or release gate.

Public functions read artifacts and return JSON data or raise Refusal. No process,
network, timer, mutation, compiler or product import is used. Input custody and
producer tool/source command binding remain the caller's separate obligations.
"""
from pathlib import Path
import hashlib
import json
import struct
import zipfile
import zlib

FREEZE = "c458497920a6cf454433f2f96bbcdf42fbf8b6945e55e5a76c813dddb00af8ff"
MANIFEST = "e52dd5bd9c415a68c843724a24fec03c72c64dbce7fae2d18377c646a4b35834"
TREE = "d767f19554c88bd24f58663de268d7a80119522380cfeb4043c37d35b432a21e"
P = "dev/mixer/android/"
V = P + "NativeAppearanceViewsV2"
R = P + "NativeRenderer"
M = V + "$Mutation"
N = V + "$NativeField"
REC = V + "$Record"
SOURCES = frozenset(x + ".java" for x in (
    "AppearanceDescriptorV2", "AppearanceGeometryV2", "AppearanceNativePathsV2",
    "AppearanceResolverV2", "AuthoredToggleInputV2", "InstalledAppearanceV2",
    "Json", "NativeAppearanceViewsV2", "NativeCoordinatorV2", "NativeEditorConnectionV2",
    "NativeEnvironmentPlatformV2", "NativeEnvironmentV2", "NativeOwnerV2",
    "NativeRenderer", "OwnerLifecycleV2", "UiPacket"))
SETTERS = ("setTextCursorDrawable", "setTextSelectHandle", "setTextSelectHandleLeft", "setTextSelectHandleRight")
DRAW = "(Landroid/graphics/drawable/Drawable;)V"
STATE = "(Ljava/lang/CharSequence;)V"
HELPERS = {
    V + "$Api29": ("authoredSelection", "(L"+N+";L"+REC+";L"+M+";)V", 29),
    V + "$Api30": ("stateDescription", "(Landroid/view/View;Ljava/lang/CharSequence;L"+M+";)V", 30),
    R + "$Api30": ("stateDescription", "(Landroid/view/View;Ljava/lang/CharSequence;)V", 30),
}
LATER = frozenset(SETTERS + ("setStateDescription",))
LIMITS = [
    "Finite emitted instruction/reference evidence only; no JVM verification, Android linkage, ART/OEM/native/UI/IME/TalkBack or physical-device execution.",
    "Does not admit lower-API V2, public V2, complete matrix/BCI equivalence, source-pair promotion, OTA, release or GA.",
    "Producer must separately bind frozen source115/product16, compiler/SDK/D8 identities, flags and immutable artifact custody.",
    "DEX checksum/structure and exact references are separate from classfile evidence; unreviewed later-API synthetic outlining refuses.",
    "DEX annotation/debug/encoded-value semantics and general verifier correctness are outside the finite decoder; executable references and relevant method bodies are checked.",
]


class Refusal(ValueError):
    """Fail-closed bounded evidence refusal."""


def need(value, message):
    if not value:
        raise Refusal(message)


def identity(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


class Reader:
    def __init__(self, data):
        need(isinstance(data, bytes) and len(data) <= 64 * 1024 * 1024, "binary input type/size")
        self.data, self.at = data, 0

    def take(self, n):
        need(0 <= n <= len(self.data) - self.at, "truncated binary")
        out = self.data[self.at:self.at+n]
        self.at += n
        return out

    def u1(self): return self.take(1)[0]
    def u2(self): return int.from_bytes(self.take(2), "big")
    def u4(self): return int.from_bytes(self.take(4), "big")


def mutf8(raw):
    need(b"\0" not in raw, "literal NUL in MUTF8")
    try:
        value = raw.replace(b"\xc0\x80", b"\0").decode("utf-8", "surrogatepass")
    except UnicodeError as e:
        raise Refusal("invalid MUTF8") from e
    return value


class ClassFile:
    """Bounded JVMS class/Code/constant-pool decoder (no execution)."""
    def __init__(self, data):
        r = Reader(data)
        need(r.take(4) == b"\xca\xfe\xba\xbe", "class magic")
        self.minor, self.major = r.u2(), r.u2()
        need(45 <= self.major <= 69 and self.minor == 0, "class version outside selected non-preview format")
        count = r.u2()
        need(count > 0, "empty constant pool")
        self.cp = [None] * count
        i = 1
        while i < count:
            tag = r.u1()
            if tag == 1: value = mutf8(r.take(r.u2()))
            elif tag in (7, 8, 16, 19, 20): value = r.u2()
            elif tag in (9, 10, 11, 12, 17, 18): value = (r.u2(), r.u2())
            elif tag in (3, 4): value = r.take(4)
            elif tag in (5, 6): value = r.take(8)
            elif tag == 15: value = (r.u1(), r.u2())
            else: raise Refusal("unknown class constant-pool tag " + str(tag))
            self.cp[i] = (tag, value)
            if tag in (5, 6):
                i += 1
                need(i < count, "wide constant pool slot")
            i += 1
        self.access, self.name = r.u2(), self.cls(r.u2())
        parent = r.u2()
        self.parent = self.cls(parent) if parent else None
        self.interfaces = [self.cls(r.u2()) for _ in range(r.u2())]
        self.fields, self.methods = {}, {}
        for table in (self.fields, self.methods):
            for _ in range(r.u2()):
                flags, name, desc = r.u2(), self.utf(r.u2()), self.utf(r.u2())
                need((name, desc) not in table, "duplicate class member")
                attrs = self.attrs(r)
                row = {"access": flags}
                if "Code" in attrs:
                    need(table is self.methods, "Code on field")
                    cr = Reader(attrs["Code"])
                    row["max_stack"], row["max_locals"] = cr.u2(), cr.u2()
                    row["code"] = cr.take(cr.u4())
                    need(0 < len(row["code"]) <= 65535, "Code size")
                    row["handlers"] = [(cr.u2(), cr.u2(), cr.u2(), cr.u2()) for _ in range(cr.u2())]
                    self.attrs(cr)
                    need(cr.at == len(cr.data), "trailing Code bytes")
                    row["instructions"] = self.decode(row["code"])
                    starts = {x["pc"] for x in row["instructions"]}
                    for a, b, c, t in row["handlers"]:
                        need(a in starts and (b == len(row["code"]) or b in starts) and a < b and c in starts, "exception handler bounds")
                        if t: self.cls(t)
                table[(name, desc)] = row
        attrs = self.attrs(r)
        need(r.at == len(data), "trailing class bytes")
        self.source = None
        if "SourceFile" in attrs:
            need(len(attrs["SourceFile"]) == 2, "SourceFile length")
            self.source = self.utf(int.from_bytes(attrs["SourceFile"], "big"))
        self.nest_host=None;self.inner_classes=[]
        if "NestHost" in attrs:
            need(len(attrs["NestHost"])==2,"NestHost length")
            self.nest_host=self.cls(int.from_bytes(attrs["NestHost"],"big"))
        if "InnerClasses" in attrs:
            ir=Reader(attrs["InnerClasses"])
            for _ in range(ir.u2()):
                inner,outer,name,flags=ir.u2(),ir.u2(),ir.u2(),ir.u2()
                self.inner_classes.append({"inner":self.cls(inner),"outer":self.cls(outer) if outer else None,"name":self.utf(name) if name else None,"access":flags})
            need(ir.at==len(ir.data),"trailing InnerClasses bytes")
        self.refs = [self.ref(i) for i, item in enumerate(self.cp) if item and item[0] in (9, 10, 11)]

    def item(self, index, tags):
        need(0 < index < len(self.cp) and self.cp[index] is not None and self.cp[index][0] in tags, "constant-pool type/index")
        return self.cp[index][1]

    def utf(self, i): return self.item(i, (1,))
    def cls(self, i): return self.utf(self.item(i, (7,)))

    def ref(self, i):
        owner, nt = self.item(i, (9, 10, 11))
        name, desc = self.item(nt, (12,))
        return [self.cls(owner), self.utf(name), self.utf(desc)]

    def attrs(self, r):
        out = {}
        for _ in range(r.u2()):
            name, data = self.utf(r.u2()), r.take(r.u4())
            need(name not in out, "duplicate attribute " + name)
            out[name] = data
        return out

    def decode(self, code):
        out, pc = [], 0
        # JVMS fixed widths including operands; all reserved/breakpoint opcodes refuse.
        widths = dict.fromkeys(range(0x00, 0xca), 1)
        for op in (0x10, 0x12, *range(0x15, 0x1a), *range(0x36, 0x3b), 0xa9, 0xbc): widths[op] = 2
        for op in (0x11, 0x13, 0x14, 0x84, *range(0x99, 0xa9), *range(0xb2, 0xb9), 0xbb, 0xbd, 0xc0, 0xc1, 0xc6, 0xc7): widths[op] = 3
        widths.update({0xb9:5, 0xba:5, 0xc5:4, 0xc8:5, 0xc9:5})
        while pc < len(code):
            op = code[pc]
            need(op in widths, "reserved JVM opcode")
            size = widths[op]
            targets = []
            if op in (0xaa, 0xab):
                a = (pc + 4) & ~3
                need(a+8 <= len(code), "truncated switch")
                default = int.from_bytes(code[a:a+4], "big", signed=True)
                if op == 0xaa:
                    need(a+12 <= len(code), "truncated tableswitch")
                    lo, hi = struct.unpack_from(">ii", code, a+4)
                    need(0 <= hi-lo <= 65535, "tableswitch bounds")
                    count, start = hi-lo+1, a+12
                else:
                    count = int.from_bytes(code[a+4:a+8], "big", signed=True)
                    need(0 <= count <= 65535, "lookupswitch bounds")
                    start = a+8
                end = start + count * (4 if op == 0xaa else 8)
                need(end <= len(code), "truncated switch entries")
                offsets = [int.from_bytes(code[start+i*(4 if op == 0xaa else 8)+(0 if op == 0xaa else 4):start+i*(4 if op == 0xaa else 8)+(4 if op == 0xaa else 8)], "big", signed=True) for i in range(count)]
                targets = [pc+default] + [pc+x for x in offsets]
                size = end-pc
            elif op == 0xc4:
                need(pc+2 <= len(code), "truncated wide")
                sub = code[pc+1]
                need(sub in (*range(0x15,0x1a), *range(0x36,0x3b), 0x84,0xa9), "wide opcode")
                size = 6 if sub == 0x84 else 4
            need(pc+size <= len(code), "truncated JVM instruction")
            row = {"pc":pc, "op":op, "operands":list(code[pc+1:pc+size]), "targets":targets}
            if op in (*range(0x99,0xa9),0xc6,0xc7,0xc8,0xc9):
                row["targets"] = [pc+int.from_bytes(code[pc+1:pc+size], "big", signed=True)]
            if 0xb2 <= op <= 0xb9:
                ref_index=int.from_bytes(code[pc+1:pc+3], "big")
                tags=(9,) if op<=0xb5 else (11,) if op==0xb9 else (10,) if op==0xb6 else (10,11)
                self.item(ref_index,tags)
                row["ref"] = self.ref(ref_index)
            if op in (0xbb,0xbd,0xc0,0xc1,0xc5): row["type"] = self.cls(int.from_bytes(code[pc+1:pc+3], "big"))
            if op == 0xb9: need(code[pc+4] == 0 and code[pc+3] != 0, "invokeinterface operands")
            if op == 0xba:
                self.item(int.from_bytes(code[pc+1:pc+3], "big"), (18,))
                need(code[pc+3:pc+5] == b"\0\0", "invokedynamic operands")
            out.append(row)
            pc += size
        starts = {x["pc"] for x in out}
        need(all(t in starts for x in out for t in x["targets"]), "JVM branch target not instruction")
        return out


def _aload(row, slot):
    return row["op"] == 0x2a + slot if 0 <= slot <= 3 else row["op"] == 0x19 and row["operands"] == [slot]


def _class_helper(c, owner):
    name, desc, api = HELPERS[owner]
    need((name,desc) in c.methods, "missing exact helper entry " + owner)
    m = c.methods[(name,desc)]
    need(m["access"] & 8 and not m.get("handlers"), "helper must be static and handler-free")
    need(not c.fields and c.parent=="java/lang/Object", "helper field/superclass topology")
    outer,inner_name=owner.rsplit("$",1)
    nesting=[x for x in c.inner_classes if x["inner"]==owner]
    need(c.nest_host==outer and nesting==[{"inner":owner,"outer":outer,"name":inner_name,"access":0x1a}],"exact emitted private static final helper nesting")
    ctor=c.methods.get(("<init>","()V"),{})
    ci=ctor.get("instructions",[])
    need(ctor.get("access")==2 and not ctor.get("handlers") and len(ci)==3 and _aload(ci[0],0) and ci[1]["op"]==0xb7 and ci[1].get("ref")==["java/lang/Object","<init>","()V"] and ci[2]["op"]==0xb1,"exact inert private helper constructor")
    ins = m.get("instructions", [])
    need(ins, "helper without instructions")
    cursor = 0
    proof = []
    def eat(predicate, why):
        nonlocal cursor
        need(cursor < len(ins) and predicate(ins[cursor]), owner + ": " + why)
        out = ins[cursor]
        cursor += 1
        return out
    def load(slot): return eat(lambda x:_aload(x,slot), "original parameter load " + str(slot))
    def invoke(op, ref): return eat(lambda x:x["op"] == op and x.get("ref") == list(ref), "exact invocation " + str(ref))
    if api == 29:
        for i, setter in enumerate(SETTERS):
            drawable = V + ("$Cursor" if i == 0 else "$Handle")
            load(0)
            new = eat(lambda x:x["op"] == 0xbb and x.get("type") == drawable, "distinct authored drawable allocation")
            eat(lambda x:x["op"] == 0x59, "drawable dup")
            load(1)
            invoke(0xb7,(drawable,"<init>","(L"+REC+";)V"))
            call = invoke(0xb6,(N,setter,DRAW))
            load(2)
            post = invoke(0xb6,(M,"require","()V"))
            proof.append({"native":call,"allocation_pc":new["pc"],"record_parameter":1,"mutation_parameter":2,"postcheck":post})
    else:
        load(0); load(1)
        call = invoke(0xb6,("android/view/View","setStateDescription",STATE))
        post = None
        if owner.startswith(V):
            load(2)
            post = invoke(0xb6,(M,"require","()V"))
        proof.append({"native":call,"mutation_parameter":2 if post else None,"postcheck":post})
    eat(lambda x:x["op"] == 0xb1, "void return")
    need(cursor == len(ins), "unreviewed extra helper instructions")
    need(set(c.methods) == {("<init>","()V"),(name,desc)}, "unreviewed helper member topology")
    return {"owner":owner,"entry":[name,desc],"api":api,"nest_host":c.nest_host,"inner_class":nesting[0],"exact_straight_line_shape":True,"native_calls":proof,"legacy_no_mutation_contract":owner == R+"$Api30"}


def _cfg(ins, handlers=(), dex=False):
    edges = {}
    for i,x in enumerate(ins):
        op, pc = x["op"], x["pc"]
        terminal = op in ((0x0e,0x0f,0x10,0x11,0x27) if dex else (*range(0xac,0xb2),0xbf))
        unconditional = op in ((0x28,0x29,0x2a) if dex else (0xa7,0xc8))
        switch = op in ((0x2b,0x2c) if dex else (0xaa,0xab))
        need(dex or op not in (0xa8,0xa9,0xc9), "JVM subroutine requires expanded proof")
        dest = set(x.get("targets", []))
        if not terminal and not unconditional and not switch and i+1 < len(ins): dest.add(ins[i+1]["pc"])
        if dex and switch and i+1 < len(ins): dest.add(ins[i+1]["pc"])
        for a,b,c,_ in handlers:
            if a <= pc < b: dest.add(c)
        edges[pc] = dest
    return edges


def _reachable(edges, start, blocked=None):
    found, todo = set(), [start]
    while todo:
        p = todo.pop()
        if p in found or p == blocked: continue
        found.add(p)
        todo.extend(edges.get(p, ()))
    return found


def _guard_chain(edges, read, const, branch):
    # No control-flow entrance may bypass the real SDK read or replace its stack/
    # register operand by entering in the middle of the three-instruction chain.
    predecessors=lambda pc:{p for p,dest in edges.items() if pc in dest}
    return predecessors(const["pc"])=={read["pc"]} and predecessors(branch["pc"])=={const["pc"]}


def _class_guard(c, key, target, api):
    m=c.methods[key]; ins=m.get("instructions",[]); edges=_cfg(ins,m.get("handlers",()))
    calls=[x for x in ins if x.get("ref") == [target,*HELPERS[target][:2]] and x["op"] == 0xb8]
    need(len(calls) == 1, "exactly one guarded helper invocation " + target)
    call=calls[0]; candidates=[]
    caller_identity=None
    if target.startswith(V):
        need(c.name==REC and key==("bind","(L"+V+"$Binding;L"+V+"$Geometry;ZL"+M+";)V"),"exact V2 caller descriptor")
        # The original final Mutation parameter is local4; no emitted store may
        # replace it. This proves the helper receives that same captured object.
        for x in ins:
            op=x["op"];slot=None;wide=False
            if 0x36<=op<=0x3a:slot=x["operands"][0]
            elif 0x3b<=op<=0x4e:slot=(op-0x3b)%4
            elif op==0xc4 and x["operands"][0] in range(0x36,0x3b):slot=int.from_bytes(bytes(x["operands"][1:3]),"big")
            if op in (0x37,0x39) or 0x3f<=op<=0x42 or 0x47<=op<=0x4a:wide=True
            if op==0xc4 and x["operands"][0] in (0x37,0x39):wide=True
            if op==0x84:slot=x["operands"][0]
            if op==0xc4 and x["operands"][0]==0x84:slot=int.from_bytes(bytes(x["operands"][1:3]),"big")
            need(slot!=4 and not (wide and slot==3),"original caller Mutation local overwritten")
        pos=ins.index(call)
        need(pos>0 and _aload(ins[pos-1],4),"helper must receive original caller Mutation")
        if api==29:need(pos>1 and _aload(ins[pos-2],0),"drawable helper must receive original Record this")
        caller_identity={"mutation_parameter_local":4,"never_overwritten":True,"last_argument_instruction":ins[pos-1],"record_this_argument":api==29}
    for i,x in enumerate(ins[:-2]):
        if x["op"] != 0xb2 or x.get("ref") != ["android/os/Build$VERSION","SDK_INT","I"]: continue
        const,branch=ins[i+1:i+3]
        if const["op"] != 0x10 or const["operands"] != [api] or branch["op"] != 0xa1: continue
        if not _guard_chain(edges,x,const,branch):continue
        low=branch["targets"][0]; high=ins[i+3]["pc"]
        if call["pc"] not in _reachable(edges,high) or call["pc"] in _reachable(edges,low): continue
        if call["pc"] in _reachable(edges,ins[0]["pc"],branch["pc"]): continue
        candidates.append({"sdk_read":x,"threshold":api,"branch":branch,"below_api_successor":low,"supported_successor":high,"call":call,"normal_and_exception_cfg_dominance":True})
    need(len(candidates) == 1, "helper SDK_INT guard/dominance proof " + target)
    return {"caller":[c.name,*key],"caller_original_identity":caller_identity,**candidates[0]}


def _class_admission(c, key):
    m=c.methods[key]; ins=m.get("instructions",[])
    result=[]
    for i,x in enumerate(ins[:-2]):
        if x.get("ref") == ["android/os/Build$VERSION","SDK_INT","I"] and x["op"] == 0xb2:
            const,branch=ins[i+1:i+3]
            if const["op"] == 0x10 and const["operands"] == [36] and branch["op"] in (0xa1,0xa2):
                result.append({"sdk_read":x,"threshold":36,"branch":branch})
    need(len(result)==1,"independent <36 admission guard absent/ambiguous " + c.name)
    # Report instruction evidence, not a general all-path semantic denial proof.
    return {"caller":[c.name,*key],"observed_actual_sdk_compare":result[0],"full_runtime_denial":"requires separate focused execution"}


def _resolve(c, name, desc, classes):
    path=[]; seen=set()
    while c is not None:
        need(c not in seen,"cyclic superclass")
        seen.add(c); path.append(c)
        if c not in classes: return {"path":path,"resolved":False,"external_terminal":c}
        obj=classes[c]
        if (name,desc) in obj.methods: return {"path":path,"resolved":True,"declaration_owner":c}
        c=obj.parent
    return {"path":path,"resolved":False,"external_terminal":None}


def _bounded_file(path, maximum=64*1024*1024):
    p=Path(path)
    need(p.is_file() and not p.is_symlink(), "artifact missing/nonregular/symlink " + str(p))
    need(p.stat().st_size <= maximum, "artifact file size bound")
    data=p.read_bytes()
    need(len(data)<=maximum,"artifact grew beyond bound")
    return data


def _inspect_classes(classes_root, *, platform_jar=None):
    """Read one closed output directory; platform_jar optionally resolves inherited APIs."""
    root=Path(classes_root)
    need(root.is_dir() and not root.is_symlink(),"class root absent/symlink")
    paths=[];todo=[root];seen=0
    while todo:
        directory=todo.pop()
        need(len(directory.relative_to(root).parts)<=12,"class directory depth bound")
        for p in directory.iterdir():
            seen+=1;need(seen<=4096,"class directory entry bound")
            need(not p.is_symlink(),"class tree symlink")
            if p.is_dir():todo.append(p)
            elif p.suffix==".class":paths.append(p)
    paths.sort()
    need(1 <= len(paths) <= 2048,"class member count bound")
    classes={}; rows=[]; total=0
    for p in paths:
        need(all(not (root/x).is_symlink() for x in p.relative_to(root).parents),"class directory symlink")
        data=_bounded_file(p,4*1024*1024); total+=len(data)
        need(total<=32*1024*1024,"class total byte bound")
        c=ClassFile(data)
        need(c.name not in classes and p.relative_to(root).as_posix() == c.name+".class","class owner/path identity")
        classes[c.name]=c
        rows.append({"path":p.relative_to(root).as_posix(),"owner":c.name,"source_file":c.source,"superclass":c.parent,"identity":identity(data)})
    product={n:c for n,c in classes.items() if n.startswith(P) and c.source in SOURCES}
    need(all(n==P+c.source[:-5] or n.startswith(P+c.source[:-5]+"$") for n,c in product.items()),"product owner/SourceFile family mismatch")
    need({c.source for c in product.values()} == SOURCES,"all exact sixteen source-class groups required")
    need(all(P+s[:-5] in product for s in SOURCES),"sixteen top-level source identities")
    excluded_sources=("NativeBridge.java","ConcreteHostProbe.java","ViewApiBoundaryTests.java")
    unknown=[n for n,c in classes.items() if n.startswith(P) and n not in product and not (c.source in excluded_sources and (n==P+c.source[:-5] or n.startswith(P+c.source[:-5]+"$")))]
    need(not unknown,"unknown product ownership/source class " + str(unknown))
    need(set(HELPERS)<=set(product),"three emitted helpers required")
    helper_proofs=[_class_helper(product[n],n) for n in HELPERS]
    refs=[]; invokes=[]
    for n,c in product.items():
        for ref in c.refs:
            if ref[1] not in LATER: continue
            expected=V+"$Api29" if ref[1] in SETTERS else {V+"$Api30",R+"$Api30"}
            need(n == expected if isinstance(expected,str) else n in expected,"later API CP reference escaped helper " + n)
            need(ref[2] == (DRAW if ref[1] in SETTERS else STATE),"later API descriptor mismatch")
            refs.append({"class":n,"reference":ref})
        for key,m in c.methods.items():
            for x in m.get("instructions",[]):
                if x.get("ref",[None])[0] in HELPERS:
                    invokes.append({"caller":[n,*key],"instruction":x})
    need(len(refs)==6,"exact six per-helper constant pool native references")
    need(len(invokes)==3,"exact three helper invocation sites")
    bind=[k for k in product[REC].methods if k[0]=="bind"]
    legacy=[k for k in product[R].methods if k[0]=="bind"]
    need(len(bind)==len(legacy)==1,"actual unique Record and Renderer bind methods")
    guards=[_class_guard(product[REC],bind[0],V+"$Api29",29),_class_guard(product[REC],bind[0],V+"$Api30",30),_class_guard(product[R],legacy[0],R+"$Api30",30)]
    observer=P+"NativeEnvironmentV2$Observer"
    obs=[k for k in product[observer].methods if k[0]=="<init>"]
    live=[k for k in product[R].methods if k[0]=="requireV2Live"]
    need(len(obs)==len(live)==1,"unique independent admission methods")
    admissions=[_class_admission(product[observer],obs[0]),_class_admission(product[R],live[0])]
    declaration_classes=dict(classes); platform=None
    if platform_jar is not None:
        raw=_bounded_file(platform_jar,128*1024*1024)
        # Reading an archive is data parsing, never class loading. Limit to the known hierarchy.
        import io
        with zipfile.ZipFile(io.BytesIO(raw)) as jar:
            for name in ("android/widget/EditText","android/widget/TextView","android/view/View"):
                info=jar.getinfo(name+".class")
                need(info.file_size<=4*1024*1024,"platform class bound")
                c=ClassFile(jar.read(info))
                need(c.name==name,"platform class identity")
                declaration_classes[name]=c
        platform=identity(raw)
    need(product[N].parent=="android/widget/EditText","actual NativeField superclass")
    resolution=[{"symbolic_owner":N,"name":name,"descriptor":DRAW,**_resolve(N,name,DRAW,declaration_classes)} for name in SETTERS]
    if platform_jar is not None:
        need(all(x["resolved"] and x["declaration_owner"]=="android/widget/TextView" and x["path"]==[N,"android/widget/EditText","android/widget/TextView"] for x in resolution),"official SDK inherited setter resolution")
    limitations=list(LIMITS)
    if platform_jar is None: limitations.append("External platform hierarchy may remain unresolved; provide pinned platform_jar for exact declaration-owner evidence.")
    return {"schema_version":1,"kind":"classfile","accepted":True,"scope":"finite helper isolation and classfile instruction proof","source_binding":{"freeze_sha256":FREEZE,"manifest_sha256":MANIFEST,"product_tree":TREE,"custody_verified_by_this_function":False},"artifacts":rows,"product_class_count":len(product),"excluded_classes":[n for n in classes if n not in product],"helpers":helper_proofs,"later_api_constant_pool_references":refs,"helper_invocations":invokes,"guards":guards,"independent_api36_comparisons":admissions,"inherited_method_resolution":resolution,"platform_jar":platform,"limitations":limitations}


class Dex:
    """Bounded DEX039 reader, adapted from independently reviewed collections decoder.

    Global method/field IDs are parsed independently of actual instructions. Code
    bodies decode every opcode; reserved opcodes/call-sites/method handles refuse.
    Debug/annotations are bounded by file/map, not semantically interpreted here.
    """
    def __init__(self,data):
        need(isinstance(data,bytes) and 112<=len(data)<=32*1024*1024,"DEX byte bound")
        self.data=data
        need(data[:8]==b"dex\n039\0","selected DEX039 magic")
        need(self.u32(32)==len(data) and self.u32(36)==112 and self.u32(40)==0x12345678,"DEX header/endianness")
        need(hashlib.sha1(data[32:]).digest()==data[12:32],"DEX SHA1")
        need(zlib.adler32(data[12:])&0xffffffff==self.u32(8),"DEX Adler32")
        need(self.u32(44)==self.u32(48)==0,"DEX link section unreviewed")
        self.map={}; at=self.u32(52); self.bound(at,4); count=self.u32(at)
        need(1<=count<=32,"DEX map count")
        self.bound(at+4,count*12)
        last=-1
        allowed={0,1,2,3,4,5,6,0x1000,0x1001,0x1002,0x1003,0x2000,0x2001,0x2002,0x2003,0x2004,0x2005,0x2006}
        for i in range(count):
            kind,unused,size,start=struct.unpack_from("<HHII",data,at+4+i*12)
            need(kind in allowed and kind not in self.map and unused==0 and size>0 and start>last,"DEX map kind/count/order")
            need(size<=100000,"DEX section item bound")
            self.bound(start,1); self.map[kind]={"count":size,"offset":start}; last=start
        need(self.map.get(0)=={"count":1,"offset":0} and self.map.get(0x1000)=={"count":1,"offset":at},"DEX header/map identity")
        need(self.map.get(0x2001,{}).get("count",0)<=8192,"DEX code body count bound")
        need(self.u32(104)+self.u32(108)==len(data) and self.u32(108)>=112,"DEX data section bounds")
        self.within(0,0,112);self.within(0x1000,at,4+count*12)
        for kind,count_at,size in [(1,56,4),(2,64,4),(3,72,12),(4,80,8),(5,88,8),(6,96,32)]:
            n,start=self.u32(count_at),self.u32(count_at+4)
            need(n<=65535,"DEX ID count bound")
            need((n==0 and start==0 and kind not in self.map) or self.map.get(kind)=={"count":n,"offset":start},"DEX header/map disagreement")
            if n:
                need(start%4==0,"DEX ID alignment")
                self.within(kind,start,n*size)
        string_offsets=[self.u32(self.u32(60)+4*i) for i in range(self.u32(56))]
        need(len(set(string_offsets))==len(string_offsets) and len(string_offsets)==self.map.get(0x2002,{}).get("count",0),"DEX exact string data item count")
        self.strings=[self.string(a) for a in string_offsets]
        self.types=[self.index(self.strings,self.u32(self.u32(68)+4*i),"type string") for i in range(self.u32(64))]
        self.protos=[]
        for i in range(self.u32(72)):
            a=self.u32(76)+12*i
            self.index(self.strings,self.u32(a),"shorty")
            self.protos.append("("+"".join(self.typelist(self.u32(a+8)))+")"+self.index(self.types,self.u32(a+4),"return type"))
        self.fields=[]; self.methods=[]
        for i in range(self.u32(80)):
            owner,typ,name=struct.unpack_from("<HHI",data,self.u32(84)+8*i)
            self.fields.append([self.owner(owner),self.index(self.strings,name,"field name"),self.index(self.types,typ,"field type")])
        for i in range(self.u32(88)):
            owner,proto,name=struct.unpack_from("<HHI",data,self.u32(92)+8*i)
            self.methods.append([self.owner(owner),self.index(self.strings,name,"method name"),self.index(self.protos,proto,"method proto")])
        need(len({tuple(x) for x in self.methods})==len(self.methods),"duplicate DEX method id")
        self.classes={}; self.code={}; self.definitions={}; self.code_offsets=set();class_data_offsets=set();self.total_code_units=0
        for i in range(self.u32(96)):
            a=self.u32(100)+32*i
            owner=self.owner(self.u32(a)); flags=self.u32(a+4); parent=self.u32(a+8); source=self.u32(a+16)
            need(owner not in self.classes,"duplicate DEX class")
            self.classes[owner]={"access":flags,"parent":None if parent==0xffffffff else self.owner(parent),"source_file":None if source==0xffffffff else self.index(self.strings,source,"source file"),"interfaces":self.typelist(self.u32(a+12))}
            for kind,offset in [(0x2006,self.u32(a+20)),(0x2005,self.u32(a+28))]:
                if offset:self.within(kind,offset,1)
            pos=self.u32(a+24)
            if not pos:continue
            need(pos not in class_data_offsets,"DEX duplicate class-data offset");class_data_offsets.add(pos);start=pos;self.within(0x2000,pos,1)
            counts=[]
            for _ in range(4):v,pos=self.leb(pos);counts.append(v)
            need(sum(counts)<=65535,"DEX class data member bound")
            for n in counts[:2]:
                idx=0
                for j in range(n):
                    delta,pos=self.leb(pos); ff,pos=self.leb(pos);idx+=delta
                    need((j==0 or delta>0) and self.index(self.fields,idx,"encoded field")[0]==owner,"DEX encoded field owner/order")
            for n in counts[2:]:
                idx=0
                for j in range(n):
                    delta,pos=self.leb(pos); mf,pos=self.leb(pos); off,pos=self.leb(pos);idx+=delta
                    need((j==0 or delta>0) and self.index(self.methods,idx,"encoded method")[0]==owner and idx not in self.definitions,"DEX encoded method owner/order/duplicate")
                    self.definitions[idx]=mf
                    if off:
                        need(off not in self.code_offsets and off%4==0,"DEX code alignment/alias")
                        self.code_offsets.add(off);self.code[idx]=self.decode_code(idx,off)
                    else:need(mf&0x500,"nonabstract/nonnative method without code")
            self.within(0x2000,start,pos-start)
        need(len(self.code)==self.map.get(0x2001,{}).get("count",0),"all DEX code items consumed")
        need(len(class_data_offsets)==self.map.get(0x2000,{}).get("count",0),"all DEX class data items consumed")

    def bound(self,at,n):need(isinstance(at,int) and isinstance(n,int) and at>=0 and n>=0 and at+n<=len(self.data),"DEX binary bounds")
    def within(self,kind,at,n):
        need(kind in self.map,"DEX missing data section "+hex(kind))
        start=self.map[kind]["offset"];end=min([x["offset"] for x in self.map.values() if x["offset"]>start]+[len(self.data)])
        need(start<=at and n>=0 and at+n<=end,"DEX section bounds "+hex(kind))
    def u16(self,at):self.bound(at,2);return struct.unpack_from("<H",self.data,at)[0]
    def u32(self,at):self.bound(at,4);return struct.unpack_from("<I",self.data,at)[0]
    def index(self,table,index,label):need(0<=index<len(table),"DEX "+label+" index");return table[index]
    def owner(self,i):
        t=self.index(self.types,i,"owner")
        # Array clone may legally appear in a method ID; keep its descriptor exact.
        if t.startswith("["):return t
        need(t.startswith("L") and t.endswith(";"),"DEX owner descriptor")
        return t[1:-1]
    def leb(self,at,signed=False):
        value=0
        for shift in range(0,35,7):
            self.bound(at,1);b=self.data[at];at+=1;value|=(b&127)<<shift
            if not b&128:
                if signed and b&64:value-=1<<(shift+7)
                need(signed or value<=0xffffffff,"DEX ULEB overflow")
                return value,at
        raise Refusal("invalid DEX LEB128")
    def string(self,at):
        origin=at;self.within(0x2002,at,1)
        length,at=self.leb(at);need(length<=1024*1024,"DEX string bound")
        end=self.data.find(b"\0",at,min(len(self.data),at+3*length+1))
        need(end>=at,"DEX unterminated string")
        value=mutf8(self.data[at:end])
        self.within(0x2002,origin,end+1-origin)
        need(len(value.encode("utf-16-le","surrogatepass"))//2==length,"DEX MUTF8 length")
        return value
    def typelist(self,at):
        if not at:return []
        need(at%4==0,"DEX typelist alignment");n=self.u32(at);need(n<=65535,"DEX typelist count");self.bound(at+4,n*2)
        self.within(0x1001,at,4+n*2)
        return [self.index(self.types,self.u16(at+4+2*i),"typelist") for i in range(n)]
    def decode_code(self,index,at):
        self.within(0x2001,at,16);registers,ins,outs,tries=struct.unpack_from("<HHHH",self.data,at)
        debug=self.u32(at+8)
        if debug:self.within(0x2003,debug,1)
        need(ins<=registers,"DEX input register count");size=self.u32(at+12)
        need(0<size<=65535,"DEX code unit bound");self.total_code_units+=size
        need(self.total_code_units<=524288,"DEX total code unit bound");self.within(0x2001,at+16,size*2)
        words=list(struct.unpack_from("<"+"H"*size,self.data,at+16));widths={}
        for ops,width in [([0,1,4,7]+list(range(10,19))+[29,30,33,39,40]+list(range(123,144))+list(range(176,208)),1),([2,5,8,19,21,22,25,26,28,31,32,34,35,41]+list(range(45,62))+list(range(68,110))+list(range(144,176))+list(range(208,227)),2),([3,6,9,20,23,27,36,37,38,42,43,44]+list(range(110,115))+list(range(116,121)),3),([24],5)]:widths.update(dict.fromkeys(ops,width))
        out=[];pc=0
        def signed(v,bits):return v-(1<<bits) if v&(1<<(bits-1)) else v
        while pc<size:
            op=words[pc]&255;word=words[pc];payload=op==0 and word!=0
            if payload:
                need(pc%2==0 and pc+2<=size,"DEX payload alignment/bounds")
                if word==0x100:width=4+2*words[pc+1]
                elif word==0x200:width=2+4*words[pc+1]
                elif word==0x300:
                    need(pc+4<=size and words[pc+1] in (1,2,4,8),"DEX array payload")
                    width=4+(words[pc+1]*(words[pc+2]|words[pc+3]<<16)+1)//2
                else:raise Refusal("DEX unknown payload")
            else:need(op in widths,"DEX reserved/unreviewed opcode "+hex(op));width=widths[op]
            need(pc+width<=size,"DEX instruction width")
            row={"pc":pc,"op":op,"words":words[pc:pc+width],"targets":[],"payload":payload}
            if op in list(range(110,115))+list(range(116,121)):
                row["ref"]=self.index(self.methods,words[pc+1],"invoke")
                if op<=114:
                    n=word>>12;need(n<=5,"DEX invoke register count")
                    w=words[pc+2];row["registers"]=[w&15,(w>>4)&15,(w>>8)&15,w>>12,(word>>8)&15][:n]
                else:
                    n=word>>8;row["registers"]=list(range(words[pc+2],words[pc+2]+n))
                need(all(x<registers for x in row["registers"]) and len(row["registers"])<=outs,"DEX invoke registers/outs")
            if 82<=op<=109:row["field"]=self.index(self.fields,words[pc+1],"field")
            if op in (0x1c,0x1f,0x20,0x22,0x23,0x24,0x25):row["type"]=self.index(self.types,words[pc+1],"instruction type")
            if op==0x1a:self.index(self.strings,words[pc+1],"const string")
            if op==0x1b:self.index(self.strings,words[pc+1]|words[pc+2]<<16,"jumbo string")
            if op==0x28:row["targets"]=[pc+signed(word>>8,8)]
            if op==0x29 or 0x32<=op<=0x3d:row["targets"]=[pc+signed(words[pc+1],16)]
            if op==0x2a:row["targets"]=[pc+signed(words[pc+1]|words[pc+2]<<16,32)]
            if op in (0x2b,0x2c,0x26):
                payload_pc=pc+signed(words[pc+1]|words[pc+2]<<16,32)
                need(0<=payload_pc<size and payload_pc%2==0,"DEX payload reference")
                row["payload_pc"]=payload_pc
                expected={0x2b:0x100,0x2c:0x200,0x26:0x300}[op]
                need(words[payload_pc]==expected,"DEX payload kind")
                if op!=0x26:
                    n=words[payload_pc+1];start=payload_pc+(4 if op==0x2b else 2+2*n)
                    need(start+2*n<=size,"DEX switch bounds")
                    row["targets"]=[pc+signed(words[start+2*j]|words[start+2*j+1]<<16,32) for j in range(n)]
            out.append(row);pc+=width
        starts={x["pc"] for x in out if not x["payload"]}
        need(all(t in starts for x in out for t in x["targets"]),"DEX branch to noninstruction/payload")
        handlers=[]
        if tries:
            try_at=at+16+size*2+(2 if size%2 else 0);self.within(0x2001,try_at,tries*8)
            hbase=try_at+tries*8;hcount,pos=self.leb(hbase);need(hcount<=65535,"DEX catch count");decoded={}
            for _ in range(hcount):
                rel=pos-hbase;n,pos=self.leb(pos,True);need(abs(n)<=65535,"DEX catch type count");dest=[]
                for _ in range(abs(n)):
                    typ,pos=self.leb(pos);addr,pos=self.leb(pos);self.index(self.types,typ,"catch type");need(addr in starts,"DEX catch address");dest.append(addr)
                if n<=0:addr,pos=self.leb(pos);need(addr in starts,"DEX catchall address");dest.append(addr)
                decoded[rel]=dest
            self.within(0x2001,hbase,pos-hbase)
            previous_end=0
            for j in range(tries):
                a,count,hoff=struct.unpack_from("<IHH",self.data,try_at+8*j)
                need(a in starts and count>0 and a>=previous_end and a+count<=size and hoff in decoded,"DEX try bounds/order/handler")
                previous_end=a+count
                for dest in decoded[hoff]:handlers.append((a,a+count,dest,0))
        return {"registers":registers,"ins":ins,"outs":outs,"instructions":out,"handlers":handlers,"code_units":size}


def _dex_helper(d,owner):
    name,desc,api=HELPERS[owner];target=[owner,name,desc]
    ids=[i for i,r in enumerate(d.methods) if r==target]
    need(len(ids)==1 and ids[0] in d.code and d.definitions[ids[0]]&8,"exact DEX static helper body")
    m=d.code[ids[0]];need(not m["handlers"],"DEX helper handlers require review")
    nparam=3 if owner.startswith(V) else 2
    need(m["ins"]==nparam,"DEX helper parameter width")
    env={m["registers"]-nparam+i:("param",i) for i in range(nparam)}
    allocations={};calls=[];postchecks=[];need_post=False;pending_allocation=None
    for x in m["instructions"]:
        op=x["op"];w=x["words"];need(not x["payload"],"DEX helper payload")
        if op in (0x07,0x08,0x09):
            if op==7:a,b=(w[0]>>8)&15,w[0]>>12
            elif op==8:a,b=w[0]>>8,w[1]
            else:a,b=w[1],w[2]
            need(b in env,"DEX helper unknown move source");env[a]=env[b];continue
        if op==0x22:
            need(not need_post and api==29 and pending_allocation is None,"DEX allocation reordered around setter/postcheck")
            expected_type="L"+V+("$Cursor;" if len(calls)==0 else "$Handle;")
            need(len(calls)<4 and x["type"]==expected_type,"DEX next authored allocation kind/order")
            a=w[0]>>8;token=("new",x["pc"]);env[a]=token;allocations[token]={"type":x["type"],"initialized":False,"pc":x["pc"]};pending_allocation=token;continue
        if op in (0x6e,0x70,0x74,0x76):
            ref=x["ref"];args=[env.get(r) for r in x["registers"]]
            if ref[1]=="<init>":
                need(op in (0x70,0x76) and not need_post and len(args)==2 and args[0] in allocations and args[0]==pending_allocation and args[1]==("param",1),"DEX drawable original Record constructor")
                obj=allocations[args[0]];need(not obj["initialized"] and ref==[obj["type"][1:-1],"<init>","(L"+REC+";)V"],"DEX exact drawable constructor")
                obj["initialized"]=True;continue
            if ref==[M,"require","()V"]:
                need(op in (0x6e,0x74) and need_post and args==[("param",2)],"DEX original Mutation postcheck")
                postchecks.append(x);need_post=False;continue
            need(not need_post,"DEX missing immediate original Mutation postcheck")
            expected=SETTERS[len(calls)] if api==29 and len(calls)<4 else "setStateDescription" if api==30 else None
            need(op in (0x6e,0x74) and expected is not None and ref==([N,expected,DRAW] if api==29 else ["android/view/View",expected,STATE]),"DEX native call order/identity")
            need(len(args)==2 and args[0]==("param",0),"DEX original native receiver")
            if api==29:
                need(args[1] in allocations and args[1]==pending_allocation,"DEX next drawable identity/order");obj=allocations[args[1]]
                expected_type="L"+V+("$Cursor;" if len(calls)==0 else "$Handle;")
                need(obj["initialized"] and obj["type"]==expected_type and all(c["allocation_pc"]!=obj["pc"] for c in calls),"DEX distinct initialized drawable")
            else:need(args[1]==("param",1),"DEX original state value")
            calls.append({"instruction":x,"allocation_pc":obj["pc"] if api==29 else None})
            pending_allocation=None
            need_post=owner.startswith(V);continue
        if op==0x0e:
            need(not need_post and pending_allocation is None and x is m["instructions"][-1],"DEX helper return/postcheck")
            continue
        raise Refusal("DEX unreviewed helper instruction "+hex(op))
    need(len(calls)==(4 if api==29 else 1) and len(postchecks)==(4 if api==29 else 1 if owner.startswith(V) else 0),"DEX complete helper call/postcheck count")
    need(len(allocations)==(4 if api==29 else 0),"DEX unreviewed helper allocations")
    members={tuple(d.methods[i][1:]) for i in d.definitions if d.methods[i][0]==owner}
    need(members=={("<init>","()V"),(name,desc)},"DEX helper member topology")
    ctor_id=next(i for i in d.definitions if d.methods[i]==[owner,"<init>","()V"])
    ctor=d.code.get(ctor_id,{});ci=ctor.get("instructions",[])
    need(d.definitions[ctor_id]&2 and not d.definitions[ctor_id]&8 and ctor.get("ins")==1 and not ctor.get("handlers") and len(ci)==2 and ci[0]["op"] in (0x70,0x76) and ci[0].get("ref")==["java/lang/Object","<init>","()V"] and ci[0].get("registers")==[ctor["registers"]-1] and ci[1]["op"]==0x0e,"DEX inert private helper constructor")
    need(m["instructions"][-1]["op"]==0x0e,"DEX helper void return")
    return {"owner":owner,"entry":[name,desc],"api":api,"native_calls":calls,"postchecks":postchecks,"original_parameters_and_drawable_identity":True,"legacy_no_mutation_contract":owner==R+"$Api30"}


def _dex_parameter_aliases(m):
    """Must-alias dataflow for original this/Mutation across actual DEX CFG.

    Every destination of the admitted standard opcode set kills prior alias;
    object moves preserve aliases. At joins only equal aliases survive. Exception
    edges receive the preinstruction state, so a throwing assignment cannot invent
    a captured identity in a handler. No Java method is executed.
    """
    ins=m["instructions"];edges=_cfg(ins,(),True);by_pc={x["pc"]:x for x in ins}
    base=m["registers"]-m["ins"]
    need(m["ins"]==5,"DEX V2 bind exact input width")
    initial={base:"this",base+4:"mutation"};states={ins[0]["pc"]:initial};todo=[ins[0]["pc"]]
    def merge(pc,state):
        if pc not in states:states[pc]=dict(state);todo.append(pc);return
        joined={r:v for r,v in states[pc].items() if state.get(r)==v}
        if joined!=states[pc]:states[pc]=joined;todo.append(pc)
    while todo:
        pc=todo.pop();x=by_pc[pc];op=x["op"];w=x["words"];before=states[pc];after=dict(before)
        dest=None;wide=False
        if op in (1,4,7):dest=(w[0]>>8)&15;src=w[0]>>12
        elif op in (2,5,8):dest=w[0]>>8;src=w[1]
        elif op in (3,6,9):dest=w[1];src=w[2]
        else:src=None
        if op in (4,5,6):wide=True
        if op in (0x0a,0x0b,0x0c,0x0d,0x13,0x14,0x15,0x16,0x17,0x18,0x19,0x1a,0x1b,0x1c,0x22,*range(0x2d,0x32),*range(0x44,0x4b),*range(0x60,0x67),*range(0x90,0xb0),*range(0xd8,0xe3)):dest=w[0]>>8
        if op in (0x12,0x20,0x21,0x23,*range(0x52,0x59),*range(0x7b,0x90),*range(0xb0,0xd8)):dest=(w[0]>>8)&15
        if op in (0x0b,0x16,0x17,0x18,0x19,0x45,0x53,0x61,0x7d,0x7e,0x80,0x81,0x83,0x86,0x88,0x89,0x8b,*range(0x9b,0xa6),*range(0xab,0xb0),*range(0xbb,0xc6),*range(0xcb,0xd0)):wide=True
        if dest is not None:
            after.pop(dest,None)
            if wide:after.pop(dest+1,None)
            if op in (7,8,9) and src in before:after[dest]=before[src]
        for successor in edges[pc]:merge(successor,after)
        for a,b,h,_ in m["handlers"]:
            if a<=pc<b:merge(h,before)
    return states


def _dex_guard(d,index,target,api):
    m=d.code[index];ins=m["instructions"];edges=_cfg(ins,m["handlers"],True)
    calls=[x for x in ins if x.get("ref")==[target,*HELPERS[target][:2]] and x["op"] in (0x71,0x77)]
    need(len(calls)==1,"DEX exact guarded helper invocation")
    call=calls[0];proof=[]
    caller_identity=None
    if target.startswith(V):
        need(d.methods[index]==[REC,"bind","(L"+V+"$Binding;L"+V+"$Geometry;ZL"+M+";)V"],"DEX exact V2 bind descriptor")
        aliases=_dex_parameter_aliases(m).get(call["pc"],{})
        args=call["registers"]
        need(len(args)==3 and aliases.get(args[-1])=="mutation","DEX helper original caller Mutation argument")
        if api==29:need(aliases.get(args[1])=="this","DEX helper original caller Record argument")
        caller_identity={"must_alias_original_mutation":True,"mutation_argument_register":args[-1],"must_alias_original_record":api==29,"analysis":"all standard opcode destinations invalidate; object moves preserve; equal-alias CFG intersection including exception handlers"}
    for i,x in enumerate(ins[:-2]):
        if x["op"]!=0x60 or x.get("field")!=["android/os/Build$VERSION","SDK_INT","I"]:continue
        sdkreg=x["words"][0]>>8;const,branch=ins[i+1:i+3];op=const["op"];w=const["words"]
        if op==0x12:cr=(w[0]>>8)&15;value=w[0]>>12;value=value-16 if value&8 else value
        elif op==0x13:cr=w[0]>>8;value=w[1]-(65536 if w[1]&32768 else 0)
        elif op==0x14:cr=w[0]>>8;value=w[1]|w[2]<<16
        else:continue
        if value!=api or branch["op"] not in (0x34,0x35,0x36,0x37):continue
        if cr==sdkreg or not _guard_chain(edges,x,const,branch):continue
        a=(branch["words"][0]>>8)&15;b=branch["words"][0]>>12
        # if-lt sdk, threshold or equivalent if-gt threshold,sdk takes unsupported branch.
        low_branch=(branch["op"]==0x34 and (a,b)==(sdkreg,cr)) or (branch["op"]==0x36 and (a,b)==(cr,sdkreg))
        high_branch=(branch["op"]==0x35 and (a,b)==(sdkreg,cr)) or (branch["op"]==0x37 and (a,b)==(cr,sdkreg))
        if not (low_branch or high_branch):continue
        low=branch["targets"][0] if low_branch else ins[i+3]["pc"];high=ins[i+3]["pc"] if low_branch else branch["targets"][0]
        if call["pc"] not in _reachable(edges,high) or call["pc"] in _reachable(edges,low) or call["pc"] in _reachable(edges,ins[0]["pc"],branch["pc"]):continue
        proof.append({"sdk_read":x,"threshold":api,"constant":const,"branch":branch,"below_api_successor":low,"supported_successor":high,"call":call,"normal_and_exception_cfg_dominance":True})
    need(len(proof)==1,"DEX actual SDK_INT guard/dominance proof "+target)
    return {"caller":d.methods[index],"caller_original_identity":caller_identity,**proof[0]}


def _inspect_dex(dex_file):
    """Read exactly one DEX039; refuse unknown later-API helper/outlining shapes."""
    data=_bounded_file(dex_file,32*1024*1024);d=Dex(data)
    need(set(HELPERS)<=set(d.classes),"DEX exact three helper class definitions")
    product={n:c for n,c in d.classes.items() if n.startswith(P) and (c["source_file"] in SOURCES or any(n==P+s[:-5] or n.startswith(P+s[:-5]+"$") for s in SOURCES))}
    need(all(P+s[:-5] in product for s in SOURCES),"DEX sixteen product top-level groups")
    need(N in product and product[N]["parent"]=="android/widget/EditText","DEX actual NativeField superclass")
    helpers=[_dex_helper(d,n) for n in HELPERS]
    later_ids=[{"method_id":i,"reference":r} for i,r in enumerate(d.methods) if r[1] in LATER]
    need(all(x["reference"][2]==(DRAW if x["reference"][1] in SETTERS else STATE) for x in later_ids),"DEX later method descriptor")
    need(len(later_ids)==5,"DEX exact five global native method IDs")
    refs=[];calls=[]
    for idx,m in d.code.items():
        owner=d.methods[idx][0]
        for x in m["instructions"]:
            ref=x.get("ref")
            if ref and ref[1] in LATER:
                need(owner==V+"$Api29" if ref[1] in SETTERS else owner in (V+"$Api30",R+"$Api30"),"DEX later native invocation escaped helper/unreviewed outlining "+owner)
                refs.append({"caller":d.methods[idx],"instruction":x})
            if ref and ref[0] in HELPERS:
                need(owner in product,"DEX helper invocation from unreviewed synthetic/foreign owner")
                calls.append((idx,ref[0]))
    need(len(refs)==6 and len(calls)==3,"DEX exact native/helper invocation counts")
    expected={(REC,"bind",V+"$Api29"),(REC,"bind",V+"$Api30"),(R,"bind",R+"$Api30")}
    need({(d.methods[i][0],d.methods[i][1],target) for i,target in calls}==expected,"DEX actual helper caller topology")
    guards=[_dex_guard(d,i,target,HELPERS[target][2]) for i,target in calls]
    synthetics=[n for n in d.classes if "ExternalSynthetic" in n or "$$" in n]
    return {"schema_version":1,"kind":"dex","accepted":True,"scope":"DEX039 exact references, helper dataflow and guarded invocation proof","artifact":identity(data),"source_binding":{"freeze_sha256":FREEZE,"manifest_sha256":MANIFEST,"product_tree":TREE,"custody_verified_by_this_function":False},"structure":{"magic":"039","sha1_valid":True,"adler32_valid":True,"map":d.map,"class_count":len(d.classes),"code_bodies":len(d.code),"method_ids":len(d.methods)},"classes":d.classes,"helpers":helpers,"later_api_method_ids":later_ids,"later_api_invocations":refs,"guards":guards,"synthetic_classes_observed":synthetics,"synthetic_outlining_policy":"later native references outside exact helpers refused; unrelated D8 synthetics enumerated, not accepted as later-API substitutes","inherited_method_resolution":{"symbolic_owner":N,"observed_superclass":product[N]["parent"],"external_declaration_resolution":"pair with pinned platform_jar classfile evidence; no ART resolution claim"},"limitations":list(LIMITS)+["DEX <36 branches are not separately proven here; classfile comparisons and selected focused runtime tests must supply independent admission evidence."]}


def inspect_classes(classes_root, *, platform_jar=None):
    """Read-only classfile evidence, or a normalized Refusal for invalid input."""
    try:return _inspect_classes(classes_root,platform_jar=platform_jar)
    except Refusal:raise
    except (OSError,KeyError,IndexError,struct.error,zipfile.BadZipFile,UnicodeError,ValueError) as e:
        raise Refusal("class artifact decoding failed: "+type(e).__name__) from e


def inspect_dex(dex_file):
    """Read-only DEX evidence, or a normalized Refusal for invalid input."""
    try:return _inspect_dex(dex_file)
    except Refusal:raise
    except (OSError,KeyError,IndexError,struct.error,UnicodeError,ValueError) as e:
        raise Refusal("DEX artifact decoding failed: "+type(e).__name__) from e
