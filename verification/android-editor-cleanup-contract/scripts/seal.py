#!/usr/bin/env python3
from pathlib import Path
import datetime, hashlib, json, platform, sys

PACK = Path(__file__).resolve().parents[1]
def meta(path):
    data=path.read_bytes()
    return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}

collection=json.loads((PACK/'collection.json').read_text())
receipt={
    'schema':1,
    'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'scope':'Design and finite host controls only; no selected implementation or native qualification',
    'python':sys.version,
    'platform':platform.platform(),
    'source_tree_digest':collection['source_tree_digest'],
    'source_revision':'Exact bounded source hashes; no Git command used',
    'commands':[
        {'command':'python3 verification/android-editor-cleanup-contract/scripts/collect.py','exit':0,'stdout':'logs/collect.stdout.txt','stderr':'logs/collect.stderr.txt','result':'203 frozen members and bounded live source verified'},
        {'command':'python3 verification/android-editor-cleanup-contract/scripts/transitions.py','exit':0,'stdout':'logs/transitions.stdout.txt','stderr':'logs/transitions.stderr.txt','result':'24 authored transition model tests'},
        {'command':'python3 verification/android-editor-cleanup-contract/scripts/disposal_probe.py','exit':0,'stdout':'logs/disposal-probe.stdout.txt','stderr':'logs/disposal-probe.stderr.txt','result':'2 actual-source failure witnesses,20 candidate host checks; detailed argv/tool versions in disposal-probe.json'},
        {'command':'python3 verification/android-editor-cleanup-contract/scripts/check_packet.py','exit':0,'stdout':'logs/check.stdout.txt','stderr':'logs/check.stderr.txt','result':'24 exact source anchors,12 actual source fragments,10 negative controls rejected'},
    ],
    'prior_failed_attempts':[
        {'command':'java -version via /usr/bin/java','exit':1,'result':'No default Java Runtime; explicit /opt/homebrew/opt/openjdk/bin used thereafter'},
        {'command':'collect.py initial attempt','exit':1,'logs':'logs/collect-attempt-1.stderr.txt','result':'Audit member metadata includes path; collector corrected to compare bytes and sha256'},
        {'command':'disposal_probe.py initial compile','exit':1,'logs':'logs/disposal-attempt-1','result':'Authored Ledger leaf lacked coordinatorFailure; actual extracted production method unchanged'},
    ],
    'evidence_corrections':[
        'renderer cancellation reporting is not coordinator disposal busy; predicate amendment required',
        'initial 15 owner scheduling checks did not protect direct leave disposal; central guard and final20 replace that limited coverage',
        'serialized CREATING supersedes newest nested native creator success',
    ],
    'cleanup':{
        'computer_use_capture_ui_runtime_process_inventory':'not used; paused',
        'native_capture_processes_started':0,
        'host_subprocesses':'subprocess.run reaped every compiler/JVM child',
        'temporary_compiler_directories':'TemporaryDirectory removed after each variant including failure',
        'other_project_processes_data':'not inspected or changed',
    },
    'pending':[
        'Independent review/selection and complete actual adapter/views implementation',
        'Actual complete-source hostile descriptor host tests and SDK cross-compilation',
        'Native TextView/EditorInfo/IME composition,batch,focus,visibility,detach and cleanup when resumed',
        'Guaranteed disposal completion under terminal Handler rejection requires separate owner amendment',
        'Full key transport/arbitrary actions/monitoring/spelling/bounds support with owned continuations',
        'API28–35/public V2 native support,physical qualification,TalkBack,design parity,immutable FieldLog,store/OTA/GA',
    ],
}
(PACK/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
members=[]
for path in sorted(PACK.rglob('*')):
    assert not path.is_symlink(),path
    if path.is_file() and path.name!='seal.json':
        members.append({'path':str(path.relative_to(PACK)),**meta(path)})
seal={'schema':1,'scope':receipt['scope'],'source_tree_digest':collection['source_tree_digest'],
      'members':members,'exclusions':['seal.json (self)']}
(PACK/'seal.json').write_text(json.dumps(seal,indent=2)+'\n')
print(json.dumps({'members':len(members),'seal':meta(PACK/'seal.json'),'scope':receipt['scope']}))
