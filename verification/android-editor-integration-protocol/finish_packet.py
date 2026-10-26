#!/usr/bin/env python3
"""Record concrete source findings and seal this owned preparation directory."""
import datetime
import hashlib
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent
def ident(data): return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
def save(path, value): path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
def main():
    patterns = {
        'inputs/repo/cli/Sources/MixerBuild/AndroidSDKCompatibility.swift': ['mixer.android-source-pair.4', 'Selected frozen 22 + 23', 'static func require(', 'static func admitInput', 'static func admitProject'],
        'inputs/repo/cli/Sources/MixerBuild/Resources/android-build.py': ["value['id'] != 'mixer.android-source-pair.4'", "(('sdk', 22), ('adapter', 23))", 'def source_profile', 'def profile_required', 'def admit_source_pair', "sources = sorted((adapter / 'app/src')"],
        'inputs/repo/cli/Sources/MixerBuild/AndroidProject.swift': ['static func snapshot', 'profile.adapter_files.keys.sorted()', 'public static func build'],
        'inputs/released-correction/source/NativeEnvironmentV2.java': ['Build.VERSION.SDK_INT < 36'],
        'inputs/released-correction/source/NativeRenderer.java': ['if(Build.VERSION.SDK_INT<36)', 'boolean editorDisposalBusyV2()', 'public long editorLossObservation()', 'public void editorLossObserved(', 'public void fieldPreservationBegin(', 'public void fieldPreservationEnd(', 'public void replacementEvent('],
        'inputs/released-correction/source/NativeAppearanceViewsV2.java': ['long editorLossObservation();', 'void editorLossObserved(Record record);', 'void fieldPreservationBegin(Record record,FieldPreservation preservation);', 'void fieldPreservationEnd(Record record,FieldPreservation preservation);', 'void replacementEvent(Record record,Replacement replacement);', 'eventEvaluating', '!record.changing'],
        'inputs/historical-preparation/closure-B-directprobe/inputs/tests/NativeOwnerV2ConcreteHostTests.java': ['record.changing=!state.equals("successor")', 'IME exact current', 'sendKeyEvent(new KeyEvent'],
        'inputs/historical-preparation/closure-B-directprobe/inputs/leaves/android/widget/EditText.java': ['selectionStart=selectionEnd=0'],
        'inputs/historical-preparation/closure-B-directprobe/inputs/leaves/android/widget/TextView.java': ['selectionStart=selectionEnd=replaceIdentity?0', 'for(TextWatcher watcher:List.copyOf(watchers))watcher.afterTextChanged(text);'],
    }
    findings = []
    for relative, needles in patterns.items():
        data = (HERE / relative).read_bytes()
        lines = data.decode().splitlines()
        for needle in needles:
            matches = [{'line': i + 1, 'text': line} for i, line in enumerate(lines) if needle in line]
            if not matches: raise RuntimeError('Missing actual source finding: ' + relative + ' ' + needle)
            findings.append({'input': relative, 'identity': ident(data), 'needle': needle, 'matches': matches,
                'scope': 'source location only; not behavior, compiled-boundary completeness or release authority'})
    save(HERE / 'source-findings.json', findings)
    save(HERE / 'delivery-receipt.json', {'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'source_revision_at_initial_freeze': json.loads((HERE / 'freeze-receipt.json').read_text())['commands'][0]['stdout'],
        'scope': 'root coordination proposal and executable migration support; no canonical integration selection',
        'authored_outputs': ['integration-contract.md', 'test-migration.md', 'compiled-boundary-qualification.md', 'family-migration.json', 'source-lists.json', 'proposed-profile5.json', 'check_protocol.py', 'MigrationSupportControls.java'],
        'results': {'copied_input_integrity': 'passed 602 copied inputs', 'historical_host_support': '9 controls / 61 assertions',
            'family_design': '16 families x 6 states = 96 design rows; not passing corrected-source cases',
            'actual_frozen_profile4_driver_refusals': 5, 'synthetic_map_integrity_refusals': 13,
            'released_correction_source_binding': '16 source members checked; root acceptance pending'},
        'not_run': ['corrected-source host integration', 'all-family migrated state suite', 'fresh exact compiled callback matrix',
            'exact SDK37 38-descriptor audit for selected integration', 'fresh CLI Debug/Release and generated consumers',
            'new Java/SDK37/D8/Swift/JNI cross-compilation', 'simulator/emulator/physical/native/UI/capture', 'public V2/FieldLog/store/OTA/GA'],
        'git_mutations': False, 'canonical_or_other_lane_mutations': False,
        'cleanup': {'support_scratch_removed': True, 'all_owned_host_children_reaped': True,
            'native_ui_capture_processes_queried_or_started': False, 'other_projects_processes_touched': False},
        'retained_authoring_failures': ['authoring-failures/freeze-attempt1.json', 'authoring-failures/support-controls-attempt1'],
        'root_decisions_required': ['independent corrected-source acceptance', 'select exact integration/profile5 and no-new-leaf test migration', 'select fresh compiled-boundary qualification roster before execution']})
    members = []
    for path in sorted(HERE.rglob('*')):
        if not path.is_file() or path.name == 'seal.json' and path.parent == HERE: continue
        members.append({'path': path.relative_to(HERE).as_posix(), **ident(path.read_bytes())})
    save(HERE / 'seal.json', {'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'scope': 'Frozen unselected integration protocol; historical host support and released-correction source binding only; no canonical/native/release acceptance',
        'root_acceptance': None, 'members': members})
    print('PASS protocol frozen:', len(members), 'members; seal SHA256', ident((HERE / 'seal.json').read_bytes())['sha256'])
if __name__ == '__main__': main()
