#!/usr/bin/env python3
"""Pure selected-baseline plus declarative delta; never reads observations."""
import copy,difflib,hashlib,json,pathlib
HERE=pathlib.Path(__file__).resolve().parent
def sha(b):return hashlib.sha256(b).hexdigest()
baseline=(HERE/'component/priv/selected-expected.json').read_bytes();delta=json.loads((HERE/'observer-profile-delta.json').read_bytes())
assert sha(baseline)==delta['baseline_sha256']=='78c0c8a56c6d358eda1e8a183176d5fe7b7e67e9427bdeb4aa1bb308dfaa8e6e'
assert len(delta['operations'])==1
op=delta['operations'][0];assert op['path']==['legacy','database','acl']
old=json.loads(baseline);profile=copy.deepcopy(old);assert profile['legacy']['database']['acl']==op['from']
assert op['to']==op['from'][:-1]+',catalog_inspector_observer=c/andreyyurlov}'
profile['legacy']['database']['acl']=op['to']
encoded=(json.dumps(profile,sort_keys=True,indent=2)+'\n').encode()
(HERE/'component/priv/observer-profile.json').write_bytes(encoded)
(HERE/'observer-profile.diff').write_text(''.join(difflib.unified_diff(baseline.decode().splitlines(True),encoded.decode().splitlines(True),fromfile='selected-baseline',tofile=delta['profile'])))
selection={'schema':1,'profile':delta['profile'],'baseline_sha256':sha(baseline),'profile_sha256':sha(encoded),'delta_sha256':sha((HERE/'observer-profile-delta.json').read_bytes()),'structural_changes':1,'observed_catalog_used':False,'independent_review_accepted':False,'production_provision_accepted':False}
(HERE/'profile-selection.json').write_text(json.dumps(selection,indent=2)+'\n');print(json.dumps(selection,indent=2))
