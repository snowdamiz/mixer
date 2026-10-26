#!/usr/bin/env python3
"""Fresh positive, path-binding and unsupported-policy probes in both Python modes."""
import importlib.util
import json
from pathlib import Path
import sys
from unittest import mock

root=Path(sys.argv[1]);path=root/'Generated/MixerAndroid/android-build.py'
spec=importlib.util.spec_from_file_location('fresh_review_driver',path)
driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver)
profile=driver.source_profile()
if driver.admit_source_pair(root,profile)!=(root/'Generated/MixerAndroid/app/assets/MixerAppearanceV2/descriptor.json').read_bytes():
    raise RuntimeError('positive descriptor admission')
tests=[]
for field,value in [('id','mixer.android-source-pair.2'),('schema',True)]:
    changed=json.loads(json.dumps(profile));changed[field]=value
    with mock.patch.object(driver,'SOURCE_PROFILE_HEX',json.dumps(changed).encode().hex()), \
         mock.patch.object(driver,'read_json',side_effect=RuntimeError('LOCK-READ-TOO-EARLY')):
        try:driver.build(root/'absent')
        except RuntimeError as error:
            if 'not rendered or supported' not in str(error):raise
        else:raise RuntimeError('unsupported policy passed')
    tests.append(field+'-pre-lock-refusal')
print(json.dumps({'methods':1,'positive_admission':True,'unsupported_policy_cases':tests,'optimized':not __debug__}))
