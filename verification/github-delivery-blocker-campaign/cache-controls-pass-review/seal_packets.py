#!/usr/bin/env python3
"""Seal only these two owned offline evidence review packets."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

BASE = Path(__file__).resolve().parent
REPO = BASE.parents[2]
SHA = 'cc350d3303ca71c5d57e87846f6a61304b658fa7'

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def load(path): return json.loads(path.read_bytes())
def put(path, value):
    with path.open('x') as out: out.write(json.dumps(value,sort_keys=True,indent=2)+'\n')

protected={'.github/workflows/hosted.yml':'fafd2560cc385a4113ea140bf2d4445d456e1f7f396539dfe2c3e7d6302e8b57',
           'hosted/lib/mixer_hosted/browser_auth/store.ex':'8c314b1d3ce288a6dc617251233796bd0a9d8894247ccb15b101e1292e513299'}
assert all(sha(REPO/path)==expected for path,expected in protected.items())
for name in ['cache-controls-pass-review','phoenix-pass-review']:
    packet=BASE.parent/name
    command=load(packet/'review.command.json')
    assert command['exit_code']==0 and command['script_sha256']==sha(packet/'review.py')
    assert command['stdout_sha256']==sha(packet/'review.stdout') and command['stderr_sha256']==sha(packet/'review.stderr')
    review=load(packet/'review.json');archive=load(packet/'zip-manifest.json');acq=load(packet/'acquisition.json')
    assert review['source_revision']==SHA and acq['head_sha']==SHA
    if name=='cache-controls-pass-review':
        assert review['runner_controls_passed']==32 and review['actual_fixture_commands']==103
        assert not review['original_flaky_primary_failure_cause_resolved']
        report=f'''Accepted current cache-control and finite host-fixture CI evidence for
run 40740023152, job 122998786883 at `{SHA}`.

The raw focused output reports 32 tests, all passing, in 2.389 seconds. The
current retained descendant timeout control records child return, owned group
killed and gone, no cleanup errors and no custody hold. The expected timeout
RuntimeError and its command/output evidence are retained. This current pass
does not identify or resolve the earlier unknown primary cleanup exception.
`Commands.stop` and the active/cleanup/child/output limits match the failed
commit; the delivered correction retains diagnostics and conservative custody.

The separate current `runs/ci-40740023152-1/receipt.json` matches the exact commit
and tree, records 103 completed commands, all command JSON/output hashes, and
all nine postflight checks. Debug and optimized outputs each contain the exact
94 controls, 84 host, 98 independent and 108 producer methods, with complete
disjoint coverage. Each mode records 31 actual File cases and 23 layouts per
host/control family. All 25 API probes per mode have their expected disposition:
23 compile rejections and two successful probes; the latter execute. Current
receipt cleanup reports all owned groups returned and scratch removed after
916 files were hashed. The 86-member closed source pack and both runner sources
match exact committed bytes. Rust is 1.98.1 on aarch64-apple-darwin.

Artifact 12839930376 is 2,525,332 bytes, SHA-256
`f3eb25955c8dd0bab96d62486c904cdda6cc531f14741dd32ab9367cb16426cf`.
All 1,385 entries were streamed for CRC, byte counts and SHA-256 under an 8 MiB
ZIP / 128 MiB expanded cap; actual expansion is 83,249,523 bytes. Only selected
evidence was extracted. The initial acquisition default mentioned a 64 MiB
expanded cap; inventory showed current plus historical data before streaming,
so the review selected the allowed 128 MiB cap and recorded it in the archive
manifest. The copied October 27 `host-resource-ci-repair-root-1` receipt is
historical and is excluded from current acceptance.

The original full Debug timeout remains failed. Semantic metrics, stored-prefix
validation, replay, performance equivalence and GA flags remain false. This
accepts only the observed finite remote host run. It clears no local custody,
native/runtime, phone, guest, stopped Android v5, compiler, release or GA hold.
No artifact code, test, compiler, native/UI/capture, database/container or product
runtime was executed by this reviewer. No process inventory, retry, dispatch,
commit, push or canonical metadata mutation occurred. Reviewer parser assertion
corrections are retained under review-attempt-1 and review-attempt-2; they are
not CI test failures. Signed download URLs were neither printed nor persisted.
'''
    else:
        runtime=load(packet/'runtime-evidence.json');sources=load(packet/'source-bindings.json');sparse=load(packet/'sparse-readset.json');nested=load(packet/'source-archive-manifest.json');timing=load(packet/'timing.json')
        assert len(runtime['lifecycle_completed_methods'])==9 and len(runtime['http2_completed_methods'])==5
        assert len(runtime['http2_wire_cases'])==7 and len(runtime['K07_f_g_h_completed'])==3
        assert len(runtime['skipped_methods'])==2 and sparse['selected_files']==194
        assert archive['expanded_bytes']+nested['expanded_bytes'] <= 64*1024*1024
        assert sources['frozen_product_177_sha256']=='023df04c9a4599c3d5a6cdf2afb53a95e2faf37765d8b96ba2bcc0e1b007c92e'
        report=f'''Accepted ordinary Phoenix host CI evidence for run 40740023060,
job 122998786324 at `{SHA}`. All 13 recorded steps succeeded.

Artifact 12837969735 is 868,414 bytes, SHA-256
`9585303f3e0391724ad434f4dde5e3fce89f194fd37ef0fb50bc07b0cb927627`.
All 150 ZIP entries (1,538,815 expanded bytes) passed bounded path/type,
duplicate, encryption, CRC, size and SHA-256 checks. The nested source archive
contains exactly the 181 receipt inputs; every byte/hash map matches exact
committed blobs. Combined expansion is {archive['expanded_bytes']+nested['expanded_bytes']:,} bytes under 64 MiB.
The precise frozen 177 path-to-byte/hash rows equal their contract and digest
`023df04c9a4599c3d5a6cdf2afb53a95e2faf37765d8b96ba2bcc0e1b007c92e`.
The additional four foundation inputs are the two network collector scripts
and two protocol golden JSON fixtures. A reviewer-only membership/digest-format
assertion was corrected and preserved under review-attempt-1; no product drift
was observed.

Raw ExUnit output reports 697 passed, two skipped and zero failures in 127.4
seconds. Protocol reports 45 passed, storage 24 passed and migration one passed.
All nine KeyOwner lifecycle methods, K07f/g/h and all five HTTP/2 methods
complete. Seven HTTP/2 wire receipts (B1, B2, B3, D1/D2 SETTINGS and WINDOW_UPDATE)
record passed=true and complete cleanup. Lifecycle cleanup errors are empty;
branch-specific observations retain their actual false values. The production
release exclusion checks pass. Five accepted handshake connections are closed;
the four-slot cleanup/reuse and crash-restart observations remain scoped to the
named fixtures. Every foundation command log and migration output hash matches.
Only the expected release-missing-config command exits 1.

The committed hosted workflow SHA-256 is
`cc0890f161e03fddc6fcf7435b125412fd26d11fad0dfdb297c3b9df83e31031`, unchanged
from the previous accepted sparse workflow. Sixteen non-cone patterns cover
exactly the required 194-file ordinary readset ({sparse['selected_logical_bytes']:,} logical bytes).
The log records blob:none fetch, sparse activation and exact commit checkout.
Exactly four current receipts are uploaded; no copied historical attempt receipt
is accepted. Checkout to next action is {timing['checkout_action_upper_bound_seconds']} seconds (an observed upper
bound); foundation step to emitted receipt is {timing['foundation_step_observed_seconds']} seconds. These are
single-run observations with no future timing, byte-transfer or cost guarantee.

Foundation records PostgreSQL stopped and owned scratch removed; protocol,
storage and migration record their own cleanup. Nine lifecycle observations and
seven HTTP/2 receipts establish their named resource cleanup. Runner logs its
orphan-cleanup phase with no orphan termination event. This is scoped evidence,
not a universal process inventory.

K03 production public-peer DNS pinning under rebinding and IS04/IS05 configured
startup public-DNS/TLS lifecycle remain skipped and pending. No configured
provider, Neon, Cloudflare, deployment, held UnitA/frozen workflow, native/phone,
customer, store or GA acceptance follows. This review uses committed workflow
bytes; the held live hosted workflow and store were only hashed to confirm
preservation. Any inherited wording in review.json saying the live workflow was
not read means it was not used as source; these byte-preservation hashes were
read. No artifact code, tests, compiler, product/native/UI/capture runtime,
database/container, process inventory, CI retry/dispatch, commit/push or canonical
metadata mutation occurred. All holds remain. Signed URLs were not retained.
'''
    with (packet/'report.md').open('x') as out:out.write(report)
    put(packet/'scope-addendum.json',{'schema':1,'protected_live_sha256_after':protected,'protected_live_matches_supplied_before_pins':True,'live_dirty_files_used_as_committed_source':False,'source_input':'exact committed Git blobs and integrity-checked remote artifact bytes','reviewer_child_processes':'finite read-only Git and Python archive/source/log review; all exited','reviewer_product_test_compiler_native_UI_capture_Docker_Postgres_guest_phone_processes_started':False,'download_child_started':False,'download_cleanup':'Fetch bodies fully consumed, timers cleared; no download child, native instance or scratch process created. Evidence files intentionally retained.','all_local_custody_and_native_runtime_holds_preserved':True,'signed_download_URL_printed_or_persisted':False,'initial_acquisition_submission':'Combined logs+metadata submission rejected before execution by 64000-byte tool-argument limit; split into bounded per-packet calls without changing scope.','archive_inspector':{'path':str(BASE/'inspect_archives.py'),'sha256':sha(BASE/'inspect_archives.py')},'note':'Reports and this addendum govern current scope wording; archived reviewer assertion corrections are not CI failures.'})
    files={}
    for path in sorted(packet.rglob('*')):
        assert not path.is_symlink()
        if path.is_file():files[str(path.relative_to(packet))]={'bytes':path.stat().st_size,'sha256':sha(path)}
    put(packet/'packet-manifest.json',{'schema':1,'source_revision':SHA,'files':files,'tree_digest_sha256':hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest()})
    put(packet/'receipt.json',{'schema':1,'sealed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'sealed-accepted-current-CI-evidence-with-explicit-limits','source_revision':SHA,'source_tree':review['source_tree'],'run_id':review['run_id'],'job_id':review['job_id'],'artifact_id':review['artifact_id'],'packet_manifest_sha256':sha(packet/'packet-manifest.json'),'files_in_manifest':len(files),'command':[sys.executable,'-B',str(BASE/'seal_packets.py')],'python':sys.version,'git_version':subprocess.run(['git','--version'],capture_output=True,check=True,timeout=5).stdout.decode().strip(),'seal_script_sha256':sha(BASE/'seal_packets.py'),'artifact_code_executed':False,'no_original_unknown_failure_cause_resolution_claim':True,'all_native_runtime_and_local_custody_holds_preserved':True})
    print(json.dumps({'packet':name,'files':len(files),'manifest_sha256':sha(packet/'packet-manifest.json'),'status':'sealed-accepted-current-CI-evidence-with-explicit-limits'},sort_keys=True))
