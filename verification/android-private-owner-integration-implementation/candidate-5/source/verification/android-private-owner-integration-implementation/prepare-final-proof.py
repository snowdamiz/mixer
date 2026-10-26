#!/usr/bin/env python3
"""Prepare an explicit candidate proposal from completed producer evidence; never edits compiled policy."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[2];BASE=Path(__file__).resolve().parent
assert not (BASE/'candidate-4').exists(), 'A frozen candidate is never refreshed'
def ident(data):return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
def save(path,value):path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
profile=json.loads((BASE/'profile-proposal.json').read_text());old=json.loads((BASE/'candidate-3/profile-proposal.json').read_text())
for relative in profile['adapter_files']:
 path=ROOT/'native/android'/('engine/'+relative if relative.startswith('Sources/') else relative);profile['adapter_files'][relative]=ident(path.read_bytes())
for relative,identity in profile['sdk_files'].items():assert ident((ROOT/'sdk'/relative).read_bytes())==identity==old['sdk_files'][relative],relative
def projection(files):return hashlib.sha256(''.join(k+'\0'+v['sha256']+'\n' for k,v in sorted(files.items())).encode()).hexdigest()
profile['adapter_compatibility_sha256']=projection(profile['adapter_files']);assert projection(profile['sdk_files'])==profile['sdk_compatibility_sha256']==old['sdk_compatibility_sha256'];assert profile['wire']==old['wire'] and profile['default_descriptor']==old['default_descriptor'];assert len(profile['adapter_files'])==22 and len(profile['sdk_files'])==22
save(BASE/'profile-proposal.json',profile)
final=BASE/'publication-repair-B-full-1';receipt=json.loads((final/'receipt.json').read_text());assert receipt['status']=='passed-host-only' and receipt['source_stable']
cases=json.loads((final/'barrier-cases.json').read_text());assert cases['baselineSites']==184 and cases['introducedSites']==5 and not cases['missing'] and len(cases['cases'])==1323
clean=[row for row in cases['cases'] if row['case']=='clean'];assert len(clean)==189 and len({row['exactCaller'] for row in clean})==189
proof=json.loads((BASE/'source-and-boundary-proof.json').read_text());proof.update(adapter_projection_sha256=profile['adapter_compatibility_sha256'],sdk_projection_sha256=profile['sdk_compatibility_sha256'],introduced_sites=5,executed_rows=1323,distinct_clean_descriptor_BCI_sites=189,bytecode=ident((final/'bytecode.stdout').read_bytes()),class_map=ident((final/'class-map.json').read_bytes()),profile=ident((BASE/'profile-proposal.json').read_bytes()),helper_boundaries=[row for row in clean if row['boundaryMode']!='direct-platform-call' and row['helperNativeSequence']],owner_bytecode=ident((BASE/'publication-repair-A-3/bytecode.stdout').read_bytes()),final_run='publication-repair-B-full-1')
leaf=json.loads((BASE/'leaf-candidate-3/manifest.json').read_text());assert all(ident((ROOT/k).read_bytes())==v for k,v in leaf['files'].items());proof['leaf3_all74_exact']=True
proof['notes']=list(dict.fromkeys(proof['notes']+["Every ordinary helper entry rejects Mode.CLEANUP before any native leaf; same explicit Mutation passes recursively and synchronous Record.scoped restores in finally.","The fifth introduced Group.onLayout forwarding boundary retains its full native sequence and final section Group layout return anchor; all four changed helper spellings retain original baseline IDs.","Actual owner Work defers a real cancellation token while post is active, clears it before exact old-identity removal/cleanupComplete, and never consumes a newer queued Work.","Final host controls bind the cancellation-only ledger, fresh-focus seal, terminal-continuation and late-post cleanup corrections to these exact source/class bytes. Native-only fixture failure unwind remains crosscompile/source-only.","Successful finish now adopts prepared state with both concrete flags false; publication uses only trusted scalar helpers after actual clean/current core completion, outside commit/finish.","Exact final completionFault and Handler.post controls remain concrete-gate closed across initial/input/refresh, lifecycle dirtiness, retirement, ordinary failure and fatal failure; clean native successors remain positive."]))
save(BASE/'source-and-boundary-proof.json',proof)
history=json.loads((BASE/'freeze-history.json').read_text())
history['candidate-3']='Preserved immutable manifest SHA256 '+ident((BASE/'candidate-3/manifest.json').read_bytes())['sha256']+'. Root HELD after independent targeted-6 demonstrated successful lifecycle-dirty finish opened concrete gates before completion/queued drain. No shared authority reopening claimed.'
history['candidate-4']='Successful finish adopts while closed; trusted scalar publication follows actual clean/current core completion only. Completion hook reentry/fault controls and identical candidate3-before/final-after witness retained. Profile is proposed only; root CLI literals are outside this lane.'
save(BASE/'freeze-history.json',history)
print(json.dumps({'profile':ident((BASE/'profile-proposal.json').read_bytes()),'adapter_projection':profile['adapter_compatibility_sha256'],'SDK_projection':profile['sdk_compatibility_sha256'],'matrix_rows':1323,'sites':189,'helper_boundaries':len(proof['helper_boundaries'])},indent=2))
