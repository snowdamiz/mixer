#!/usr/bin/env python3
"""Execute explicit JVM closures against frozen source bytes and controlled leaves."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import time
from private_owner_commands import ControlledCommands, CUSTODIAN_SHA256

ROOT = Path(__file__).resolve().parents[3]
TESTS = 'native/android/tests/'
ROSTER = TESTS+'private-owner-host-roster.json'
MAPPING = TESTS+'private-owner-barrier-map.json'
BINDINGS = TESTS+'private-owner-barrier-bindings.json'
DESCRIPTOR = 'verification/ui-measured-appearance-v2-contract/mixer-measured-default-v2.json'
STRIP = ('_JAVA_OPTIONS','JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','CLASSPATH','JAVA_OPTS','JDK_JAVAC_OPTIONS','TOOLCHAINS')
CASES = ('clean','terminal-at-entry','terminal-before-return','dirty-at-entry','dirty-before-return','ordinary-throw-after-callback','fatal-throw-after-callback')

def ident(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

def save(path, value):
    temporary = path.with_name(path.name+'.tmp')
    with temporary.open('w') as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True)+'\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)

def check(value, message):
    if not value:
        raise RuntimeError(message)

def source_anchors(frozen, mapping):
    check(len(mapping['records']) == 189, '189 callback obligations required')
    check(len({r['baseline'] for r in mapping['records']}) == 189, 'duplicate callback ID')
    for source, digest in mapping['source_sha256'].items():
        check(ident(frozen[source])['sha256'] == digest, 'callback map source changed: '+source)
    for record in mapping['records']:
        check(tuple(record['required_cases']) == CASES, 'callback cases changed')
        text = frozen[record['source']].decode()
        lines = text.splitlines(keepends=True)
        check(len(record['candidates']) == 1, 'single accepted anchor required')
        for candidate in record['candidates']:
            at = sum(map(len, lines[:candidate['line']-1]))+candidate['column']-1
            check(text[at:at+len(candidate['text'])] == candidate['text'], 'source anchor changed: '+record['baseline'])

def parse_javap(text):
    methods = {}
    current_class = name = method = None
    for line in text.splitlines():
        declaration = re.match(r'.*\b(?:class|interface) ([\w.$]+).*\{\s*$', line)
        if declaration:
            current_class = declaration.group(1)
            name = method = None
        elif line.startswith('  ') and not line.startswith('    ') and line.rstrip().endswith(';'):
            signature = line.strip()
            if '(' in signature:
                name = signature.split('(',1)[0].split()[-1]
                if name == current_class:
                    name = '<init>'
            elif signature == 'static {};':
                name = '<clinit>'
            else:
                name = None
            method = None
        elif line.strip().startswith('descriptor:') and name:
            descriptor = line.split('descriptor:',1)[1].strip()
            check((current_class, name, descriptor) not in methods, 'duplicate compiled method')
            method = {'instructions': {}, 'lines': []}
            methods[(current_class, name, descriptor)] = method
        elif method is not None:
            instruction = re.match(r'\s*(\d+):\s+([a-z][a-z0-9_]*)\s*(.*)', line)
            source = re.match(r'\s*line (\d+): (\d+)\s*$', line)
            if source:
                method['lines'].append((int(source.group(2)), int(source.group(1))))
            elif instruction:
                offset = int(instruction.group(1))
                check(offset not in method['instructions'], 'duplicate compiled instruction')
                method['instructions'][offset] = (instruction.group(2), instruction.group(3).strip())
    return methods

def bytecode_anchors(text, fixture, mapping):
    methods = parse_javap(text)
    records = {r['baseline']: r for r in mapping['records']}
    check(len(fixture['bindings']) == 189 and len({r['site'] for r in fixture['bindings']}) == 189, '189 BCI fixtures required')
    check({r['site'] for r in fixture['bindings']} == set(records), 'BCI fixture ID mismatch')
    check(len(fixture['helpers']) == 15 and len(set(fixture['helpers'])) == 15, '15 helper obligations required')
    helpers = [r['baseline'] for r in mapping['records'] if any(k in r['boundary']['mode'] for k in ('helper','constructor'))]
    check(set(helpers) == set(fixture['helpers']), 'helper obligations differ from source map')
    results = []
    for binding in fixture['bindings']:
        record = records[binding['site']]
        line = record['candidates'][0]['line']
        check(binding['source'] == record['source'] and binding['line'] == line, 'source/target obligation disagreement')
        check(binding['opcode'] in ('invokevirtual','invokeinterface','invokespecial','invokestatic'), 'unsupported invocation opcode')
        expected = binding['invocation'].split('//',1)[-1].strip()
        candidates = []
        owner = 'dev.mixer.android.'+record['class']
        for (cls, name, descriptor), method in methods.items():
            if cls != owner and not cls.startswith(owner+'$'):
                continue
            if record.get('caller_method_prefix') and not name.startswith(record['caller_method_prefix']):
                continue
            for offset, (opcode, operands) in method['instructions'].items():
                if opcode != binding['opcode'] or operands.split('//',1)[-1].strip() != expected:
                    continue
                positions = [x for x in method['lines'] if x[0] <= offset]
                if positions and max(positions,key=lambda x:x[0])[1] == line:
                    candidates.append({'site':binding['site'], 'source':record['source'],
                        'exactCaller':cls+'#'+name+descriptor+'@'+str(offset),
                        'class':cls, 'method':name, 'descriptor':descriptor, 'bytecodeIndex':offset,
                        'line':line, 'opcode':opcode, 'target':expected})
        check(len(candidates) == 1, 'compiled anchor absent or ambiguous: '+binding['site']+' candidates='+str(len(candidates)))
        results.append(candidates[0])
    distinct = len({r['exactCaller'] for r in results})
    check(distinct == 189, 'compiled obligations collapsed')
    return {'status':'passed-before-matrix', 'binding_origin':'actual compiled bytecode; historical exactCaller is evidence only',
        'bindings':results, 'helpers':helpers, 'distinctBindings':distinct, 'compiledMethods':len(methods)}

def frame_key(frame):
    return frame['class']+'#'+frame['method']+frame['descriptor']+'@'+str(frame['bytecodeIndex'])

def matrix_proof(evidence, observed, mapping):
    matrix = json.loads((evidence/'barrier-cases.json').read_text())
    cases = matrix['cases']
    bindings = {b['site']:b for b in observed['bindings']}
    check(len(bindings) == 189 and len({b['exactCaller'] for b in bindings.values()}) == 189, '189 observed bindings required')
    expected = {s:b['exactCaller'] for s,b in bindings.items()}
    check(matrix['missing'] == [] and len(cases) == 1323, 'full matrix incomplete')
    check({(c['site'],c['case']) for c in cases} == {(s,k) for s in expected for k in CASES}, 'matrix IDs/cases differ')
    for c in cases:
        check(c['hit'] is True and c['exactCaller'] == expected[c['site']], 'matrix runtime BCI differs')
        check(len(c['selectedFrames']) == 1, 'ambiguous matrix runtime frame')
        f = c['selectedFrames'][0]
        check(frame_key(f) == c['exactCaller'] and f['line'] == bindings[c['site']]['line'], 'matrix frame evidence differs')
    helpers = [json.loads(x) for x in (evidence/'helper-boundaries.jsonl').read_text().splitlines()]
    check(len(helpers) == 15 and {h['site'] for h in helpers} == set(observed['helpers']), 'helper matrix incomplete')
    records = {r['baseline']:r for r in mapping['records']}
    clean = {c['site']:c for c in cases if c['case'] == 'clean'}
    for helper in helpers:
        site = helper['site']
        record, boundary = records[site], records[site]['boundary']
        sequence = helper['helperNativeSequence']
        check(helper['finalAnchorMatches'] is True and helper['exactCaller'] == expected[site], 'helper final return mismatch')
        check(isinstance(sequence,list) and len(sequence) > 0, 'empty helper native sequence: '+site)
        check(sequence == clean[site]['helperNativeSequence'], 'helper sequence differs from clean matrix')
        check(helper['helperSequenceEnd'] == clean[site]['helperSequenceEnd'] == 'original invocation frame/operation left', 'helper trace did not finish')
        for event in sequence:
            check(event['phase'] in ('entry','beforeReturn') and bool(event['productionFrames']), 'invalid helper event')
            check(any(frame_key(f) == expected[site] and f['line'] == bindings[site]['line'] for f in event['productionFrames']), 'helper lost original invocation')
        last = sequence[-1]
        target = boundary['return_native_suffix']
        check(last['phase'] == 'beforeReturn' and (target == '*' or (last['nativeMethod'] == target if '.' in target else last['nativeMethod'].endswith('.'+target))), 'helper final native target differs')
        for key, field in (('return_receiver_id','receiverId'),('return_receiver_class','receiverClass')):
            check(boundary[key] is None or last[field] == boundary[key], 'helper final receiver differs')
        if boundary['return_frame_line'] is not None:
            check(any(f['class'] == 'dev.mixer.android.NativeAppearanceViewsV2' and f['line'] == boundary['return_frame_line'] for f in last['productionFrames']), 'helper final source frame differs')
    return {'cases':len(cases),'IDs':len(expected),'distinctBindings':len(set(expected.values())), 'helpers':len(helpers),'allCasesHit':True,'allHelpersFinal':True,'missing':[]}

def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--closure', choices=('A','B'), default='B')
    parser.add_argument('--jdk', type=Path, default=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home'))
    parser.add_argument('--active-seconds', type=float, default=360)
    parser.add_argument('--aggregate-bytes', type=int, default=64*1024*1024)
    args = parser.parse_args(argv)
    check(0 < args.active_seconds <= 480, 'finite active command budget required')
    check(0 < args.aggregate_bytes <= 64*1024*1024, 'aggregate output budget must be at most 64 MiB')
    evidence = args.evidence.resolve()
    evidence.mkdir(parents=True, exist_ok=False)
    scratch = evidence/'scratch'
    scratch.mkdir()
    started = time.monotonic()
    receipt = {'schema':3, 'closure':args.closure, 'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'argv':list(argv) if argv is not None else sys.argv[1:], 'python':sys.version, 'scope':'installed production bytes, controlled Android/JNI leaves; host JVM only',
        'status':'failed', 'custodian_sha256':CUSTODIAN_SHA256, 'command_budget_seconds':args.active_seconds,
        'cleanup_reserve_seconds':60, 'native_or_capture_processes_started_or_queried':False}
    env = dict(os.environ)
    for key in STRIP:
        env.pop(key,None)
    env.update(TMPDIR=str(scratch), PYTHONDONTWRITEBYTECODE='1')
    commands = ControlledCommands(evidence, env, deadline=started+args.active_seconds+60)
    commands.commands.total_output_bytes = args.aggregate_bytes
    frozen = {}
    interrupted = False
    try:
        roster_bytes = (ROOT/ROSTER).read_bytes()
        roster = json.loads(roster_bytes)
        closure = roster['closures']['A-orchestration' if args.closure == 'A' else 'B-concrete-renderer-views']
        sources = closure['actual_production_sources']+[s['source'] for s in closure['substitutes']]+closure['test_support_sources']+[closure['test_source']]
        check(len(set(sources)) == len(sources), 'duplicate explicit source')
        fqcn = []
        for source in sources:
            check(not Path(source).is_absolute() and '..' not in Path(source).parts, 'source outside repository')
            data = (ROOT/source).read_bytes()
            package = re.search(rb'\bpackage\s+([\w.]+)\s*;',data)
            check(package is not None, 'explicit package required')
            fqcn.append(package.group(1).decode()+'.'+Path(source).stem)
            frozen[source] = data
        check(len(fqcn) == len(set(fqcn)), 'duplicate source FQCN')
        check('dev.mixer.android.AndroidUIProfile' in fqcn and 'native/android/app/src/dev/mixer/android/AndroidUIProfile.java' in closure['actual_production_sources'], 'actual public profile required')
        for key in (ROSTER, MAPPING, BINDINGS, DESCRIPTOR, TESTS+'run-private-owner-host.py', TESTS+'private_owner_commands.py', TESTS+'private_owner_cleanup_control.py'):
            frozen[key] = (ROOT/key).read_bytes()
        mapping = json.loads(frozen[MAPPING])
        fixture = json.loads(frozen[BINDINGS])
        check(ident(frozen[MAPPING])['sha256'] == fixture['provenance']['map_sha256'], 'map/binding fixture mismatch')
        if args.closure == 'B':
            source_anchors(frozen, mapping)
        save(evidence/'source-map.json', {s:ident(b) for s,b in frozen.items()})
        save(evidence/'roster.json', {'closure':closure,'sourceCount':len(sources),'fqcn':fqcn})
        inputs = evidence/'inputs'
        for source,data in frozen.items():
            dest = inputs/source
            dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_bytes(data)
        jdk = args.jdk.resolve(strict=True)
        tools = {name:(jdk/'bin'/name).resolve(strict=True) for name in ('java','javac','javap')}
        check(all(p.is_file() and os.access(p,os.X_OK) for p in tools.values()), 'executable tool required before launch')
        receipt['tools'] = {name:{'path':str(p),**ident(p.read_bytes())} for name,p in tools.items()}
        env['JAVA_HOME'] = str(jdk)
        check(evidence.is_dir() and scratch.is_dir() and scratch.resolve() == scratch and scratch.parent == evidence, 'invalid evidence/scratch directory')
        classes = scratch/'classes'
        empty = scratch/'empty'
        classes.mkdir(); empty.mkdir()
        compile_argv = [tools['javac'],'-J-Xmx256m','-J-XX:ActiveProcessorCount=2','--release','17','-Xlint:all','-Werror','-proc:none','-classpath',empty,'-sourcepath',empty,'-d',classes,*[inputs/s for s in sources]]
        scratch_stat, evidence_stat = scratch.stat(), evidence.stat()
        receipt['launch_identity'] = {'evidence':str(evidence), 'scratch':str(scratch),
            'evidence_identity':{'device':evidence_stat.st_dev,'inode':evidence_stat.st_ino},
            'scratch_identity':{'device':scratch_stat.st_dev,'inode':scratch_stat.st_ino},
            'sources':{s:ident(data) for s,data in frozen.items()}, 'tools':receipt['tools'],
            'python_executable':{'path':str(Path(sys.executable).resolve()),**ident(Path(sys.executable).read_bytes())},
            'first_argv':[str(tools['java']),'-version'], 'compile_argv':list(map(str,compile_argv)),
            'bounds':{'active_seconds':args.active_seconds,'cleanup_reserve_seconds':60,'per_command_bytes':8*1024*1024,
                'aggregate_bytes':args.aggregate_bytes,'compile_seconds':60,'bytecode_seconds':30,'host_seconds':300 if args.closure == 'B' else 120},
            'outer_custody':'not established by this inner runner'}
        receipt['status'] = 'PREPARED'
        receipt['command_admissions'] = []
        save(evidence/'launch-identity.json',receipt['launch_identity'])
        save(evidence/'receipt.json',receipt)
        def launch(label, command, timeout):
            executable = Path(command[0])
            check(executable.is_file() and os.access(executable,os.X_OK), 'executable unavailable before admission')
            check(ident(executable.read_bytes())['sha256'] == next(v['sha256'] for v in receipt['tools'].values() if v['path'] == str(executable)), 'tool changed before admission')
            current = scratch.stat()
            check((current.st_dev,current.st_ino) == (scratch_stat.st_dev,scratch_stat.st_ino), 'scratch identity changed')
            receipt['command_admissions'].append({'label':label,'argv':list(map(str,command)), 'cwd':str(scratch),
                'timeout_seconds':timeout,'prepared_monotonic':time.monotonic()})
            save(evidence/'receipt.json',receipt)
            return commands.run(label,command,scratch,timeout)
        for name in ('java','javac','javap'):
            launch(name+'-version',[tools[name],'-version'],10)
        launch('compile',compile_argv,60)
        class_files = sorted(classes.rglob('*.class'))
        save(evidence/'class-map.json',{str(p.relative_to(classes)):ident(p.read_bytes()) for p in class_files})
        shutil.copytree(classes,evidence/'classes')
        names = [str(p.relative_to(classes)).removesuffix('.class').replace('/','.') for p in class_files if p.name.startswith(('NativeRenderer','NativeAppearanceViewsV2','NativeEditorConnectionV2'))] if args.closure == 'B' else ['dev.mixer.android.NativeOwnerV2','dev.mixer.android.NativeCoordinatorV2']
        bytecode = launch('bytecode',[tools['javap'],'-J-Xmx256m','-J-XX:ActiveProcessorCount=2','-c','-p','-s','-l','-classpath',classes,*names],30)
        (evidence/'bytecode.txt').write_bytes(bytecode)
        if args.closure == 'B':
            proof = bytecode_anchors(bytecode.decode(),fixture,mapping)
            proof['provenance'] = {'compiler':receipt['tools']['javac'], 'compiler_version':commands.commands.captured('javac-version'),
                'sources':receipt['launch_identity']['sources'], 'classes':ident((evidence/'class-map.json').read_bytes()),
                'bytecode':ident(bytecode), 'historical_fixture':ident(frozen[BINDINGS])}
            check(proof['distinctBindings'] == 189,'distinct BCI anchors required before matrix')
            save(evidence/'barrier-preflight.json',proof)
        host = [tools['java'],'-ea','-Xmx256m','-XX:ActiveProcessorCount=2','-cp',classes,'dev.mixer.android.NativeOwnerV2'+('Concrete' if args.closure == 'B' else '')+'HostTests',inputs/DESCRIPTOR,evidence/'observed-sites.txt']
        if args.closure == 'B':
            host += [inputs/MAPPING,evidence/'barrier-cases.json']
        result = launch('host',host,300 if args.closure == 'B' else 120)
        check(result.startswith(b'PASS '),'missing host PASS')
        receipt['host_stdout'] = result.decode().strip()
        if args.closure == 'B':
            receipt['matrix'] = matrix_proof(evidence,proof,mapping)
        receipt['status'] = 'passed-host-only'
    except BaseException as error:
        interrupted = isinstance(error,(KeyboardInterrupt,SystemExit))
        receipt['status'] = 'failed'
        receipt['failure'] = {'type':type(error).__name__,'message':str(error)}
    finally:
        receipt['cleanup'] = commands.finish(scratch,retain_scratch=interrupted)
        if commands.commands.hold or not receipt['cleanup']['allTerminalCustody'] or (not receipt['cleanup']['scratchRemoved'] and not interrupted):
            receipt['status'] = 'UNKNOWN' if commands.commands.hold else 'failed'
        receipt['source_stable'] = all((ROOT/s).read_bytes() == data for s,data in frozen.items())
        if not receipt['source_stable']:
            receipt['status'] = 'failed'
        receipt['elapsed_seconds'] = time.monotonic()-started
        save(evidence/'receipt.json',receipt)
    print(json.dumps({'status':receipt['status'],'failure':receipt.get('failure'),'receipt':str(evidence/'receipt.json')}))
    return 0 if receipt['status'] == 'passed-host-only' else 1

if __name__ == '__main__':
    sys.exit(main())
