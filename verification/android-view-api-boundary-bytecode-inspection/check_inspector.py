"""Data-only controls. The bootstrap denies effects before importing the subject."""
import os
import sys
import subprocess
import signal
import socket
import time
import threading
import importlib.util
from pathlib import Path
import json
import hashlib
import struct
import zipfile
import zlib
import copy

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.dont_write_bytecode=True
DENIED=[]
def denied(*args,**kwargs):
    raise RuntimeError("process/session/group/signal/timer/wait/socket denied before subject import")
for module,names in [
    (os,"system popen fork forkpty posix_spawn posix_spawnp kill killpg wait waitpid waitid wait3 wait4 setsid setpgid getpgid getsid getpgrp execl execle execlp execlpe execv execve execvp execvpe spawnl spawnle spawnlp spawnlpe spawnv spawnve spawnvp spawnvpe"),
    (subprocess,"Popen run call check_call check_output getoutput getstatusoutput"),
    (socket,"socket socketpair create_connection create_server getaddrinfo"),
    (signal,"signal pthread_kill raise_signal alarm setitimer pause sigwait sigwaitinfo sigtimedwait"),
    (time,"sleep"),(threading,"Timer Thread")]:
    for name in names.split():
        if hasattr(module,name):setattr(module,name,denied);DENIED.append(module.__name__+"."+name)
def audit(event,args):
    if event.startswith(("subprocess.","socket.","os.exec","os.spawn","os.fork","os.kill","os.posix_spawn")):
        denied()
sys.addaudithook(audit)
spec=importlib.util.spec_from_file_location("view_api_inspector",HERE/"inspect_artifacts.py")
subject=importlib.util.module_from_spec(spec)
spec.loader.exec_module(subject)


class Builder:
    """Authored minimal classfile encoder; fixtures never loaded or executed."""
    def __init__(self):self.pool=[];self.cached={}
    def cp(self,tag,value):
        key=(tag,value)
        if key not in self.cached:self.pool.append(key);self.cached[key]=len(self.pool)
        return self.cached[key]
    def utf(self,value):return self.cp(1,value)
    def cls(self,value):return self.cp(7,self.utf(value))
    def ref(self,owner,name,desc,field=False):return self.cp(9 if field else 10,(self.cls(owner),self.cp(12,(self.utf(name),self.utf(desc)))))
    def op(self,op,ref):return bytes([op])+struct.pack(">H",ref)
    def file(self,owner,methods,parent="java/lang/Object",source=None):
        cname,superclass=self.cls(owner),self.cls(parent)
        code_attr=self.utf("Code");source_attr=self.utf("SourceFile")
        source_index=self.utf(source or owner.rsplit("/",1)[-1].split("$",1)[0]+".java")
        nested="$Api" in owner
        if nested:
            outer,inner=owner.rsplit("$",1);outer_index=self.cls(outer);inner_index=self.utf(inner)
            nest_attr=self.utf("NestHost");inner_attr=self.utf("InnerClasses")
        for name,desc,code,flags in methods:self.utf(name);self.utf(desc)
        out=b"\xca\xfe\xba\xbe"+struct.pack(">HHH",0,61,len(self.pool)+1)
        for tag,value in self.pool:
            out+=bytes([tag])
            if tag==1:raw=value.encode();out+=struct.pack(">H",len(raw))+raw
            elif tag==7:out+=struct.pack(">H",value)
            else:out+=struct.pack(">HH",*value)
        out+=struct.pack(">HHHHH",0x20,cname,superclass,0,0)+struct.pack(">H",len(methods))
        for name,desc,code,flags in methods:
            body=struct.pack(">HHI",16,16,len(code))+code+struct.pack(">HH",0,0)
            out+=struct.pack(">HHHHHI",flags,self.utf(name),self.utf(desc),1,code_attr,len(body))+body
        out+=struct.pack(">HHIH",3 if nested else 1,source_attr,2,source_index)
        if nested:
            out+=struct.pack(">HIH",nest_attr,2,outer_index)
            out+=struct.pack(">HIHHHHH",inner_attr,10,1,cname,outer_index,inner_index,0x1a)
        return out


def helper_binary(order=None,mutation_owner=None,record_slot=1,mutation_slot=2):
    s=subject;b=Builder();owner=s.V+"$Api29";code=b""
    for i,name in enumerate(order or s.SETTERS):
        drawable=s.V+("$Cursor" if i==0 else "$Handle")
        code+=b"\x2a"+b.op(0xbb,b.cls(drawable))+b"\x59"+bytes([0x2a+record_slot])+b.op(0xb7,b.ref(drawable,"<init>","(L"+s.REC+";)V"))
        code+=b.op(0xb6,b.ref(s.N,name,s.DRAW))+bytes([0x2a+mutation_slot])+b.op(0xb6,b.ref(mutation_owner or s.M,"require","()V"))
    code+=b"\xb1"
    init=b"\x2a"+b.op(0xb7,b.ref("java/lang/Object","<init>","()V"))+b"\xb1"
    return b.file(owner,[("<init>","()V",init,2),(s.HELPERS[owner][0],s.HELPERS[owner][1],code,8)])


def guard_binary(fake_sdk=False,bypass=False,threshold=29):
    s=subject;b=Builder();target=s.V+"$Api29"
    # [optional goto const] SDK read; bipush threshold; if_icmplt return;
    # aload field-local5; aload0; aload4; invokestatic; return.
    start=b"\xa7\x00\x06" if bypass else b""
    read=b.op(0xb2,b.ref("evil/Build" if fake_sdk else "android/os/Build$VERSION","SDK_INT","I",True))
    call=b.op(0xb8,b.ref(target,*s.HELPERS[target][:2]))
    code=start+read+bytes([0x10,threshold])+b"\xa1\x00\x0a"+b"\x19\x05\x2a\x19\x04"+call+b"\xb1"
    # branch PC is prefix+5; return PC prefix+16 => offset11
    code=code[:len(start)+6]+b"\x00\x0b"+code[len(start)+8:]
    return b.file(s.REC,[("bind","(L"+s.V+"$Binding;L"+s.V+"$Geometry;ZL"+s.M+";)V",code,0)])


def run():
    s=subject;results=[]
    def check(name,fn,refuse=False):
        try:fn()
        except s.Refusal as e:
            if not refuse:raise
            results.append({"name":name,"expected_refusal":True,"reason":str(e)})
        else:
            if refuse:raise AssertionError("control accepted: "+name)
            results.append({"name":name,"passed":True})
    good=helper_binary();owner=s.V+"$Api29"
    check("authored binary API29 helper exact object/Mutation sequence",lambda:s._class_helper(s.ClassFile(good),owner))
    check("binary changed setter order",lambda:s._class_helper(s.ClassFile(helper_binary(order=(s.SETTERS[1],s.SETTERS[0],*s.SETTERS[2:]))),owner),True)
    check("binary false Mutation require owner",lambda:s._class_helper(s.ClassFile(helper_binary(mutation_owner="evil/Mutation")),owner),True)
    check("binary wrong original Record parameter",lambda:s._class_helper(s.ClassFile(helper_binary(record_slot=0)),owner),True)
    check("binary wrong original Mutation parameter",lambda:s._class_helper(s.ClassFile(helper_binary(mutation_slot=1)),owner),True)
    for name,data in [("class truncated header",good[:9]),("class trailing garbage",good+b"x"),("class wrong magic",b"bad!"+good[4:]),("class truncated code",good[:-20])]:check(name,lambda data=data:s.ClassFile(data),True)
    key=("bind","(L"+s.V+"$Binding;L"+s.V+"$Geometry;ZL"+s.M+";)V")
    check("authored binary real SDK guard",lambda:s._class_guard(s.ClassFile(guard_binary()),key,owner,29))
    check("binary fake SDK owner",lambda:s._class_guard(s.ClassFile(guard_binary(fake_sdk=True)),key,owner,29),True)
    check("binary guard-chain jump-in",lambda:s._class_guard(s.ClassFile(guard_binary(bypass=True)),key,owner,29),True)
    check("binary changed threshold",lambda:s._class_guard(s.ClassFile(guard_binary(threshold=28)),key,owner,29),True)
    historical=ROOT/"verification/android-api28-collections-prerequisite/attempt-1/actual20.classes.dex"
    raw=historical.read_bytes();fixture=s.identity(raw);fixture["path"]=str(historical.relative_to(ROOT))
    check("retained historical DEX structural parse only",lambda:s.Dex(raw))
    for name,data in [("DEX truncated header",raw[:100]),("DEX wrong magic",b"bad!"+raw[4:]),("DEX truncated body",raw[:-1]),("DEX broken SHA1",raw[:12]+bytes([raw[12]^1])+raw[13:]),("DEX broken Adler",raw[:8]+bytes([raw[8]^1])+raw[9:])]:check(name,lambda data=data:s.Dex(data),True)
    def repair(data):
        out=bytearray(data);out[12:32]=hashlib.sha1(out[32:]).digest();out[8:12]=struct.pack("<I",zlib.adler32(out[12:])&0xffffffff);return bytes(out)
    bad=bytearray(raw);bad[36:40]=struct.pack("<I",113)
    check("DEX structurally invalid header with repaired checksums",lambda:s.Dex(repair(bad)),True)
    d=s.Dex(raw);bad=bytearray(raw);off=next(iter(d.code_offsets));bad[off+16:off+18]=b"\xff\x00"
    check("DEX reserved opcode with repaired checksums",lambda:s.Dex(repair(bad)),True)
    bad=bytearray(raw);map_at=d.u32(52);bad[map_at+4:map_at+6]=struct.pack("<H",7)
    check("DEX unreviewed call-site section with repaired checksums",lambda:s.Dex(repair(bad)),True)
    # Param identity data controls operate on hand-authored instruction records.
    m={"registers":7,"ins":5,"handlers":[],"instructions":[{"pc":0,"op":7,"words":[0x6107],"targets":[]},{"pc":1,"op":0x0e,"words":[0x000e],"targets":[]}]}
    check("DEX original Mutation move alias",lambda:s.need(s._dex_parameter_aliases(m)[1].get(1)=="mutation","alias not propagated"))
    corrupted=copy.deepcopy(m);corrupted["instructions"][0]={"pc":0,"op":0x13,"words":[0x0113,0],"targets":[]}
    check("DEX overwritten register has no original Mutation alias",lambda:s.need(1 not in s._dex_parameter_aliases(corrupted)[1],"overwritten alias survives"))
    class FakeDex:pass
    f=FakeDex();f.methods=[[owner,*s.HELPERS[owner][:2]],[owner,"<init>","()V"]];f.definitions={0:8,1:0x10002}
    body=[];pc=0
    for i,name in enumerate(s.SETTERS):
        temp=i%2;typ=s.V+("$Cursor" if i==0 else "$Handle")
        rows=[{"op":0x22,"words":[0x22|(temp<<8),0],"type":"L"+typ+";"},
              {"op":0x70,"words":[0,0,0],"registers":[temp,3],"ref":[typ,"<init>","(L"+s.REC+";)V"]},
              {"op":0x6e,"words":[0,0,0],"registers":[2,temp],"ref":[s.N,name,s.DRAW]},
              {"op":0x6e,"words":[0,0,0],"registers":[4],"ref":[s.M,"require","()V"]}]
        for row in rows:row.update(pc=pc,targets=[],payload=False);pc+=len(row["words"]);body.append(row)
    body.append({"pc":pc,"op":0x0e,"words":[0x0e],"targets":[],"payload":False})
    f.code={0:{"registers":5,"ins":3,"outs":2,"handlers":[],"instructions":body},1:{"registers":1,"ins":1,"outs":1,"handlers":[],"instructions":[{"pc":0,"op":0x70,"words":[0,0,0],"registers":[0],"ref":["java/lang/Object","<init>","()V"]},{"pc":3,"op":0x0e,"words":[0x0e]}]}}
    check("authored DEX helper dataflow exact constructor/setter/postcheck order",lambda:s._dex_helper(f,owner))
    hoisted=copy.deepcopy(f);old=hoisted.code[0]["instructions"];hoisted.code[0]["instructions"]=old[:2]+old[4:6]+old[2:4]+old[6:]
    check("DEX hoisted future drawable constructor refused",lambda:s._dex_helper(hoisted,owner),True)
    missing=copy.deepcopy(f);del missing.code[0]["instructions"][3]
    check("DEX missing immediate Mutation postcheck refused",lambda:s._dex_helper(missing,owner),True)
    kind=copy.deepcopy(f);kind.code[0]["instructions"][1]["op"]=0x6e
    check("DEX constructor invoke kind mismatch refused",lambda:s._dex_helper(kind,owner),True)
    for name,fn in [("process mock active",lambda:os.system("ignored")),("socket mock active",lambda:socket.socket()),("timer mock active",lambda:time.sleep(0)),("wait mock active",lambda:os.waitpid(0,0)),("signal mock active",lambda:signal.alarm(0))]:
        try:fn()
        except RuntimeError:results.append({"name":name,"denied":True})
        else:raise AssertionError(name)
    report={"schema":1,"status":"passed data-only preparation controls; no changed product artifact exists in this lane","command":["python3","-B",str(Path(__file__).relative_to(ROOT))],"python":{"executable":sys.executable,"version":sys.version,"executable_identity":s.identity(Path(sys.executable).read_bytes())},"source_context":"root supplied 5b6fc4f5 context only; no Git query","inspector":s.identity((HERE/"inspect_artifacts.py").read_bytes()),"denied_before_subject_import":DENIED,"controls":results,"control_count":len(results),"historical_fixture":fixture,"authored_fixtures":{"class_api29":s.identity(good),"class_guard":s.identity(guard_binary()),"provenance":"Builder in this file authors binary bytes; no javac/JVM or generated product fixture"},"limitations":s.LIMITS,"failures_preserved":"setup-and-failures.md"}
    (HERE/"controls.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"controls":len(results),"status":"passed","inspector_sha256":report["inspector"]["sha256"]}))


if __name__=="__main__":run()
