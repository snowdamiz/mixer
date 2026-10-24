#!/usr/bin/env python3
"""Freeze observations after both source-bound collectors complete."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
def read(name): return json.loads((OUT/name).read_text())
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
mac=read('macos-execution.json')
linux=read('linux-execution.json')
assert mac['inputsUnchanged'] and not mac['newTLSKeyDirectoriesRetained']
assert all(command['exitCode']==0 for command in mac['commands'])
assert linux['exitCode']==0 and linux['prodExitCode']==0
assert read('linux-cleanup.json')=={'scratchRemoved':True,'container':'mixer-key-owner-linux-tests','containerRetained':False}
source=read('source-manifest.json')['files']
linux_source=read('linux-source-manifest.json')['files']
assert all(sha(ROOT/path)==digest and linux_source[path]==digest for path,digest in source.items())
pure=json.loads((ROOT/'verification/hosted-token-verifier/source-manifest.json').read_text())['files']
assert all(sha(ROOT/item['path'])==item['sha256'] for item in pure)
for name,count in [('macos-tests-final.log',45),('linux-tests.log',46)]:
    assert f'Result: {count} passed' in (OUT/name).read_text()
assert read('production-DNS-rebinding.json') if (OUT/'production-DNS-rebinding.json').exists() else True
bindings=dict(source)
for path in [ROOT/'docs/hosted-key-owner-implementation.md',ROOT/'verification/hosted-key-owner-root-review/selection.json',ROOT/'verification/hosted-key-owner-root-review/profile-history-selection.json']:
    bindings[str(path.relative_to(ROOT))]=sha(path)
for path in sorted(OUT.rglob('*')):
    if path.is_file() and path.name!='receipt.json' and '__pycache__' not in path.parts:
        bindings[str(path.relative_to(ROOT))]=sha(path)
rows={
'K01':'whole-manifest/profile/key limits; atomic policy/version checks; lifetime16-ID history across cooldown expiry; retired/re-enable version increase; no partial seventeenth-ID churn; measured/derived metadata bounds',
'K02':'actual IP-pinned TLS Host/path/SNI/peer; CA/hostname/expired/future/bad-signature chain/plaintext/TLS1.1 rejection; IPv6 peer',
'K03':'actual UDP DNS unsafe/mixed/mapped/ULA/CNAME/overflow/truncation/delay; production classifier+transport public-peer rebinding with forbidden sink0 in isolated Linux namespace',
'K04':'actual301/302/307/308/304/206/401/429/500, huge error bodies, separate redirect sink0, fixed no-auth/no-cookie headers',
'K05':'four full256KiB Content-Length/chunked transport successes and full owner validation/publication/JOSE/fence; oversize, chunk/header/trailer/framing/compression/information/Unicode-OWS rejection; four8MiB500 and suspended consumers resource samples',
'K06':'paired-clock freshness Date/Age/max-age/s-maxage/Expires, shorter expiry, invalid/zero/no-store/no-cache/future metadata; validation/publication consumes original expiry',
'K07':'actual DNS/handshake/status/header/body/drip total deadlines, pre-mailbox queue time, caller death, raw-port/controller/worker DOWN, held-controller slot retention, owner shutdown/crash/restart cleanup',
'K08':'100-call single-flight;16/profile128/process pre-mailbox admission; eight profiles <=four flights;128 FIFO negative entries, hit non-renewal; no known-signature refresh; cooldown survives failed fetch/remove/re-add',
'K09':'real signed tokens and actual HTTPS overlapping rotation then old-key removal; lease fence and negative reset; invalid candidate retains original snapshot/deadlines',
'K10':'serialized profile/disable/removal/snapshot/clock epoch fences; reviewed manifest generation survives clock fault; lifetime identity history survives clock/reap',
'K11':'production constructor rejects fixture options/missing roots; packaged Linux release excludes fixture functions; explicit startup only; recorded versions/source/cleanup; no provider/deployment/GA acceptance'}
receipt={
'schema':1,'status':'implemented-component-ready-for-independent-root-review-not-product-or-GA-acceptance',
'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
'sourceRevision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
'sourceTreeDigest':hashlib.sha256(json.dumps(source,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
'acceptedPureVerifierUnchanged':True,
'contractSupplement':'verification/hosted-key-owner-root-review/profile-history-selection.json',
'hostEvidence':{'macOS':'45 explicit identity tests passed; format; production compile/fixture-export exclusion','Linux':'46 identity tests passed including isolated production DNS/rebinding; production release built without starting; fixture exports absent','image':linux['image'],'network':'none; NET_ADMIN only for disposable namespace lo:1 fixture','OTP':'29.1.1','ssl':'11.7.7','Elixir':'1.20.4'},
'matrix':{key:{'status':'component-exercised','observations':value} for key,value in rows.items()},
'resourceEvidence':['transport-metrics.json','chunked-TLS-resources.json','hostile-fast-TLS-resources.json','suspended-consumer-TLS-resources.json','owner-four-full-candidate-publication.json','handshake-cleanup.json','crash-restart-cleanup.json','history-metadata-size.json','linux-production-DNS-rebinding.json'],
'limitations':[
'Component is not wired to Application or an authenticated HTTP route; existing API remains health-only. No provider, membership/database authorization or release execution.',
'Process-lifetime identity history is bounded16 IDs and rejects further churn. Durable historical identity/version enforcement across owner/component restart is pending authoritative provisioning/DB work.',
'Observed memory samples and driver-buffer checks are not universal RSS, kernel-buffer, hard process-memory or hard real-time bounds. Application payload/parser/header/admission/flight limits are enforced.',
'Large close-delimited bodies use exact one-byte reads and can exhaust the fixed deadline; no deadline relaxation or stale fallback.',
'Graceful stop/restart remains pending while an owned TLS controller is held. Container/SIGKILL termination is outside this graceful process-cleanup guarantee.',
'Cooldown/clock race tests explicitly move private owner timing state rather than changing system clocks or waiting30 seconds; actual socket/deadline/DNS tests use real platform behavior.',
'Provider issuance/rotation/cache semantics, fleet quotas/egress/clock behavior, Cloudflare/Neon, external FieldLog, independent security acceptance and GA remain pending.',
'No native simulator/emulator, physical phone, screen capture, production publish, customer message, schema migration or credential change occurred.'],
'producerCorrections':['passive0/active-once batch assumptions disproved','4MiB TLS-buffer hypothesis failed before scoped cb_info flow control','buffer-only activation preservation fixed','normal and shutdown controller-DOWN accounting corrected','clock epoch separated from reviewed configuration generation','expired-tombstone identity-history gap corrected under root supplement','HTTP metadata trimming narrowed to ASCII SP/HTAB','ephemeral TLS fixture directories use exclusive128-bit random names and0700 permissions'],
'bindings':bindings}
(OUT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'status':receipt['status'],'sourceTreeDigest':receipt['sourceTreeDigest'],'bindings':len(bindings)}))
