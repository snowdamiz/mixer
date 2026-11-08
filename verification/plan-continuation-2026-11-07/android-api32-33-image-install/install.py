"""Install two absent official images for the named API32/33 motion gate."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parent.parent
SDK = Path('/opt/homebrew/share/android-commandlinetools')
JDK = Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')
sys.path.insert(0, str(BASE/'native-custody-premise'))
from cleanup_control import Commands

def require(value, message):
    if not value:
        raise RuntimeError(message)

def identity(path):
    require(path.is_file() and not path.is_symlink(), 'Regular input required: '+str(path))
    h = hashlib.sha256()
    with path.open('rb') as stream:
        while data := stream.read(1024*1024):
            h.update(data)
    return {'bytes': path.stat().st_size, 'sha256': h.hexdigest()}

def local(element):
    return element.tag.rsplit('}', 1)[-1]

def first(element, name):
    rows = [x for x in element if local(x)==name]
    require(len(rows)==1, 'Exact metadata child required: '+name)
    return rows[0]

def main():
    receipt = {'startedAt': datetime.now(timezone.utc).isoformat(),
               'scope': 'Install official API32/33 ARM64 images; no device or runtime execution',
               'namedNextGate': 'PAIR9-MOTION-API32-33', 'runtimeQualified': False,
               'nativeInstancesStarted': 0, 'historicalHoldsReleased': False}
    logs = HERE/'commands'
    logs.mkdir(exist_ok=False)
    scratch = HERE/'scratch'
    scratch.mkdir(exist_ok=False)
    user = scratch/'android-user'
    user.mkdir()
    env = dict(os.environ, JAVA_HOME=str(JDK), ANDROID_HOME=str(SDK),
               ANDROID_SDK_ROOT=str(SDK), ANDROID_USER_HOME=str(user),
               PYTHONDONTWRITEBYTECODE='1')
    commands = Commands(logs, env, deadline=time.monotonic()+660,
                        output_bytes=8*1024*1024, total_output_bytes=64*1024*1024)
    try:
        old = json.loads((BASE/'android-api28-image-install/receipt.json').read_text())
        protected = {name: identity(Path(name)) for name in old['protectedTools']}
        require(protected==old['protectedTools'], 'Previously admitted tool/image bytes changed')
        receipt['protectedBefore'] = protected
        meta = BASE/'android-lower-api-availability/android.xml'
        receipt['officialMetadata'] = {'path': str(meta), **identity(meta)}
        root = ET.fromstring(meta.read_bytes())
        selected = []
        for api, size, checksum in [(32,643262633,'c57d92a4131590b2a3b62f2a728766aa6bbec57f'),
                                   (33,672331372,'69883e92b77f8705af135ee86e1d87589f8f113e')]:
            package = f'system-images;android-{api};default;arm64-v8a'
            target = SDK/f'system-images/android-{api}/default/arm64-v8a'
            require(not target.exists(), 'Selected target already exists; no reinstall')
            matches = [e for e in root.iter() if local(e)=='remotePackage' and e.get('path')==package]
            require(len(matches)==1, 'One official package required')
            entry = matches[0]
            revision = int(first(first(entry,'revision'),'major').text)
            complete = first(first(first(entry,'archives'),'archive'),'complete')
            archive = {'url': 'https://dl.google.com/android/repository/sys-img/android/'+first(complete,'url').text,
                       'bytes': int(first(complete,'size').text), 'publisherSHA1': first(complete,'checksum').text}
            require(revision==2 and archive['bytes']==size and archive['publisherSHA1']==checksum,
                    'Pinned official archive selection changed')
            selected.append({'api':api,'package':package,'target':str(target),'revision':revision,
                             'archive':archive,'targetPreviouslyAbsent':True})
        receipt['selected'] = selected
        space = os.statvfs(SDK)
        receipt['initialFreeBytes'] = space.f_bavail*space.f_frsize
        require(receipt['initialFreeBytes']>=16*1024**3, 'Need 16GiB free for two image installations')
        receipt['sdkmanagerIdentity'] = identity(SDK/'cmdline-tools/latest/bin/sdkmanager')
        receipt['javaIdentity'] = identity((JDK/'bin/java').resolve())
        (HERE/'selection.json').write_text(json.dumps(receipt, indent=2)+'\n')
        argv = [str(SDK/'cmdline-tools/latest/bin/sdkmanager'), '--sdk_root='+str(SDK),
                '--install', *[row['package'] for row in selected]]
        item = commands.start('install-two-official-images', argv, ROOT)
        deadline = time.monotonic()+600
        while not commands.hold:
            commands.pump(.05)
            commands.reaped(item)
            if item['record']['direct_child_reaped'] or commands.limit or time.monotonic()>=deadline:
                break
        commands.stop(item)
        record = item['record']
        require(record['terminal_custody'] and record['exit_code']==0 and not commands.limit,
                'Image installation did not complete with terminal custody')
        receipt['installed'] = {}
        for row in selected:
            target = Path(row['target'])
            package = ET.fromstring((target/'package.xml').read_bytes())
            lp = [e for e in package.iter() if local(e)=='localPackage' and e.get('path')==row['package']]
            require(len(lp)==1 and int(first(first(lp[0],'revision'),'major').text)==row['revision'],
                    'Installed official package revision mismatch')
            properties = (target/'source.properties').read_text()
            require(f'AndroidVersion.ApiLevel={row["api"]}' in properties and 'SystemImage.Abi=arm64-v8a' in properties,
                    'Installed image API or ABI mismatch')
            receipt['installed'][row['package']] = {'sourceProperties':properties,
                'files': {str(p.relative_to(target)):identity(p) for p in sorted(target.rglob('*')) if p.is_file()}}
        receipt['protectedAfter'] = {name: identity(Path(name)) for name in protected}
        require(receipt['protectedAfter']==protected, 'Protected tool or existing image changed')
        receipt['status'] = 'INSTALLED_OFFICIAL_IMAGES_RUNTIME_UNRUN'
    except BaseException as error:
        receipt['status'] = 'STOPPED'
        receipt['error'] = repr(error)
    finally:
        receipt['cleanup'] = commands.cleanup(scratch)
        receipt['finishedAt'] = datetime.now(timezone.utc).isoformat()
        (HERE/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps({key:value for key,value in receipt.items()
                     if key not in ('protectedBefore','protectedAfter','installed')}))

if __name__ == '__main__':
    main()
