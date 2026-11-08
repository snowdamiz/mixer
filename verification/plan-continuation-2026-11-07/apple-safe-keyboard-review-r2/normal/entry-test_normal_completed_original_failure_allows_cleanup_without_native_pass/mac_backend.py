"""Public AX + exact simctl backend. Root-only future use; not run in this task."""
import ctypes as C
import dataclasses, importlib.util, json, os, sys, time, uuid
from pathlib import Path
from commands import Commands, write, digest
from controller import Owned, Window, require, HELD
from verify_bindings import verify, OLD, PACKET_SHA, HERE
DEV='/Applications/Xcode_26.6.app/Contents/Developer'
EXE=DEV+'/Applications/Simulator.app/Contents/MacOS/Simulator'
RUNTIME='com.apple.CoreSimulator.SimRuntime.iOS-26-5'
DEVICE='com.apple.CoreSimulator.SimDeviceType.iPhone-17-Pro'

class AX:
    def __init__(self):
        self.ax=C.CDLL('/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices')
        self.cf=C.CDLL('/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation')
        self.refs=[]
        signatures={
            'AXIsProcessTrustedWithOptions':([C.c_void_p],C.c_bool),
            'AXUIElementCreateApplication':([C.c_int],C.c_void_p),
            'AXUIElementCopyAttributeValue':([C.c_void_p,C.c_void_p,C.POINTER(C.c_void_p)],C.c_int),
            'AXUIElementPerformAction':([C.c_void_p,C.c_void_p],C.c_int),
            'AXUIElementSetMessagingTimeout':([C.c_void_p,C.c_float],C.c_int)}
        for name,(args,result) in signatures.items():
            f=getattr(self.ax,name); f.argtypes=args; f.restype=result
        signatures={
            'CFStringCreateWithCString':([C.c_void_p,C.c_char_p,C.c_uint32],C.c_void_p),
            'CFStringGetCString':([C.c_void_p,C.c_char_p,C.c_long,C.c_uint32],C.c_bool),
            'CFArrayGetCount':([C.c_void_p],C.c_long),
            'CFArrayGetValueAtIndex':([C.c_void_p,C.c_long],C.c_void_p),
            'CFBooleanGetValue':([C.c_void_p],C.c_bool),
            'CFGetTypeID':([C.c_void_p],C.c_ulong),
            'CFStringGetTypeID':([],C.c_ulong),'CFArrayGetTypeID':([],C.c_ulong),
            'CFBooleanGetTypeID':([],C.c_ulong),'CFRelease':([C.c_void_p],None)}
        for name,(args,result) in signatures.items():
            f=getattr(self.cf,name); f.argtypes=args; f.restype=result
    def trusted(self): return bool(self.ax.AXIsProcessTrustedWithOptions(None))
    def keep(self,ref):
        if ref: self.refs.append(ref)
        return ref
    def release(self):
        for ref in reversed(self.refs): self.cf.CFRelease(ref)
        self.refs=[]
    def string(self,text): return self.keep(self.cf.CFStringCreateWithCString(None,text.encode(),0x08000100))
    def app(self,pid):
        require(pid>1 and pid not in HELD,'Held PID refused')
        app=self.keep(self.ax.AXUIElementCreateApplication(pid))
        require(app and self.ax.AXUIElementSetMessagingTimeout(app,2.0)==0,'AX timeout setup failed')
        return app
    def attr(self,obj,name,optional=False):
        result=C.c_void_p(); code=self.ax.AXUIElementCopyAttributeValue(obj,self.string(name),C.byref(result))
        if optional and code in (-25205,-25212): return None
        require(code==0 and result.value is not None,'AX read failed '+name+': '+str(code))
        return self.keep(result.value)
    def text(self,obj,name,optional=False):
        ref=self.attr(obj,name,optional)
        if ref is None: return ''
        require(self.cf.CFGetTypeID(ref)==self.cf.CFStringGetTypeID(),'AX string required')
        buf=C.create_string_buffer(16384)
        require(self.cf.CFStringGetCString(ref,buf,len(buf),0x08000100),'AX string overflow')
        return buf.value.decode()
    def flag(self,obj,name):
        ref=self.attr(obj,name)
        require(self.cf.CFGetTypeID(ref)==self.cf.CFBooleanGetTypeID(),'AX boolean required')
        return bool(self.cf.CFBooleanGetValue(ref))
    def children(self,obj,name='AXChildren',optional=True):
        ref=self.attr(obj,name,optional)
        if ref is None:return []
        require(self.cf.CFGetTypeID(ref)==self.cf.CFArrayGetTypeID(),'AX array required')
        count=self.cf.CFArrayGetCount(ref); require(0<=count<=2000,'AX child bound')
        return [self.cf.CFArrayGetValueAtIndex(ref,i) for i in range(count)]
    def press(self,obj): require(self.ax.AXUIElementPerformAction(obj,self.string('AXPress'))==0,'AXPress failed')

class MacBackend:
    def __init__(self,folder):
        self.folder=Path(folder); self.c=Commands(self.folder/'commands'); self.ax=AX(); self.index=0
        self.owned=None; self.baseline_windows=None; self.baseline_frontends=None; self.unknown=False
    def assert_custody(self):
        require(not getattr(self, 'unknown', False) and not (getattr(self, 'c', None) and self.c.unresolved),
                'Unknown custody; no further probes, launches or cleanup')
    def record(self,path,value):
        try: write(path,value)
        except BaseException:
            self.unknown=True
            raise
    def native_dispatch(self,argv):
        self.assert_custody()
        self.index+=1
        return self.c.run('%03d-unchanged-native-dispatch'%self.index,argv,950,operation='native-dispatch')
    def command(self,label,argv,timeout=45):
        self.assert_custody()
        self.index+=1; return self.c.run('%03d-%s'%(self.index,label),argv,timeout)
    def ax_trusted(self):
        self.assert_custody()
        current=self.ax.trusted()
        # Keep the historical requesting route visible; no permission bypass by
        # switching interpreters. Both checks are public, nonprompting queries.
        original=json.loads(self.command('ax', ['/usr/bin/osascript','-l','JavaScript',str(HERE/'ax_probe.js')],30))
        return current is True and original['trusted'] is True
    def verify_bindings(self):
        self.assert_custody()
        result=verify()
        runtimes=json.loads(self.command('runtimes',['/usr/bin/xcrun','simctl','list','runtimes','--json']))
        matched=[r for r in runtimes['runtimes'] if r['identifier']==RUNTIME]
        require(len(matched)==1 and matched[0]['isAvailable'] and matched[0]['buildversion']=='23F77',
                'Exact available runtime build required before creation')
        return result
    def devices(self):
        self.assert_custody()
        raw=json.loads(self.command('devices',['/usr/bin/xcrun','simctl','list','devices','--json']))
        fields=['name','state','deviceTypeIdentifier','dataPath','logPath']
        return {r['udid']:{**{k:r.get(k) for k in fields},'runtime':rt,'deviceType':r['deviceTypeIdentifier']}
                for rt,rows in raw['devices'].items() for r in rows}
    def frontends(self):
        self.assert_custody()
        script="""ObjC.import('AppKit'); function run(args) { return JSON.stringify(ObjC.unwrap($.NSWorkspace.sharedWorkspace.runningApplications).filter(a=>ObjC.unwrap(a.bundleIdentifier)==='com.apple.iphonesimulator'||ObjC.unwrap(a.executableURL.path)===args[0]).map(a=>Number(a.processIdentifier))); }"""
        pids=json.loads(self.command('frontend-pids',['/usr/bin/osascript','-l','JavaScript','-e',script,EXE]))
        result={}
        for pid in sorted(pids):
            require(type(pid) is int and pid>1 and pid not in HELD,'Held/invalid frontend refused')
            row=self.command('frontend-identity',['/bin/ps','-p',str(pid),'-o','pid=,lstart=,comm=']).strip()
            require(row.endswith(EXE),'Unexpected frontend executable'); result[pid]=row
        return result
    def inventory(self):
        self.assert_custody()
        try:
            require(self.ax.trusted(),'AX permission absent')
            identities=self.frontends(); self.inventory_frontends=identities; rows=[]
            for pid,identity in identities.items():
                app=self.ax.app(pid)
                for window in self.ax.children(app,'AXWindows',False):
                    rows.append((pid,identity,self.ax.text(window,'AXIdentifier',True),self.ax.text(window,'AXTitle'),window))
            return rows
        except BaseException:
            self.unknown=True
            release=getattr(self.ax, "release", None)
            if release is not None: release()
            raise
    def verify_outside_windows(self):
        self.assert_custody()
        if self.baseline_windows is not None:
            self.windows_for_device(self.owned.uuid)
    def classify_windows(self,rows):
        keys=[tuple(row[:4]) for row in rows]
        require(len(keys)==len(set(keys)), 'Duplicate public window identity')
        require(all(pid>1 and pid not in HELD and identity and token and title
                    for pid,identity,token,title in keys), 'Public window identifier unavailable; retain custody')
        require(self.baseline_windows is not None and self.baseline_frontends is not None,
                'Complete pre-open inventory unavailable')
        before=set(self.baseline_windows); now=set(keys)
        require(before<=now, 'Outside window changed/disappeared; retain custody')
        current=self.inventory_frontends
        require(all(current.get(pid)==identity for pid,identity in self.baseline_frontends.items()),
                'Outside frontend changed/disappeared; retain custody')
        added=now-before
        require(len(added)<=1, 'Unclassified new windows; retain custody')
        found=[]
        for pid,identity,token,title in added:
            window=Window(pid,identity,token,title,self.owned.uuid)
            if self.owned.window is not None:
                require(window==self.owned.window, 'Exact window identity changed; retain custody')
            else:
                name=self.owned.name
                require(title==name or title.startswith(name+' – ') or title.startswith(name+' - '),
                        'Unclassified new window; retain custody')
            found.append(window)
        allowed=dict(self.baseline_frontends)
        if self.owned.window:
            allowed[self.owned.window.pid]=self.owned.window.process_identity
        for w in found: allowed[w.pid]=w.process_identity
        require(all(allowed.get(pid)==identity for pid,identity in current.items()),
                'Unclassified frontend; retain custody')
        return found
    def windows_for_device(self,uid):
        self.assert_custody()
        require(self.owned is not None and self.owned.uuid==uid,'Unowned UUID query refused')
        try:
            return self.classify_windows(self.inventory())
        except BaseException:
            self.unknown=True
            raise
        finally: self.ax.release()
    def capture_window_baseline(self):
        self.assert_custody()
        try:
            rows=self.inventory()
            keys=[tuple(row[:4]) for row in rows]
            require(len(keys)==len(set(keys)) and all(pid not in HELD and pid>1 and identity and token and title
                    for pid,identity,token,title in keys), 'Unclassified baseline window')
            require(not any(title==self.owned.name or title.startswith(self.owned.name+' – ') or
                            title.startswith(self.owned.name+' - ') for _,_,_,title in keys), 'Owned window already exists')
            self.baseline_windows=keys; self.baseline_frontends=dict(self.inventory_frontends)
            self.record(self.folder/'window-baseline.json',dict(windows=keys,frontends=self.baseline_frontends))
        except BaseException:
            self.unknown=True
            raise
        finally: self.ax.release()
    def create_owned(self):
        self.assert_custody()
        run=str(uuid.uuid4()); name='MixerFocusReferenceV9-'+run
        self.record(self.folder/'creation-intent.json',dict(runID=run,name=name,runtime=RUNTIME,deviceType=DEVICE))
        uid=self.command('create',['/usr/bin/xcrun','simctl','create',name,DEVICE,RUNTIME]).strip()
        require(str(uuid.UUID(uid)).upper()==uid,'Invalid new UUID')
        self.owned=Owned(uid,name,RUNTIME,DEVICE,None)
        self.record(self.folder/'owned-device.json',dataclasses.asdict(self.owned)); return self.owned
    def boot(self,uid):
        self.assert_custody()
        require(self.owned and self.owned.uuid==uid,'Unowned UUID')
        self.command('boot',['/usr/bin/xcrun','simctl','boot',uid])
        self.command('bootstatus',['/usr/bin/xcrun','simctl','bootstatus',uid,'-b'],120)
    def open_owned_window(self,owned):
        self.assert_custody()
        require(self.owned==owned,'Owned record mismatch')
        self.capture_window_baseline()
        try:
            self.command('open-owned-window',['/usr/bin/open','-a',DEV+'/Applications/Simulator.app','--args','-CurrentDeviceUDID',owned.uuid])
        except BaseException:
            self.unknown=True
            raise
        # Finite discovery; a missing/ambiguous public identity is a custody hold.
        for _ in range(5):
            matches=self.windows_for_device(owned.uuid)
            if len(matches)==1:
                self.owned=dataclasses.replace(owned,window=matches[0])
                self.record(self.folder/'owned-window.json',dataclasses.asdict(self.owned)); return self.owned
            require(len(matches)==0,'Ambiguous new windows'); time.sleep(0.2)
        self.unknown=True
        raise RuntimeError('Owned window identity unavailable; never quit frontend')
    def exact_element(self,expected):
        self.assert_custody()
        require(self.owned and self.owned.uuid==expected.device_uuid,'Unowned window')
        rows=self.inventory()
        try:
            require(self.classify_windows(rows)==[expected], "Exact window identity unavailable")
        except BaseException:
            self.unknown=True
            raise
        matches=[element for pid,identity,token,title,element in rows
                 if (pid,identity,token,title)==(expected.pid,expected.process_identity,expected.identifier,expected.title)]
        require(len(matches)==1 and bool(expected.identifier),'Exact window identity unavailable')
        return matches[0]
    def close_window(self,expected):
        self.assert_custody()
        try:
            window=self.exact_element(expected)
            require(self.ax.text(window,'AXRole')=='AXWindow','Not a public window')
            close=self.ax.attr(window,'AXCloseButton')
            require(self.ax.flag(close,'AXEnabled'),'Close button disabled')
            self.ax.press(close)
        finally: self.ax.release()
        self.record(self.folder/'window-close-request.json',dict(window=dataclasses.asdict(expected),action='AXPress AXCloseButton',frontendQuit=False))
    def keyboard_connected(self,expected):
        self.assert_custody()
        try:
            window=self.exact_element(expected)
            require(self.ax.flag(window,'AXMain'),'Owned window is not the menu target')
            app=self.ax.app(expected.pid); bar=self.ax.attr(app,'AXMenuBar')
            stack=[(bar,0)]; matches=[]; count=0
            while stack:
                obj,depth=stack.pop(); count+=1
                require(count<=2000 and depth<=10,'Menu traversal bound exceeded')
                title=self.ax.text(obj,'AXTitle',True)
                if title=='Connect Hardware Keyboard': matches.append(obj)
                for child in self.ax.children(obj): stack.append((child,depth+1))
            require(len(matches)==1,'Unique public keyboard menu item required')
            item=matches[0]; mark=self.ax.text(item,'AXMenuItemMarkChar',True)
            connected=self.ax.flag(item,'AXEnabled') and mark=='✓'
            self.record(self.folder/('keyboard-observation-%03d.json'%self.index),dict(window=dataclasses.asdict(expected),mark=mark,connected=connected,menuMutation=False))
            return connected
        finally:self.ax.release()
    def shutdown(self,uid):
        self.assert_custody()
        require(self.owned and self.owned.uuid==uid,'Unowned UUID')
        self.command('shutdown-owned',['/usr/bin/xcrun','simctl','shutdown',uid])
    def delete(self,uid):
        self.assert_custody()
        require(self.owned and self.owned.uuid==uid,'Unowned UUID')
        self.command('delete-owned',['/usr/bin/xcrun','simctl','delete',uid])
    def dispatch_unchanged(self,owned,baseline):
        self.assert_custody()
        # This is the sole handoff to accepted source: no patched module globals,
        # no argv/oracle/timeout rewrite, and no retry of an old run ID.
        old=json.loads((OLD/'root-selection.json').read_text())
        raw=json.loads(self.command('inner-baseline',['/usr/bin/xcrun','simctl','list','devices','--json']))
        for rt in raw['devices']:
            raw['devices'][rt]=[r for r in raw['devices'][rt] if r['udid']!=owned.uuid]
        root={**old,'runID':json.loads((self.folder/'creation-intent.json').read_text())['runID'],
              'ownedSimulatorIdentity':dict(udid=owned.uuid,name=owned.name,runtime=RUNTIME,build='23F77'),
              'baselineDevices':raw,'baselineFrontends':list(self.frontends().values())}
        import datetime
        root['selectedAtUTC']=datetime.datetime.now(datetime.timezone.utc).isoformat()
        self.record(self.folder/'root-selection.json',root)
        path=self.folder/'root-selection.json'; selected_sha=digest(path.read_bytes())
        self.record(self.folder/'dispatch-intent.json',dict(packetSHA256=PACKET_SHA,selectionSHA256=selected_sha,dispatcher=str(OLD/'dispatch_successor.py'),maximumNativeAttempts=1))
        # Native dispatch must be invoked in its own observed command by root.
        argv=[sys.executable,'-B',str(HERE/'dispatch_once.py'),str(path),selected_sha]
        return dict(argv=argv,packetSHA256=PACKET_SHA,selectionSHA256=selected_sha,
                    nativeStarted=False,gate='root bounded supervisor must execute exactly once; retain frontend until completion')
