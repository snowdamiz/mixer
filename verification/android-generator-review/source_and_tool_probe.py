#!/usr/bin/env python3
"""Independent source-lock and complete synthetic tool-tree closure checks."""
import hashlib
import json
import pathlib
import runpy

OUT=pathlib.Path(__file__).resolve().parent
ROOT=OUT.parents[1]
module=runpy.run_path(str(OUT/'.local/source/cli/Sources/MixerBuild/Resources/android-build.py'))
base=OUT/'.local/tool-closure';base.mkdir()
distribution=base/'distribution';distribution.mkdir();real=distribution/'real';real.mkdir()
file=real/'tool';file.write_text('first')
(distribution/'internal').symlink_to(real,target_is_directory=True)
first=module['tree'](distribution);file.write_text('second');second=module['tree'](distribution)
assert first!=second
external=base/'external-file';external.write_text('A');(distribution/'file-link').symlink_to(external)
third=module['tree'](distribution);external.write_text('B');fourth=module['tree'](distribution)
assert third!=fourth
outside=base/'outside';outside.mkdir();link=distribution/'dir-link';link.symlink_to(outside,target_is_directory=True)
try:module['tree'](distribution);raise AssertionError('Directory escape accepted')
except RuntimeError as error:assert 'symlink escapes hashed root' in str(error)
link.unlink();(distribution/'dangling').symlink_to(base/'absent')
try:module['tree'](distribution);raise AssertionError('Dangling link accepted')
except FileNotFoundError:pass
receipt=json.loads((OUT/'.local/audited-evidence/verification/android-generated-consumer/build-receipt.json').read_text())
app=pathlib.Path(receipt['apk']).parents[2]
observed={
    'actual_app_tree':module['source_tree'](app),
    'actual_sdk_tree':module['source_tree'](app/'Generated/MixerSDK'),
    'actual_adapter_tree':module['source_tree'](app/'Generated/MixerAndroid'),
}
assert observed['actual_app_tree']==receipt['source_tree_sha256']==receipt['source_tree_after_sha256']
assert observed['actual_sdk_tree']==receipt['sdk_digest']
assert observed['actual_adapter_tree']==receipt['adapter_digest']
source=json.loads((OUT/'.local/audited-evidence/verification/android-generated-consumer/receipt.json').read_text())
for path,digest in source['user_owned_files_preserved'].items():assert hashlib.sha256((app/path).read_bytes()).hexdigest()==digest
result={'source_revision':json.loads((OUT/'freeze.json').read_text())['revision'],'synthetic_tool_tree':{'internal_directory_link_content_covered':True,'external_file_link_target_bytes_covered':True,'external_directory_link_rejected':True,'dangling_link_rejected':True},'actual_built_app_source_matches_receipt':observed,'actual_user_owned_files_hashes_preserved':source['user_owned_files_preserved'],'scope':'Read-only audit of same exact app and committed build evidence; complete before/after sandbox isolation is not claimed.'}
(OUT/'source-and-tool-probe.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
