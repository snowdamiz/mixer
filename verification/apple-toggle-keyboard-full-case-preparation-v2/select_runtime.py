#!/usr/bin/env python3
"""Preparation-only closed source selection; never run by verify or runtime."""
import hashlib,json,pathlib
BASE=pathlib.Path(__file__).resolve().parent
assert not (BASE/'packet-seal.json').exists()
paths=[BASE/name for name in ['composition.py','attachment_export.py','runtime_summary.py','orchestration.py','runtime_bindings.py']]+[p for p in (BASE/'inputs/runtime').rglob('*') if p.is_file()]
files={str(p.relative_to(BASE)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}
s='inputs/runtime/verification/'
aliases={'composition':'composition.py','attachment_export':'attachment_export.py','runtime_summary':'runtime_summary.py','orchestration':'orchestration.py','runtime_bindings':'runtime_bindings.py','_selected_runtime_bindings':'runtime_bindings.py',
'harness':s+'apple-toggle-pan-origin-correction/harness.py','apps':s+'apple-toggle-pan-origin-correction/apps.py','bridge':s+'apple-toggle-pan-origin-correction/bridge.py','oracle':s+'apple-toggle-pan-origin-correction/oracle.py',
'keyboard_oracle':s+'apple-toggle-keyboard-focus-v9-preparation/keyboard_oracle.py','keyboard_bridge':s+'apple-toggle-keyboard-focus/keyboard_bridge.py','settings_telemetry':s+'apple-toggle-keyboard-focus-v9-preparation/settings_telemetry.py','durable_settings':s+'apple-toggle-keyboard-focus-v9-preparation/durable_settings.py',
'immutable_keyboard_v1_oracle':s+'apple-toggle-keyboard-focus/keyboard_oracle.py','reviewed_pan_state':s+'apple-toggle-pan-commit-harness-v2/commit_oracle.py','pan_commit_original_oracle':s+'apple-toggle-pan-origin-correction/oracle.py','pan_commit_interruption_oracle':s+'apple-toggle-native-interruption/interruption_oracle.py','pan_commit_semantic_oracle':s+'apple-toggle-semantic-activation/semantic_oracle.py','original_geometry':s+'apple-toggle-pan-origin-correction/oracle.py','mixer_frozen_toggle_handoff':s+'apple-toggle-native-failure-analysis/packet.py',
'full_case_reviewed_reader':s+'apple-toggle-pan-commit-harness-v2/observation_reader.py','reviewed_keyboard_reader':s+'apple-toggle-pan-commit-harness-v2/observation_reader.py'}
case_data={'keyboard_oracle':s+'apple-toggle-keyboard-focus/cases.json','immutable_keyboard_v1_oracle':s+'apple-toggle-keyboard-focus/cases.json','reviewed_pan_state':s+'apple-toggle-pan-commit-harness-v2/cases.json','pan_commit_interruption_oracle':s+'apple-toggle-native-interruption/cases.json'}
(BASE/'runtime-selection.json').write_text(json.dumps(dict(schema=1,files=files,moduleAliases=aliases,caseDataAliases=case_data,scope='Selected closed runtime sources/data only; no historical evidence rescan'),sort_keys=True,indent=2)+'\n')
print(json.dumps(dict(selectedFiles=len(files),sourceFiles=sum(name.endswith('.py') for name in files),dataFiles=sum(not name.endswith('.py') for name in files))))
