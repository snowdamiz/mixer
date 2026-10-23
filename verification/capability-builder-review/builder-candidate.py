#!/usr/bin/env python3
"""Build one frozen experimental static archive; never use a Cargo library search path.

This is a local developer builder, not release authorization or a reproducible-
binary attestation. Output must be new. Source comes only from committed regular
Git blobs. Existing output is never deleted, reused, or overwritten.
"""
import argparse
import collections
import contextlib
import datetime
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import selectors
import shutil
import signal
import stat
import subprocess
import sys
import tarfile
import time
try:
    import tomllib
except ModuleNotFoundError:
    sys.exit("experimental VM builder requires Python 3.11 or newer")

ROOT=Path(__file__).resolve().parents[1]
FEATURE='experimental-capability-native'
HEADER_HASHES={
    'vm/include/mixer_vm.h':'18c2498d0d1deae2c998ef9f4b3f811b2184c45e8169610012b05e99342385fd',
    'vm/include/mixer_vm_capability.h':'9213c34ebf0f14d14f3319172e83647f704f3a02a60d413b4de990884357b4a6',
}
PATHS=['vm/Cargo.toml','vm/Cargo.lock','vm/build.rs','vm/src','vm/include','vm/profiles','vm/tests','vm/tools',
    'contracts/vm-profile-v1.json','contracts/vm-session-v1.json','contracts/guest-capability-transport-v1.json',
    'capabilities/schema/v1.json','capabilities/schema/hashes.json','runtime/Sources/CMixerVM/include/mixer_vm.h']
REQUIRED=['vm/Cargo.toml','vm/Cargo.lock','vm/src/lib.rs',*HEADER_HASHES,
    'contracts/vm-profile-v1.json','contracts/vm-session-v1.json','contracts/guest-capability-transport-v1.json',
    'capabilities/schema/v1.json','capabilities/schema/hashes.json','runtime/Sources/CMixerVM/include/mixer_vm.h']
LIBRARY='libmixer_vm_capability_experimental.a'
MAX_FILES=8192
MAX_FILE_BYTES=8*1024*1024
MAX_SOURCE_BYTES=64*1024*1024
MAX_ARCHIVE_BYTES=512*1024*1024
DIRECTORY=os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC
REGULAR=os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC|os.O_NONBLOCK

class BuildError(Exception):pass
class ProcessGroupError(BuildError):pass
def digest(raw):return hashlib.sha256(raw).hexdigest()
def relative(name):
    path=PurePosixPath(name)
    if path.is_absolute() or not path.parts or any(p in ('.','..','.git') for p in path.parts) or '\x00' in name:
        raise BuildError('unsafe relative source path')
    return path.parts
def absolute(path):
    path=Path(path)
    if not path.is_absolute() or path.anchor!='/' or '..' in path.parts:
        raise BuildError('output/cache paths must be absolute without parent traversal')
    if len(path.parts)<2:raise BuildError('filesystem root is not an output/cache')
    return path

def stop_group(child):
    """Kill/reap the direct child, then observe the private group disappearing."""
    with contextlib.suppress(ProcessLookupError):os.killpg(child.pid,signal.SIGKILL)
    child.wait()
    deadline=time.monotonic()+3
    while True:
        try:os.killpg(child.pid,0)
        except ProcessLookupError:return True
        except PermissionError:return False # exit cannot be established; quarantine, never assume dead
        if time.monotonic()>=deadline:return False
        time.sleep(0.01)

def capture(argv,*,cwd,env=None,maximum=2*1024*1024,timeout=300):
    """Bound output/time in a private session. Failed commands kill the group.

    This contains ordinary compiler descendants, not hostile tools that escape
    their session. A surviving group produces a distinct cache-quarantine error.
    """
    child=subprocess.Popen(argv,cwd=cwd,env=env,stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,start_new_session=True)
    data=bytearray();failure=None;deadline=time.monotonic()+timeout
    try:
        with selectors.DefaultSelector() as selected:
            selected.register(child.stdout,selectors.EVENT_READ)
            while selected.get_map():
                remaining=deadline-time.monotonic()
                if remaining<=0:failure='command timeout';break
                for key,_ in selected.select(min(remaining,1)):
                    block=os.read(key.fd,min(65536,maximum+1-len(data)))
                    if not block:selected.unregister(key.fileobj);continue
                    data.extend(block)
                    if len(data)>maximum:failure='command output limit';break
                if failure:break
        if not failure:
            try:child.wait(timeout=max(0.001,deadline-time.monotonic()))
            except subprocess.TimeoutExpired:failure='command timeout'
        if not failure and child.returncode==0:
            try:os.killpg(child.pid,0)
            except ProcessLookupError:pass
            else:failure='command left running descendants'
        if failure or child.returncode:
            if not stop_group(child):failure=(failure or 'command failed')+'; process group still present'
    except BaseException as error:
        try:stopped=stop_group(child)
        except BaseException as cleanup_error:
            raise ProcessGroupError('exceptional command cleanup could not establish group exit') from cleanup_error
        if not stopped:raise ProcessGroupError('exceptional command cleanup left process group present') from error
        raise
    finally:child.stdout.close()
    return child.returncode,bytes(data[:maximum]),failure

def rust_selector(requested):
    if requested is not None:
        selected=Path(requested)
        if not selected.is_absolute():raise BuildError('--rustc must be an absolute executable path')
    else:
        found=shutil.which('rustc')
        if found is None:raise BuildError('rustc is not on PATH; pass --rustc /absolute/path/to/rustc')
        selected=Path(found).absolute()
    if not selected.is_file() or not os.access(selected,os.X_OK):raise BuildError('rustc selector is not executable')
    return selected

def tool_identity(path):
    path=Path(path)
    resolved=path.resolve(strict=True)
    if not resolved.is_file():raise BuildError('tool is not a regular file')
    checksum=hashlib.sha256()
    with resolved.open('rb') as stream:
        while block:=stream.read(1024*1024):checksum.update(block)
    return {'path':str(path),'resolved_path':str(resolved),'sha256':checksum.hexdigest()}

def git(*args,maximum=2*1024*1024):
    code,raw,failure=capture(['git','--no-replace-objects',*args],cwd=ROOT,maximum=maximum)
    if code or failure:raise BuildError('frozen Git read failed: '+(failure or raw[:512].decode(errors='replace')))
    return raw

def frozen_inputs(revision):
    if not re.fullmatch('[0-9a-f]{40}',revision):raise BuildError('--revision requires a complete lowercase40hex commit, not a branch/tag')
    if git('cat-file','-t',revision).strip()!=b'commit':raise BuildError('revision is not a commit object')
    listing=git('ls-tree','-r','-z',revision,'--',*PATHS)
    files={};total=0
    for row in listing.split(b'\0'):
        if not row:continue
        try:metadata,name=row.split(b'\t',1);mode,kind,oid=metadata.split();name=name.decode('utf-8')
        except (ValueError,UnicodeError) as error:raise BuildError('invalid Git entry') from error
        relative(name)
        if kind!=b'blob' or mode not in (b'100644',b'100755'):raise BuildError('source entry is not a regular file: '+name)
        if name in files or len(files)>=MAX_FILES:raise BuildError('duplicate/too many source files')
        size=int(git('cat-file','-s',oid.decode()).strip())
        if size>MAX_FILE_BYTES or total+size>MAX_SOURCE_BYTES:raise BuildError('source byte limit exceeded')
        raw=git('cat-file','blob',oid.decode(),maximum=MAX_FILE_BYTES)
        if len(raw)!=size:raise BuildError('Git object size changed')
        files[name]={'bytes':raw,'mode':0o755 if mode==b'100755' else 0o644,'git_blob':oid.decode()};total+=size
    if any(p not in files for p in REQUIRED):raise BuildError('required frozen feature/header/contract input is missing')
    for path,expected in HEADER_HASHES.items():
        if digest(files[path]['bytes'])!=expected:raise BuildError('reviewed header mismatch: '+path)
    if files['vm/include/mixer_vm.h']['bytes']!=files['runtime/Sources/CMixerVM/include/mixer_vm.h']['bytes']:
        raise BuildError('frozen legacy header copies differ')
    try:manifest=tomllib.loads(files['vm/Cargo.toml']['bytes'].decode())
    except (ValueError,UnicodeError) as error:raise BuildError('invalid frozen Cargo manifest') from error
    features=manifest.get('features',{})
    if features.get(FEATURE)!=['experimental-capability-guest'] or features.get('experimental-capability-guest')!=['experimental-capability-mailbox'] or features.get('default')!=[]:
        raise BuildError('explicit native feature chain/defaults mismatch')
    if 'staticlib' not in manifest.get('lib',{}).get('crate-type',[]):raise BuildError('static library target missing')
    if manifest.get('lib',{}).get('path') not in (None,'src/lib.rs'):raise BuildError('external or alternate library source is unsupported')
    if any(manifest.get(k) for k in ('dependencies','dev-dependencies','build-dependencies','workspace','patch','replace')):
        raise BuildError('export is not a dependency-free self-contained VM package')
    if any(value.get(k) for value in manifest.get('target',{}).values() for k in ('dependencies','dev-dependencies','build-dependencies')):
        raise BuildError('target dependencies are outside this builder contract')
    if manifest.get('package',{}).get('build') not in (None,False) or 'vm/build.rs' in files:
        raise BuildError('build scripts are outside this builder contract')
    contract=files['contracts/guest-capability-transport-v1.json']['bytes']
    if digest(contract)!='052ebe9fbdc20a41307332086767e7903680bc83ba273c696edf9187be6b6439':
        raise BuildError('reviewed transport contract mismatch')
    return files

def opened_directory(path,*,create=False):
    path=absolute(path);fd=os.open('/',DIRECTORY)
    try:
        for part in path.parts[1:]:
            if create:
                try:os.mkdir(part,0o700,dir_fd=fd)
                except FileExistsError:pass
            child=os.open(part,DIRECTORY,dir_fd=fd);os.close(fd);fd=child
        return fd
    except BaseException:os.close(fd);raise

class Output:
    def __init__(self,path):
        self.path=absolute(path);parent=opened_directory(self.path.parent,create=True)
        try:os.mkdir(self.path.name,0o700,dir_fd=parent);self.fd=os.open(self.path.name,DIRECTORY,dir_fd=parent)
        finally:os.close(parent)
        self.identity=os.fstat(self.fd)
    def check(self):
        fd=opened_directory(self.path)
        try:
            now=os.fstat(fd)
            if (now.st_dev,now.st_ino)!=(self.identity.st_dev,self.identity.st_ino):raise BuildError('output directory identity changed')
        finally:os.close(fd)
    def parent(self,name):
        parts=relative(name);fd=os.dup(self.fd)
        try:
            for part in parts[:-1]:
                try:os.mkdir(part,0o700,dir_fd=fd)
                except FileExistsError:pass
                child=os.open(part,DIRECTORY,dir_fd=fd);os.close(fd);fd=child
            return fd,parts[-1]
        except BaseException:os.close(fd);raise
    def new(self,name,mode=0o600):
        parent,leaf=self.parent(name)
        try:return os.open(leaf,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,mode,dir_fd=parent)
        finally:os.close(parent)
    def write(self,name,data,mode=0o600):
        fd=self.new(name,mode)
        with os.fdopen(fd,'wb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
    def read(self,name,maximum=MAX_SOURCE_BYTES):
        parent,leaf=self.parent(name)
        try:fd=os.open(leaf,REGULAR,dir_fd=parent)
        finally:os.close(parent)
        with os.fdopen(fd,'rb') as stream:
            info=os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1 or info.st_size>maximum:raise BuildError('unsafe exported file')
            raw=stream.read(maximum+1)
            if len(raw)!=info.st_size:raise BuildError('exported file size changed')
            return raw
    def mkdir(self,name):
        parent,leaf=self.parent(name)
        try:os.mkdir(leaf,0o700,dir_fd=parent)
        finally:os.close(parent)
    def close(self):os.close(self.fd)

def audit_cache(fd):
    """Reject symlinks/special files and links outside the selected cache.

    Cargo legitimately hardlinks incremental objects within its cache. Counting
    every inode reference allows those, without accepting an outside alias.
    """
    counts=collections.Counter();links={};seen=0
    def visit(directory,depth):
        nonlocal seen
        if depth>64:raise BuildError('cache nesting limit')
        with os.scandir(directory) as entries:
            for entry in entries:
                seen+=1
                if seen>200000:raise BuildError('cache entry limit')
                info=entry.stat(follow_symlinks=False)
                if info.st_uid!=os.getuid() or info.st_mode&0o022:raise BuildError('cache entry ownership/mode is unsafe')
                if stat.S_ISDIR(info.st_mode):
                    child=os.open(entry.name,DIRECTORY,dir_fd=directory)
                    try:
                        actual=os.fstat(child)
                        if (actual.st_dev,actual.st_ino)!=(info.st_dev,info.st_ino):raise BuildError('cache directory changed')
                        visit(child,depth+1)
                    finally:os.close(child)
                elif stat.S_ISREG(info.st_mode):
                    key=(info.st_dev,info.st_ino);counts[key]+=1;links[key]=info.st_nlink
                else:raise BuildError('cache has a symlink or special file')
    visit(fd,0)
    if any(counts[key]!=count for key,count in links.items()):raise BuildError('cache has an external hardlink')
    return {'entries':seen,'regular_inodes':len(counts),'internal_hardlinks_permitted':True}

@contextlib.contextmanager
def cache_owner(path):
    fd=opened_directory(path,create=True);lock=None
    try:
        info=os.fstat(fd)
        if info.st_uid!=os.getuid() or info.st_mode&0o022:raise BuildError('cache directory ownership/mode is unsafe')
        audit_cache(fd)
        lock=os.open('.mixer-capability-builder.lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=fd)
        if not stat.S_ISREG(os.fstat(lock).st_mode) or os.fstat(lock).st_nlink!=1:raise BuildError('cache lock is unsafe')
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as error:raise BuildError('cache is already used by another builder') from error
        try:os.stat('.mixer-capability-builder-quarantine',dir_fd=fd,follow_symlinks=False)
        except FileNotFoundError:pass
        else:raise BuildError('cache was quarantined after incomplete command cleanup')
        try:yield fd
        except BaseException as error:
            if not isinstance(error,(ProcessGroupError,KeyboardInterrupt,SystemExit)):raise
            marker=os.open('.mixer-capability-builder-quarantine',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=fd)
            with os.fdopen(marker,'wb') as stream:stream.write(b'Interrupted command or incomplete group cleanup; do not reuse this cache.\n');stream.flush();os.fsync(stream.fileno())
            raise
    finally:
        if lock is not None:os.close(lock)
        os.close(fd)

def source_archive(output,files):
    fd=output.new('source.tar')
    with os.fdopen(fd,'wb') as stream:
        with tarfile.open(fileobj=stream,mode='w',format=tarfile.PAX_FORMAT) as archive:
            for name,item in sorted(files.items()):
                info=tarfile.TarInfo(name);info.size=len(item['bytes']);info.mode=item['mode'];info.mtime=0
                archive.addfile(info,io.BytesIO(item['bytes']))
        stream.flush();os.fsync(stream.fileno())

def copy_library(output,cache_fd,parts):
    fd=os.dup(cache_fd)
    try:
        for part in parts[:-1]:child=os.open(part,DIRECTORY,dir_fd=fd);os.close(fd);fd=child
        library=os.open(parts[-1],REGULAR,dir_fd=fd)
    finally:os.close(fd)
    try:destination=output.new('lib/'+LIBRARY)
    except BaseException:os.close(library);raise
    checksum=hashlib.sha256();size=0
    with os.fdopen(library,'rb') as source,os.fdopen(destination,'wb') as staged:
        before=os.fstat(source.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1 or before.st_size>MAX_ARCHIVE_BYTES:raise BuildError('unsafe Cargo archive')
        magic=source.read(8)
        if magic!=b'!<arch>\n':raise BuildError('Cargo output is not a static archive')
        source.seek(0)
        while True:
            chunk=source.read(1024*1024)
            if not chunk:break
            size+=len(chunk)
            if size>MAX_ARCHIVE_BYTES:raise BuildError('archive byte limit')
            staged.write(chunk);checksum.update(chunk)
        after=os.fstat(source.fileno())
        fields=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_nlink)
        if fields(before)!=fields(after) or size!=before.st_size:raise BuildError('Cargo archive changed while copying')
        staged.flush();os.fsync(staged.fileno())
    return {'sha256':checksum.hexdigest(),'bytes':size,'path':str(output.path/'lib'/LIBRARY)}

def build(args):
    files=frozen_inputs(args.revision) # feature/header rejection before any output/cache/staging
    selector=rust_selector(args.rustc)
    out_path=absolute(args.output)
    if args.cache:
        cache=absolute(args.cache)
        if cache==out_path or cache in out_path.parents or out_path in cache.parents:raise BuildError('explicit cache/output paths overlap')
    else:cache=out_path/'cargo-target'
    output=Output(out_path);receipt={'schema_version':1,'source_revision':args.revision,'feature':FEATURE,'features':['experimental-capability-mailbox','experimental-capability-guest',FEATURE],
        'target_selector':args.target,'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'commands':[],
        'qualification':'local frozen-source development artifact; no release/identity/signing/device/bit-reproducibility claim',
        'builder_sha256':digest(Path(__file__).read_bytes()),'mutable_SDK_source_consumed':False}
    try:
        source_manifest=''.join(f'{digest(item["bytes"])}  {name}\n' for name,item in sorted(files.items()))
        receipt['source_manifest_sha256']=digest(source_manifest.encode());receipt['source_file_count']=len(files)
        receipt['source_blobs']={name:{'sha256':digest(item['bytes']),'git_blob':item['git_blob'],'bytes':len(item['bytes'])} for name,item in sorted(files.items())}
        output.write('source-manifest.sha256',source_manifest.encode())
        for name,item in sorted(files.items()):output.write('source/'+name,item['bytes'],item['mode'])
        source_archive(output,files);receipt['source_archive_sha256']=digest(output.read('source.tar'))
        output.mkdir('cargo-home');output.mkdir('tmp')
        env={'HOME':os.environ['HOME'],'PATH':str(selector.parent)+':/usr/bin:/bin:/usr/sbin:/sbin',
            'CARGO_HOME':str(out_path/'cargo-home'),'CARGO_TARGET_DIR':str(cache),'TMPDIR':str(out_path/'tmp'),'LANG':'C','LC_ALL':'C'}
        if os.environ.get('RUSTUP_HOME'):env['RUSTUP_HOME']=os.environ['RUSTUP_HOME']
        if os.environ.get('DEVELOPER_DIR'):env['DEVELOPER_DIR']=os.environ['DEVELOPER_DIR']
        def run(name,argv):
            began=time.monotonic();code,raw,problem=capture(argv,cwd='/',env=env)
            output.write(name+'.log',raw)
            receipt['commands'].append({'name':name,'argv':argv,'cwd':'/','exit_code':code,'problem':problem,
                'elapsed_host_development_seconds':round(time.monotonic()-began,6),'log':name+'.log','sha256':digest(raw)})
            if problem and 'process group still present' in problem:raise ProcessGroupError(name+' failed cleanup; see '+str(out_path/(name+'.log')))
            if code or problem:raise BuildError(name+' failed; see '+str(out_path/(name+'.log')))
            return raw.decode().strip()
        receipt['tools']={'rustc_selector':tool_identity(selector)}
        sysroot=Path(run('rust-sysroot',[str(selector),'--print','sysroot']))
        if not sysroot.is_absolute():raise BuildError('Rust sysroot must be absolute')
        cargo=sysroot/'bin/cargo';rustc=sysroot/'bin/rustc';env['RUSTC']=str(rustc);env['PATH']=str(sysroot/'bin')+':/usr/bin:/bin:/usr/sbin:/sbin'
        receipt['tools'].update({'cargo':tool_identity(cargo),'rustc':tool_identity(rustc)})
        receipt['rustc']=run('rustc-version',[str(rustc),'-Vv']);receipt['cargo']=run('cargo-version',[str(cargo),'-V'])
        if Path('/.cargo/config').exists() or Path('/.cargo/config.toml').exists():raise BuildError('root Cargo configuration is unsupported')
        target={'host':None,'ios':'aarch64-apple-ios','ios-simulator':'aarch64-apple-ios-sim','android':'aarch64-linux-android'}[args.target]
        rust_host=next(line[6:] for line in receipt['rustc'].splitlines() if line.startswith('host: '))
        receipt['rust_target']=target or rust_host
        nm=sysroot/'lib/rustlib'/rust_host/'bin/llvm-nm'
        if not nm.is_file():raise BuildError('matching Rust llvm-tools component required (llvm-nm missing)')
        receipt['tools']['llvm_nm']=tool_identity(nm);receipt['llvm_nm']=run('llvm-nm-version',[str(nm),'--version'])
        if args.target in ('ios','ios-simulator'):
            env['IPHONEOS_DEPLOYMENT_TARGET']='17.0';sdk='iphoneos' if args.target=='ios' else 'iphonesimulator'
            env['SDKROOT']=run('apple-sdk',['xcrun','--sdk',sdk,'--show-sdk-path'])
        elif args.target=='host' and rust_host.endswith('apple-darwin'):
            env['MACOSX_DEPLOYMENT_TARGET']='14.0';env['SDKROOT']=run('apple-sdk',['xcrun','--sdk','macosx','--show-sdk-path'])
        if args.target=='android':
            if args.ndk is None:raise BuildError('--ndk is required for Android')
            ndk=args.ndk.resolve();linker=ndk/'toolchains/llvm/prebuilt/darwin-x86_64/bin/aarch64-linux-android28-clang'
            env['CARGO_TARGET_AARCH64_LINUX_ANDROID_LINKER']=str(linker);env['RUSTFLAGS']='-C link-arg=-Wl,-z,max-page-size=16384'
            receipt['linker']=run('android-linker-version',[str(linker),'--version']);receipt['tools']['linker']=tool_identity(linker)
        elif args.target!='host' or rust_host.endswith('apple-darwin'):
            linker=Path(run('apple-clang-path',['xcrun','--find','clang']))
            receipt['linker']=run('apple-linker-version',[str(linker),'--version']);receipt['tools']['linker']=tool_identity(linker)
        else:
            linker=Path(shutil.which('cc',path=env['PATH']) or '/usr/bin/cc')
            receipt['linker']=run('host-linker-version',[str(linker),'--version']);receipt['tools']['linker']=tool_identity(linker)
        receipt['environment']=env.copy();receipt['cache_path']=str(cache)
        with cache_owner(cache) as cache_fd:
            receipt['cache_preflight']=audit_cache(cache_fd);output.check()
            for name,item in files.items():
                if output.read('source/'+name)!=item['bytes']:raise BuildError('export differs before build: '+name)
            command=[str(cargo),'build','--locked','--offline','--release','--lib','--no-default-features','--features',FEATURE,'--manifest-path',str(out_path/'source/vm/Cargo.toml')]
            if target:command+=['--target',target]
            run('cargo-build',command);output.check();receipt['cache_after_build']=audit_cache(cache_fd)
            for name,item in files.items():
                if output.read('source/'+name)!=item['bytes']:raise BuildError('export differs after build: '+name)
            parts=([target] if target else [])+['release','libmixer_vm.a']
            library=cache.joinpath(*parts)
            symbols=run('archive-symbols',[str(nm),'--extern-only','--defined-only',str(library)])
            names=[line.split()[-1].removeprefix('_') for line in symbols.splitlines() if line.split() and line.split()[-1].removeprefix('_').startswith('mixer_vm_')]
            if len(names)!=27 or len(set(names))!=27 or sum(n.startswith('mixer_vm_capability_') for n in names)!=15:raise BuildError('archive C symbol family mismatch')
            receipt['public_C_symbols']=sorted(names);receipt['library']=copy_library(output,cache_fd,parts)
        for path,expected in HEADER_HASHES.items():
            raw=files[path]['bytes'];output.write('include/'+Path(path).name,raw,0o644)
        receipt['headers']={Path(p).name:{'sha256':h,'path':str(out_path/'include'/Path(p).name)} for p,h in HEADER_HASHES.items()}
        output.check();receipt['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
        output.write('receipt.json',(json.dumps(receipt,indent=2)+'\n').encode()) # completion manifest last
        print(json.dumps({'library':receipt['library']['path'],'include':str(out_path/'include'),'receipt':str(out_path/'receipt.json')},indent=2))
        return receipt
    except BaseException as error:
        with contextlib.suppress(Exception):
            output.write('failure.json',(json.dumps({'incomplete':True,'error':str(error)[:2048],'commands':receipt['commands']},indent=2)+'\n').encode())
        raise
    finally:output.close()

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--revision',required=True)
    parser.add_argument('--target',choices=['host','ios','ios-simulator','android'],required=True)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--cache',type=Path);parser.add_argument('--ndk',type=Path);parser.add_argument('--rustc',type=Path,help='absolute Rust selector; defaults to rustc discovered on PATH')
    args=parser.parse_args()
    try:build(args)
    except (BuildError,OSError,ValueError,KeyError) as error:
        print('experimental VM build rejected: '+str(error),file=sys.stderr);return 1
    return 0
if __name__=='__main__':sys.exit(main())
