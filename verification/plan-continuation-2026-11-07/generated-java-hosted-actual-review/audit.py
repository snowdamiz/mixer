#!/usr/bin/env python3
"""Read-only frozen hosted pair8 artifact audit. Only writes reports beside this script.

Run: python3 -B verification/plan-continuation-2026-11-07/generated-java-hosted-actual-review/audit.py
No product imports or toolchain execution; only bounded read-only Git subprocesses.
"""
import hashlib
import json
import os
from pathlib import Path
import plistlib
import struct
import sys
import time
import zlib
import subprocess
import zipfile
import re
from datetime import datetime, timezone

OUT = Path(__file__).resolve().parent
REPO = OUT.parents[2]
ROOT = Path('/Users/runner/work/mixer/mixer')
REV = '25ac442c5213326b3601456a5fd62898f152111f'
ART = OUT.parent / 'ci25-generated-java-actual/artifact'
REMOTE = Path('/Users/runner/work/_temp/generated-java-ci')
GIT_CALLS = []
FROZEN = {}
BASE = OUT.parent
RUN = REMOTE / 'integration'
START = time.monotonic()
CHECKS = []
FACTS = {}
MANIFEST = {}


def check(ok, label):
    CHECKS.append({'check': label, 'passed': bool(ok)})
    if not ok:
        raise RuntimeError(label)


def bound():
    if time.monotonic() - START > 240:
        raise RuntimeError('Audit exceeded 240-second read/hash bound')


def git(*args):
    bound()
    argv = ['git', *args]
    p = subprocess.run(argv, cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
    GIT_CALLS.append(dict(argv=argv, exit_code=p.returncode, stdout_bytes=len(p.stdout), stdout_sha256=hashlib.sha256(p.stdout).hexdigest(), stderr=p.stderr.decode()))
    if p.returncode or len(p.stdout)>16*1024**2:
        raise RuntimeError('Read-only Git failed or exceeded output bound: '+repr(argv))
    return p.stdout


def frozen(path):
    path = str(path)
    if path not in FROZEN:
        FROZEN[path] = git('show', REV + ':' + path)
    return FROZEN[path]


def local(path):
    path = Path(path)
    if path.is_relative_to(REMOTE):
        return ART / path.relative_to(REMOTE)
    return path


def read(path):
    path = Path(path)
    if path.is_relative_to(ROOT):
        b = frozen(path.relative_to(ROOT))
        key = 'git:'+REV+':'+str(path.relative_to(ROOT))
    else:
        p = local(path)
        if p.stat().st_size > 128*1024**2:
            raise RuntimeError('Materialized file bound exceeded')
        b = p.read_bytes()
        key = str(p)
    MANIFEST[key] = {'bytes':len(b), 'sha256':hashlib.sha256(b).hexdigest()}
    bound()
    return b


def ident(path):
    b = read(path)
    return {'bytes':len(b), 'sha256':hashlib.sha256(b).hexdigest()}


def pairs(values):
    d = {}
    for k, v in values:
        if k in d:
            raise RuntimeError('Duplicate JSON key ' + k)
        d[k] = v
    return d


def js(path):
    return json.loads(read(path), object_pairs_hook=pairs)


def projection(files):
    return hashlib.sha256(''.join(k + '\0' + v['sha256'] + '\n'
                                  for k, v in sorted(files.items())).encode()).hexdigest()


def inventory(root):
    root = local(root)
    result = {}
    for p in sorted(root.rglob('*')):
        bound()
        if p.is_symlink():
            raise RuntimeError('Unexpected artifact symlink: ' + str(p))
        if p.is_file():
            result[p.relative_to(root).as_posix()] = ident(p)
            if len(result) > 10000:
                raise RuntimeError('Artifact file-count bound exceeded')
    return result


def class_members(path):
    data = read(path)
    if data[:4] != b'\xca\xfe\xba\xbe':
        raise RuntimeError('Bad classfile magic')
    minor, major, n = struct.unpack_from('>HHH', data, 4)
    cp, pos, i = {}, 10, 1
    sizes = {3: 4, 4: 4, 5: 8, 6: 8, 7: 2, 8: 2, 9: 4, 10: 4, 11: 4,
             12: 4, 15: 3, 16: 2, 17: 4, 18: 4, 19: 2, 20: 2}
    while i < n:
        tag = data[pos]
        pos += 1
        if tag == 1:
            size = struct.unpack_from('>H', data, pos)[0]
            pos += 2
            cp[i] = (tag, data[pos:pos + size])
        else:
            size = sizes[tag]
            cp[i] = (tag, data[pos:pos + size])
        pos += size
        i += 2 if tag in (5, 6) else 1
    def u2(b):
        return struct.unpack('>H', b)[0]
    def utf(index):
        # Member identifiers and descriptors in these files are ASCII/UTF-8.
        return cp[index][1].decode('utf-8')
    this_class = struct.unpack_from('>H', data, pos + 2)[0]
    name = utf(u2(cp[this_class][1]))
    refs = []
    for index, (tag, value) in cp.items():
        if tag in (9, 10, 11):
            owner, nt = struct.unpack('>HH', value)
            member, descriptor = struct.unpack('>HH', cp[nt][1])
            refs.append((str(path), '#' + str(index), {9: 'Fieldref', 10: 'Methodref', 11: 'InterfaceMethodref'}[tag],
                         utf(u2(cp[owner][1])) + '.' + utf(member) + ':' + utf(descriptor)))
    return name, minor, major, refs


def dex_classes(path):
    data = read(path)
    check(data[:8] in [b'dex\n035\0', b'dex\n037\0', b'dex\n038\0', b'dex\n039\0',
                          b'dex\n040\0', b'dex\n041\0'], str(path) + ': DEX magic')
    u32 = lambda off: struct.unpack_from('<I', data, off)[0]
    check(u32(32) == len(data) and u32(36) == 112 and u32(40) == 0x12345678, str(path) + ': DEX header')
    check(hashlib.sha1(data[32:]).digest() == data[12:32] and zlib.adler32(data[12:]) == u32(8), str(path) + ': DEX checksums')
    strings = []
    for i in range(u32(56)):
        pos = u32(u32(60) + i * 4)
        while data[pos] & 128:
            pos += 1
        pos += 1
        end = data.index(0, pos)
        strings.append(data[pos:end])
    types = [strings[u32(u32(68) + i * 4)] for i in range(u32(64))]
    return {types[u32(u32(100) + i * 32)].decode('utf-8') for i in range(u32(96))}



def bootstrap_audit(integration):
    capture = ART.parent
    acq = js(capture/'acquisition.json')
    records = js(capture/'artifact-list.json')['artifacts']
    item = next(v for v in records if v['id']==13596648929)
    job = next(v for v in js(capture/'jobs.json')['jobs'] if v['id']==128576481908)
    joblog = read(capture/'job.log').decode('utf-8-sig')
    archive = Path('/tmp/mixer-ci25-generated-java.zip')
    archive_id = ident(archive)
    expected_archive = dict(bytes=14306110,sha256='aa29102263e52d6e0edacc5524953a2680dfa0a32837fdf877d93a6b8b19aa73')
    check(archive_id==expected_archive=={k:acq['archive'][k] for k in ('bytes','sha256')}, 'Exact downloaded ZIP bytes/hash')
    check(item['size_in_bytes']==archive_id['bytes'] and item['digest']=='sha256:'+archive_id['sha256'], 'ZIP digest matches captured GitHub metadata')
    check(item['workflow_run']['id']==acq['run']==job['run_id']==42429965271 and item['workflow_run']['head_sha']==acq['head']==REV, 'Run/revision binding across acquisition, job and artifact')
    check(acq['attempt']==1 and acq['job']==job['id']==128576481908 and acq['artifact']==item['id']==13596648929, 'Exact attempt/job/artifact identity')
    name='generated-java-'+REV+'-42429965271-1'
    check(item['name']==name and name in joblog and 'Artifact ID 13596648929' in joblog and archive_id['sha256'] in joblog and '14306110 bytes' in joblog, 'Upload log binds name, attempt, artifact, ZIP hash and size')
    check(job['name']=='android-generated-java' and job['status']=='completed' and job['conclusion']=='success' and all(v['conclusion']=='success' for v in job['steps']), 'Exact captured job and every step successful')
    check(acq['downloadCompleted'] and acq['responseReaderClosed'] and acq['zipReaderClosed'] and 'not observed' in acq['providerInternalDisposal'], 'Acquisition reports owned-reader closure; explicitly no internal-provider disposal evidence')
    actual = inventory(ART)
    zipped = {}
    with zipfile.ZipFile(archive) as z:
        for member in z.infolist():
            bound()
            name=member.filename
            check(not name.startswith('/') and '..' not in Path(name).parts and not member.is_dir() and name not in zipped, 'Safe unique ZIP file '+name)
            check(member.file_size<=128*1024**2 and len(zipped)<2000 and (member.external_attr>>16)&0o170000 != 0o120000, 'Bounded nonsymlink ZIP entry '+name)
            data=z.read(member)
            zipped[name]=dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
    check(z.fp is None, 'Reviewer ZIP reader closed')
    check(zipped==actual==acq['files'], 'All ZIP CRC/read bytes, extracted bytes and acquisition hashes agree')
    check(len(actual)==acq['extractedFileCount']==1526 and sum(v['bytes'] for v in actual.values())==acq['extractedBytes']==115140057, 'Exact 1526-file 115140057-byte artifact')
    (OUT/'artifact-inventory.json').write_text(json.dumps(actual,indent=2,sort_keys=True)+'\n')
    boot=js(REMOTE/'bootstrap-receipt.json')
    commands=js(REMOTE/'bootstrap-commands/commands.json')
    check(commands==boot['commands'] and len(commands)==13, 'Bootstrap 13-command ledgers agree')
    check(boot['status']=='passed-hosted-java-crosscompile-only' and 'error' not in boot and boot['revision']==REV and boot['git_tree']==integration['git_tree'], 'Actual bootstrap success at exact historical revision/tree')
    check(boot['source_inputs']==integration['source_inputs'] and boot['source_inputs_sha256']==integration['source_inputs_sha256'], 'Bootstrap and integration 101-source closure identical')
    check(boot['limits']=={'bootstrap_command_seconds':300,'bootstrap_seconds':1200,'download_bytes':1836753341,'downloads':2,'integration_seconds':2400,'producer_jobs':2}, 'Finite bootstrap/download/integration/concurrency limits')
    check(boot['initial_disk_space']['admitted'] and boot['initial_disk_space']['minimum_free_bytes']==12884901888 and boot['initial_disk_space']['free_bytes']>=12884901888, 'Actual bootstrap admitted above 12GiB floor')
    check(boot['image']['RUNNER_ARCH']=='X64' and boot['image']['RUNNER_OS']=='macOS' and boot['image']['ImageOS']=='macos26' and boot['image']['ImageVersion']=='20260824.0517.1', 'Hosted Intel image identity')
    labels=['revision','git-tree','curl-version','tar-version','download-swift-host','swift-package-signature','swift-package-expand','swift-package-payload','download-swift-android','extract-swift-android','copy-image-ndk','official-sdk-setup','official-inspect']
    check([c['label'] for c in commands]==labels, 'Download/trust/expand/payload/SDK/preparation order')
    used=0; previous=None
    for index,c in enumerate(commands):
        label=c['label']
        check(c['exit_code']==0 and c['stop'] is None and 'execution_error' not in c, 'Bootstrap '+label+': successful exit')
        check(all(c[k] is True for k in ('direct_child_reaped','stdout_eof','stderr_eof','owned_group_absent','terminal_custody')) and not c['cleanup_errors'] and c['group_observation']['outcome']=='absent' and c['group_observation']['attempts']>=1, 'Bootstrap '+label+': independent EOF/reap/positive group absence')
        check(c['pid']==c['owned_pgid'] and c['pid']>1 and c['signal']['attempted'] and c['signal']['name']=='SIGKILL' and c['signal']['outcome'] in ('sent','already-absent'), 'Bootstrap '+label+': only recorded newly owned group custody')
        check(c['elapsed_seconds']<300 and c['cleanup_seconds_limit']==5 and c['group_observation']['elapsed_seconds']<=5.01 and c['stream_output_limits']=={'stdout':4194304,'stderr':4194304} and c['total_output_limit']==67108864 and c['output_bytes_before']==used, 'Bootstrap '+label+': command/output/cleanup budgets')
        start=datetime.fromisoformat(c['started_utc']).timestamp()
        check(previous is None or start>=previous-.02, 'Bootstrap '+label+': prior terminal custody before next command')
        previous=start+c['elapsed_seconds']
        for stream,v in c['logs'].items():
            check(v['path']==str(REMOTE/'bootstrap-commands'/f'{index:03}-{label}.{stream}') and ident(v['path'])=={k:v[k] for k in ('bytes','sha256')} and v['bytes']<=4194304, 'Bootstrap '+label+': '+stream+' bytes/hash')
            used+=v['bytes']
    elapsed=previous-datetime.fromisoformat(commands[0]['started_utc']).timestamp()
    check(elapsed<1200 and used<67108864, 'Bootstrap aggregate elapsed/output bounds')
    by={v['label']:v for v in commands}
    def log(label,stream='stdout'): return read(by[label]['logs'][stream]['path']).decode()
    check(log('revision').strip()==REV and log('git-tree').strip()==boot['git_tree'] and log('curl-version')==boot['curl_version'] and log('tar-version')==boot['tar_version'], 'Bootstrap raw Git/tool-version evidence')
    owned=Path(boot['cleanup']['owned_path'])
    for key,label,url,size,sha,filename in [
        ('host_download','download-swift-host','https://download.swift.org/swift-6.3.3-release/xcode/swift-6.3.3-RELEASE/swift-6.3.3-RELEASE-osx.pkg',1503529808,'ee82e57774d6650f94aa06302435d6f44a055b9411698db8ecb85d9a3bcc91d0','swift.pkg'),
        ('sdk_download','download-swift-android','https://download.swift.org/swift-6.3.3-release/android-sdk/swift-6.3.3-RELEASE/swift-6.3.3-RELEASE_android.artifactbundle.tar.gz',333223533,'d160cc3206dd1886dae3fef2337af5e25ec034692cd0ec225721c56cc69da7f5','android.tar.gz')]:
        check(boot[key]==dict(bytes=size,sha256=sha,url=url,effective_url=url) and log(label).strip()==url, 'Actual official '+key+' URL/effective URL/size/hash receipt')
        check(by[label]['argv']==['/usr/bin/curl','--fail','--silent','--show-error','--location','--proto','=https','--proto-redir','=https','--connect-timeout','20','--max-time','300','--max-filesize',str(size),'--output',str(owned/filename),'--write-out','%{url_effective}',url], 'Exact bounded HTTPS '+key+' invocation')
    report=log('swift-package-signature')
    check(not log('swift-package-signature','stderr') and ident(by['swift-package-signature']['logs']['stdout']['path'])==dict(bytes=1091,sha256='a6c20c7320918c428ec649491fde14930b9d37d7b7a54e56eb7b49971d05b9c7'), 'Complete successful pkgutil report matches R2 reviewed official report')
    lines=[v.strip() for v in report.splitlines() if v.strip()]
    check(lines.pop(0)=='Package "swift.pkg":' and lines.pop(0)=='Status: signed by a developer certificate issued by Apple for distribution' and lines.pop(0)=='Notarization: trusted by the Apple notary service', 'Actual trusted signed and notarized status')
    signed=datetime.strptime(lines.pop(0),'Signed with a trusted timestamp on: %Y-%m-%d %H:%M:%S %z')
    check(lines.pop(0)=='Certificate Chain:', 'Exact certificate chain report')
    chain=[('Developer ID Installer: Swift Open Source (V9AUD2URP3)','AC12310FADC4904F89203418BE5801B6EE79DE3A0DF223A1F1F4127BAB97B1A5'),('Developer ID Certification Authority','7AFC9D01A62F03A2DE9637936D4AFE68090D2DE18D03F29C88CFB0B1BA63587F'),('Apple Root CA','B0B1730ECBC7FF4505142C49F1295E6EDA6BCAED7E2C68C5BE91B5A11001F024')]
    for n,(who,fingerprint) in enumerate(chain,1):
        check(lines.pop(0)==f'{n}. {who}', 'Certificate identity '+str(n))
        expiry=datetime.strptime(lines.pop(0),'Expires: %Y-%m-%d %H:%M:%S %z')
        check(signed<=expiry and lines.pop(0)=='SHA256 Fingerprint:', 'Certificate timestamp '+str(n))
        octets=[]
        while lines and re.fullmatch(r'[0-9A-F]{2}(?: [0-9A-F]{2})*',lines[0]):octets.extend(lines.pop(0).split())
        check(''.join(octets)==fingerprint,'Exact certificate fingerprint '+str(n))
        if n<3: check(lines.pop(0)=='-'*72,'Certificate separator '+str(n))
    check(not lines, 'Entire package report consumed; no hidden trailing diagnostics')
    check(by['swift-package-signature']['argv']==['/usr/sbin/pkgutil','--check-signature',str(owned/'swift.pkg')] and by['swift-package-expand']['argv']==['/usr/sbin/pkgutil','--expand',str(owned/'swift.pkg'),str(owned/'expanded')], 'Trust invocation binds same package before expansion')
    check(by['swift-package-payload']['argv']==['/usr/bin/tar','-xf',str(owned/'expanded/swift-6.3.3-RELEASE-osx-package.pkg/Payload'),'-C',str(owned/'swift.xctoolchain')], 'Expanded private official payload')
    art=owned/'swift-sdks/swift-6.3.3-RELEASE_android.artifactbundle/swift-android'
    ndk=art/'android-ndk-r27d'
    check(by['extract-swift-android']['argv']==['/usr/bin/tar','-xzf',str(owned/'android.tar.gz'),'-C',str(owned/'swift-sdks')], 'Private Android SDK extraction')
    check(by['copy-image-ndk']['argv']==['/usr/bin/ditto','/Users/runner/Library/Android/sdk/ndk/27.3.13750724',str(ndk)], 'Image NDK copied into private SDK')
    check(by['official-sdk-setup']['argv']==['/bin/bash',str(art/'scripts/setup-android-sdk.sh')] and by['official-sdk-setup']['cwd']==str(art) and 'success: ndk-sysroot linked' in log('official-sdk-setup'), 'Official SDK preparation completed in private bundle')
    check(json.loads(log('official-inspect'))==boot['official_inspect']==integration['official_toolchain'], 'Bootstrap inspection matches all integration tool identities')
    check(boot['cleanup']['terminal_custody'] and boot['cleanup']['owned_removed'] and not any(v.startswith('owned-') for v in actual), 'Bootstrap reports private scratch removed only after integration terminal custody')
    check('Ran 28 tests' in joblog and 'Ran 12 tests' in joblog and len(re.findall(r'\btest_.* \.\.\. ok',joblog))==40, 'Actual 28+12 hosted policy controls passed')
    negative='{"status": "failed", "error": "Need 12GiB free private bootstrap/build capacity; do not delete shared image tools"}'
    positive='{"status": "passed-hosted-java-crosscompile-only", "error": null}'
    check(joblog.index('test_low_disk_main_persists_receipt_before_native_or_download')<joblog.index(negative)<joblog.index('Ran 12 tests')<joblog.index('##[group]Run set -euo pipefail')<joblog.index(positive), 'Intentional low-disk control distinguished from later real success')
    frozen_paths=['verification/plan-continuation-2026-11-07/generated-java-ci-integration/'+v for v in ['bootstrap.py','test_bootstrap.py','test_sparse_checkout.py']]+['scripts/ci/check-android-generated-java.py','.github/workflows/verify.yml']
    expected_hashes=['c7ff731208c61102cf76ab497ab6d098cc1b960e96a843a035079c1b5f355e4b','5958cb4e9350e79760d51bc5aaaa1f8ecee4fe2449ec299aab5678acb842302f','309c1c7eaec226349177d60a5d3607f267c716ee95505c44eb9d83995ba27be6','ba369ff360ee991acf0d0d7867e31170ad663800cadd8b78416a14c6b2a0c4aa']
    for path in frozen_paths:
        content=read(ROOT/path)
        target=OUT/'frozen'/path
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(content)
    check([ident(ROOT/p)['sha256'] for p in frozen_paths[:4]]==expected_hashes, 'Frozen bootstrap, policy tests and runner exactly match accepted signature R2 bytes')
    workflow=frozen(frozen_paths[-1]).decode()
    check('runs-on: macos-26-intel' in workflow and 'name: generated-java-${{ github.sha }}-${{ github.run_id }}-${{ github.run_attempt }}' in workflow, 'Frozen workflow routes Intel and binds artifact run/attempt')
    FACTS['bootstrap']=dict(command_count=13,aggregate_output_bytes=used,elapsed_seconds=round(elapsed,3),downloads={k:boot[k] for k in ['host_download','sdk_download']},image=boot['image'],apple_producer=boot['apple_producer'],cleanup=boot['cleanup'],limits=boot['limits'])
    FACTS['acquisition']=dict(run=acq['run'],attempt=acq['attempt'],job=acq['job'],artifact=acq['artifact'],archive=archive_id,file_count=len(actual),extracted_bytes=sum(v['bytes'] for v in actual.values()),inventory_sha256=projection(actual),reader_claims={k:acq[k] for k in ['downloadCompleted','responseReaderClosed','zipReaderClosed','providerInternalDisposal']},job_url='https://github.com/snowdamiz/mixer/actions/runs/42429965271/job/128576481908')
    FACTS['controls']=dict(bootstrap=28,sparse=12,negative_disk_control_intentional=True)

def main():
    FACTS['git_version'] = git('--version').decode().strip()
    FACTS['checkout_head_observed_only'] = git('rev-parse','HEAD').decode().strip()
    capture_baseline = {str(ART.parent/p):ident(ART.parent/p) for p in ['acquisition.json','artifact-list.json','jobs.json','job.log']}
    full_artifact_baseline = inventory(ART)
    archive_baseline = ident('/tmp/mixer-ci25-generated-java.zip')
    baseline = inventory(RUN)
    preserved_paths = [BASE / 'generated-java-signature-review-r2', BASE / 'ci-e725-generated-java-failure']
    preserved = {str(p): inventory(p) for p in preserved_paths}
    receipt = js(RUN / 'receipt.json')
    check(receipt['status'] == 'passed-java-crosscompile-only', 'Run passed Java/D8 scope')
    check(receipt['revision'] == REV, 'Historical revision; never compare current pair9 checkout')
    tree = git('rev-parse', REV+'^{tree}').decode().strip()
    check(receipt['git_tree'] == tree, 'Frozen Git tree matches hosted receipt')
    bootstrap_audit(receipt)
    source = receipt['source_inputs']
    check(projection(source) == receipt['source_inputs_sha256'] == '53ad5501dcaa0168ec8196c8816d07a246e6b04bcd0160edadd22ecafd4ff815', 'Exact source inventory digest')
    check({p: ident(ROOT / p) for p in source} == source, 'All 101 frozen revision source inputs match run')
    policy = read(ROOT / 'cli/Sources/MixerBuild/AndroidSDKCompatibility.swift').decode()
    profile = json.loads(policy.split('Data(#"""\n', 1)[1].split('\n        """#.utf8)', 1)[0], object_pairs_hook=pairs)
    check(profile['id'] == 'mixer.android-source-pair.8', 'Pair8 profile identity')
    expected = {'scripts/ci/check-android-generated-java.py', 'scripts/ci/check-android-binding.py',
                'cli/Sources/MixerBuild/AndroidSDKCompatibility.swift', 'cli/Sources/MixerBuild/Resources/android-build.py'}
    tracked = git('ls-tree', '-r', '--name-only', REV, 'cli', 'sdk', 'updates').decode().splitlines()
    for package in ('cli', 'sdk', 'updates'):
        expected.update(p for p in tracked if p.startswith(package+'/Sources/') or (p.startswith(package+'/Package.') and p.count('/')==1))
    for p in profile['adapter_files']:
        expected.add('native/android/' + ('engine/' if p.startswith('Sources/') else '') + p)
    check(set(source) == expected and len(source) == 101, 'Source inventory closed over producer packages, runner, adapter')
    for kind, count in (('sdk', 22), ('adapter', 24)):
        check(len(profile[kind + '_files']) == count and projection(profile[kind + '_files']) == profile[kind + '_compatibility_sha256'], kind + ' exact profile projection')
    commands = js(RUN / 'commands/commands.json')
    check(commands == receipt['command_records'] and len(commands) == 79, 'Both 79-command ledgers identical')
    by_label = {c['label']: c for c in commands}
    check(len(by_label) == 79, 'Unique command labels')
    def log(label, stream='stdout'):
        return read(by_label[label]['logs'][stream]['path']).decode()
    used = 0
    held = {23663, 20745, 20770, 20780, 20817, 20842, 20851, 20866, 2424, 2621}
    previous_end = None
    for index, c in enumerate(commands):
        label = c['label']
        check(c['exit_code'] == (1 if '-tamper-' in label else 0) and c['stop'] is None and 'execution_error' not in c, label + ': exit/stop')
        check(all(c[k] is True for k in ('direct_child_reaped', 'stdout_eof', 'stderr_eof', 'owned_group_absent', 'terminal_custody'))
              and not c['cleanup_errors'] and c['group_observation']['outcome'] == 'absent'
              and c['group_observation']['attempts'] >= 1, label + ': reap, independent EOFs, positive absence')
        check(c['pid'] == c['owned_pgid'] and c['pid'] not in held and c['pid'] > 1, label + ': custody only owned group')
        check(c['signal']['attempted'] and c['signal']['name'] == 'SIGKILL' and c['signal']['outcome'] in ('sent', 'already-absent'), label + ': recorded cleanup')
        limits = {'stdout': 8388608 if label.endswith('-javap-members') else 4194304, 'stderr': 4194304}
        check(c['stream_output_limits'] == limits and c['total_output_limit'] == 67108864 and c['output_bytes_before'] == used,
              label + ': exact output bounds/accounting')
        check(c['elapsed_seconds'] < 600 and c['cleanup_seconds_limit'] == 5 and c['group_observation']['elapsed_seconds'] <= 5.01,
              label + ': command and cleanup time bounds')
        start = datetime.fromisoformat(c['started_utc']).timestamp()
        check(previous_end is None or start >= previous_end - .02, label + ': serial command custody')
        previous_end = start + c['elapsed_seconds']
        for stream, value in c['logs'].items():
            p = Path(value['path'])
            check(p == RUN / 'commands' / (f'{index:03}-{label}.' + stream), label + ': ' + stream + ' log path')
            actual = ident(p)
            check(actual == {k: value[k] for k in ('bytes', 'sha256')} and actual['bytes'] <= limits[stream], label + ': ' + stream + ' bytes/hash')
            used += actual['bytes']
    duration = previous_end - datetime.fromisoformat(commands[0]['started_utc']).timestamp()
    check(used < 67108864 and duration < 2400 and len(commands) <= 160, 'Aggregate output, time, command limits')
    check(log('revision').strip() == receipt['revision'] and log('git-tree').strip() == receipt['git_tree'], 'Raw revision/tree outputs')
    inspect = receipt['official_toolchain']
    check(json.loads(log('official-inspect')) == inspect == json.loads(log('official-inspect-postflight')), 'Full canonical pre/post inspection identity')
    check(inspect['schema'] == 1 and inspect['sdk_id'] == 'aarch64-unknown-linux-android28' and inspect['min_api'] == 28 and inspect['target_api'] == 37,
          'Canonical platform scope')
    for label in ('official-inspect', 'official-inspect-postflight'):
        check(by_label[label]['argv'][1:] == ['-B', str(ROOT / 'cli/Sources/MixerBuild/Resources/android-build.py'), 'inspect'], label + ': canonical driver invocation')
    dist = inspect['distributions']
    check(set(dist) == {'swift_toolchain','swift_android_sdk','android_platform','android_build_tools','jdk'}, 'Full five-distribution pre/post inspection')
    for group in ('tools','metadata','distributions'):
        check(all(re.fullmatch('[0-9a-f]{64}', v['sha256']) for v in inspect[group].values()), 'Hosted '+group+' digest identities retained (not local rehash)')
    jt = receipt['javap_tool']
    check(log('javap-version').strip() == log('javap-version-postflight').strip() == jt['version'], 'Raw javap version pre/post')
    check(log('d8-version').strip() == receipt['d8_version'], 'Raw D8 version')
    apple = receipt['apple_producer']
    check(apple == js(REMOTE/'bootstrap-receipt.json')['apple_producer'] and apple['xcode_version']=='26.6' and apple['sdk_version']=='26.5' and apple['xcode_build']=='17F113', 'Bootstrap/integration explicit Xcode26.6 SDK26.5 metadata')
    check(apple['selection']=={'DEVELOPER_DIR':'/Applications/Xcode_26.6.app/Contents/Developer','SDKROOT':'/Applications/Xcode_26.6.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX26.5.sdk'}, 'Exact child-environment Apple routing')
    pins = js(ROOT / 'cli/Package.resolved')['pins']
    dependencies = {p['identity']: dict(location=p['location'], revision=p['state']['revision'], version=p['state']['version'], status='') for p in pins}
    scratch = Path(receipt['cleanup']['owned_scratch_path'])
    for mode in ('debug', 'release'):
        producer = receipt['producers'][mode]
        flags = [receipt['selected_paths']['swift'], 'build', '--package-path', str(ROOT / 'cli'), '--scratch-path', str(scratch / ('producer-' + mode)),
                 '--disable-automatic-resolution', '-j', '2', '-c', mode]
        check(producer['build_argv'] == by_label[mode + '-producer-build']['argv'] == flags + ['--product', 'mixer']
              and by_label[mode + '-producer-bin']['argv'] == flags + ['--show-bin-path'] and producer['jobs'] == receipt['producer_jobs'] == 2,
              mode + ': actual producer build flags/jobs')
        cli = (Path(log(mode + '-producer-bin').strip()) / 'mixer').resolve()
        check(cli.is_relative_to(scratch.resolve() / ('producer-' + mode)) and producer['binary']['bytes'] > 1000000 and len(producer['binary']['sha256']) == 64,
              mode + ': recorded producer binary identity and isolated path')
        check(producer['dependencies'] == producer['dependencies_postflight'] == dependencies, mode + ': immutable pinned dependencies')
        for name, pin in dependencies.items():
            for phase in ('dependency', 'post-dependency'):
                label = mode + '-' + phase + '-' + name
                check(log(label + '-revision').strip() == pin['revision'] and log(label + '-status') == '', label + ': raw checkout evidence')
        check(by_label[mode + '-create']['argv'] == [str(cli), 'create', 'GeneratedJavaApp', '--platform', 'android', '--directory', str(scratch / mode / 'original'),
              '--application', 'dev.mixer.generatedjava', '--sdk-path', str(ROOT / 'sdk'), '--android-adapter-path', str(ROOT / 'native/android')], mode + ': actual CLI create')
        check(by_label[mode + '-export']['argv'] == [str(cli), 'export', str(scratch / mode / 'exported'), '--directory', str(scratch / mode / 'original')], mode + ': actual CLI export')
        for outcome in receipt['tamper'][mode]:
            case = outcome['case']
            label = mode + '-tamper-' + case
            code = 'android.sdk-profile-mismatch' if case == 'profile' else 'android.sdk-profile-required' if case == 'missing-lock' else 'android.sdk-compatibility'
            check(by_label[label]['argv'] == [str(cli), 'build', '--platform', 'android', '--directory', str(scratch / mode / 'tamper' / case)], label + ': actual producer call')
            check(json.loads(log(label)) == outcome['refusal'] and outcome['refusal']['status'] == 'error' and outcome['refusal']['code'] == code, label + ': exact refusal')
            driverlabel = mode + '-driver-tamper-' + case
            check(by_label[driverlabel]['argv'][1:] == ['-B', str(scratch / mode / 'tamper' / case / 'Generated/MixerAndroid/android-build.py'), 'build', str(scratch / mode / 'tamper' / case)], driverlabel + ': copied driver call')
            diagnostic = log(driverlabel) + log(driverlabel, 'stderr')
            check(diagnostic == outcome['driver_refusal'] and 'Android local build error:' in diagnostic and 'Traceback' not in diagnostic and not outcome['build_staging_created'], driverlabel + ': actual fail-closed refusal')
        check({v['case'] for v in receipt['tamper'][mode]} == {'sdk', 'adapter', 'descriptor', 'extra-java', 'profile', 'missing-lock'}, mode + ': all six tamper cases')
    consumers = {}
    all_inventory, all_classes, all_dex, all_lock = [], [], [], []
    for mode in ('debug', 'release'):
        for form in ('original', 'relocated', 'exported'):
            label = mode + '-' + form
            dest = RUN / label
            inv = js(dest / 'consumer-inventory.json')
            lock = js(dest / 'mixer.lock')
            r = js(dest / 'receipt.json')
            summary = receipt['consumers'][label]
            check(projection(inv) == summary['inventory_sha256'] and summary['java_count'] == 18 and summary['classes'] == 215, label + ': consumer summary')
            check(ident(dest / 'mixer.lock') == inv['mixer.lock'] and ident(dest / 'descriptor.json') == profile['default_descriptor'] == inv['Generated/MixerAndroid/app/assets/MixerAppearanceV2/descriptor.json'], label + ': retained lock and descriptor bytes')
            check(lock['android']['profile'] == {k: profile[k] for k in ('id', 'sdk_compatibility_sha256', 'adapter_compatibility_sha256', 'default_descriptor')}
                  and lock['android']['toolchain'] == inspect and lock['swiftVersion'] == inspect['swift_version'], label + ': exact profile/tool lock')
            for kind, directory in (('sdk', 'MixerSDK'), ('adapter', 'MixerAndroid')):
                prefix = 'Generated/' + directory + '/'
                files = {p[len(prefix):]: v for p, v in inv.items() if p.startswith(prefix)}
                check(all(files.get(p) == v for p, v in profile[kind + '_files'].items()), label + ': ' + kind + ' pinned byte preservation')
                check(projection(files) == (lock['sdkDigest'] if kind == 'sdk' else lock['android']['adapterDigest']), label + ': ' + kind + ' full lock digest')
                closed = ('Sources/MixerCore/', 'Sources/MixerUI/') if kind == 'sdk' else ('Sources/MixerAndroidRuntime/', 'app/src/', 'bridge/', 'contracts/')
                check({p for p in files if p.startswith(closed)} == {p for p in profile[kind + '_files'] if p.startswith(closed)}, label + ': ' + kind + ' closed source roster')
            dirs = js(dest / 'consumer-directories.json')
            check(len(dirs) == len(set(dirs)) and all(str(p) in dirs for f in inv for p in Path(f).parents if str(p) != '.'), label + ': retained directory topology')
            sources = {'Generated/MixerAndroid/' + p: v for p, v in profile['adapter_files'].items() if p.endswith('.java')}
            check(r['sources'] == sources and {p for p in inv if p.endswith('.java')} == set(sources), label + ': all 18 original product Java sources')
            jar = inspect['distributions']['android_platform']['path'] + '/android.jar'
            javac = [inspect['tools']['javac']['path'], '--release', '17', '-Xlint:all', '-Werror', '-proc:none', '-sourcepath', '', '-classpath', jar, '-d', str(dest / 'classes')]
            check(by_label[label + '-javac']['argv'] == javac + [str(scratch / mode / form / p) for p in sorted(sources)], label + ': strict actual javac closure')
            classes = inventory(dest / 'classes')
            dex = inventory(dest / 'dex')
            check(classes == r['classes'] and len(classes) == 215 and dex == r['dex'] and set(dex) == {'classes.dex'}, label + ': all class and DEX file hashes')
            classpaths = [str(dest / 'classes' / p) for p in sorted(classes)]
            check(by_label[label + '-d8']['argv'] == [inspect['tools']['d8']['path'], '--min-api', '28', '--lib', jar, '--output', str(dest / 'dex')] + classpaths, label + ': D8 min28 all-class inputs')
            members = js(dest / 'member-references.json')
            check(ident(dest / 'member-references.json') == r['member_references']['inventory'] and r['member_references'] == summary['member_references'], label + ': member receipt binding')
            check(members['class_inputs'] == classes and members['argv'] == by_label[label + '-javap-members']['argv'] == [jt['path'], '-v', '-p', '-c', '-s'] + classpaths, label + ': complete javap inputs')
            raw = read(dest / 'member-references.javap.txt').decode()
            check(raw == log(label + '-javap-members') and ident(dest / 'member-references.javap.txt') == {k: members['raw_output'][k] for k in ('bytes', 'sha256')}, label + ': retained raw javap bytes')
            parsed, scoped, current = [], [], None
            for line in raw.splitlines():
                if line.startswith('Classfile '):
                    current = line[len('Classfile '):].strip()
                    scoped.append(current)
                left, sep, right = line.strip().partition(' = ')
                if sep and right.split()[0] in ('Fieldref', 'Methodref', 'InterfaceMethodref'):
                    parsed.append(dict(class_file=current, constant_pool_index=left, kind=right.split()[0], member=right.partition(' // ')[2], raw_entry=line))
            check(scoped == classpaths and parsed == members['references'] and len(parsed) == r['member_references']['count'] == 4946, label + ': complete raw 215-class/4946-reference inventory')
            binary_refs, binary_names = [], set()
            for path in classpaths:
                name, minor, major, refs = class_members(Path(path))
                check(major == 61 and minor == 0 and name + '.class' == str(Path(path).relative_to(dest / 'classes')), label + ': Java17 binary ' + name)
                binary_refs += refs
                binary_names.add('L' + name + ';')
            reported_refs = [(m['class_file'], m['constant_pool_index'], m['kind'], m['member'].replace('"', '')) for m in parsed]
            check(binary_refs == reported_refs, label + ': independently decoded binary constant-pool refs')
            descriptors = dex_classes(dest / 'dex/classes.dex')
            raw_descriptors = {line.partition(':')[2].strip().strip("'") for line in log(label + '-dexdump').splitlines() if line.strip().startswith('Class descriptor')}
            check(descriptors == raw_descriptors and binary_names <= descriptors, label + ': binary DEX matches dexdump and contains all 215 product classes')
            consumers[label] = {'class_count': len(classes), 'dex_class_count': len(descriptors), 'member_count': len(parsed), 'raw_javap': ident(dest / 'member-references.javap.txt'), 'dex': dex,
                                'class_inventory_sha256': projection(classes), 'consumer_inventory_sha256': projection(inv), 'member_inventory': ident(dest / 'member-references.json')}
            all_inventory.append(inv)
            all_classes.append(classes)
            all_dex.append(dex)
            all_lock.append(read(dest / 'mixer.lock'))
    check(all(v == all_inventory[0] for v in all_inventory), 'All six full consumer inventories byte-identical')
    check(all(v == all_classes[0] for v in all_classes), 'All six class inventories byte-identical')
    check(all(v == all_dex[0] for v in all_dex), 'All six DEX files byte-identical')
    check(all(v == all_lock[0] for v in all_lock), 'All six locks byte-identical')
    cleanup = receipt['cleanup']
    check(cleanup['owned_scratch_started'] and cleanup['owned_scratch_removed'] and cleanup['command_custody_terminal'], 'Historical scratch removal after terminal custody; no live path/process inference')
    check(not any(p.startswith('generated-java-owned-') for p in baseline), 'Uploaded integration contains retained products, no owned scratch')
    for p in preserved_paths:
        check(inventory(p)==preserved[str(p)], 'Prior review/failure evidence unchanged: '+p.name)
    check(inventory(RUN)==baseline, 'All integration artifacts unchanged during audit')
    check(inventory(ART)==full_artifact_baseline and ident('/tmp/mixer-ci25-generated-java.zip')==archive_baseline, 'Full uploaded ZIP and extracted bootstrap/integration artifact unchanged before/after')
    check({p:ident(p) for p in capture_baseline}==capture_baseline, 'All acquisition/job/artifact metadata and job log unchanged before/after')
    FACTS['capture_inputs'] = capture_baseline
    FROZEN.clear()
    check({p:ident(ROOT/p) for p in source}==source, 'Frozen25ac source independently reread postflight')
    FACTS.update(run_receipt=ident(RUN/'receipt.json'), source_revision=receipt['revision'], git_tree=tree,
        source_inputs_sha256=projection(source), source_inputs=source, producers=receipt['producers'], consumers=consumers,
        distributions=dist, command_count=len(commands), aggregate_output_bytes=used, run_elapsed_seconds=round(duration,3),
        command_ledger=ident(RUN/'commands/commands.json'), preserved_evidence={p:{'files':len(v),'inventory_sha256':projection(v)} for p,v in preserved.items()},
        integration_artifact_files=len(baseline), integration_inventory_sha256=projection(baseline))


if __name__ == '__main__':
    error = None
    try:
        main()
    except Exception as exc:
        error = type(exc).__name__ + ': ' + str(exc)
    report = dict(schema=1, verdict='ACCEPT' if error is None else 'REQUEST CHANGES', error=error,
                  finished_utc=datetime.now(timezone.utc).isoformat(), elapsed_seconds=round(time.monotonic() - START, 3),
                  python=sys.version, python_executable=sys.executable, python_identity=ident(Path(sys.executable).resolve()),
                  audit_script=ident(Path(__file__)), command=[sys.executable, '-B', str(Path(__file__).resolve())],
                  checks=CHECKS, facts=FACTS, read_manifest=MANIFEST, git_calls=GIT_CALLS,
                  limits=dict(seconds=240, git_command_seconds=15, git_stdout_bytes=16*1024**2, artifact_files=10000, zip_files=2000, materialized_file_bytes=128*1024**2),
                  scope='First successful hosted frozen pair8 Java17/D8 bootstrap only; no API-floor approval',
                  limitations=['Producer binaries, generated source directories, dependency checkouts, and tamper trees were removed by the runner; their historical identity/admission and immutability use the hash-bound reviewed runner and retained command/consumer receipts.',
                               'Hosted tools and downloads were removed; their identities use captured receipts and frozen owning code, not a fresh byte rehash. Positive process-group absence and scratch deletion are historical receipt evidence; no process probes. Escaped descendants, provider-internal HTTP disposal and entire worker disposal are outside the claim.',
                               'No APK, runtime, API28 linkage/floor, device, signing, immutable published package, FieldLog release, or GA qualification.'],
                  reviewer_child_delegation=0, reviewer_compiler_jvm_native_runs=0, reviewer_process_probes_or_signals=0,
                  commits=0, pushes=0, write_ownership=str(OUT))
    (OUT / 'audit.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'verdict': report['verdict'], 'error': error, 'checks': len(CHECKS), 'elapsed_seconds': report['elapsed_seconds']}))
    sys.exit(0 if error is None else 1)
