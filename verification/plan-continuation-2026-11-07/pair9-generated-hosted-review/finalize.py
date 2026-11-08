#!/usr/bin/env python3
"""Seal this review only. Requires successful fresh data audits; no product execution."""
import hashlib,json,sys
from pathlib import Path
from datetime import datetime,timezone
OUT=Path(__file__).resolve().parent

def ident(p):
    data=p.read_bytes()
    return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}

def load(p):return json.loads((OUT/p).read_bytes())
def write(p,d):(OUT/p).write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
a=load('audit.json');s=load('supplemental.json');f=a['facts'];ac=f['acquisition']
assert a['verdict']==s['verdict']=='ACCEPT'
assert ident(OUT/'audit.py')==a['audit_script'] and ident(OUT/'supplemental.py')==s['script']
assert s['audit']==ident(OUT/'audit.json')
assert all(x['passed'] for x in a['checks']+s['checks'])
consumers=f['consumers'];one=next(iter(consumers.values()))
result={'schema':1,'verdict':'ACCEPT','blocking_findings':[],
 'scope':'Completed exact96f hosted pair9 R2 Java17/D8 bootstrap, six original/relocated/exported Debug/Release CLI closures and 24 tamper invocations only.',
 'reviewed_revision':f['source_revision'],'reviewed_git_tree':f['git_tree'],
 'run':ac['run'],'attempt':ac['attempt'],'job':ac['job'],'artifact':ac['artifact'],'job_url':ac['job_url'],
 'archive':ac['archive'],'artifact_files':ac['file_count'],'artifact_bytes':ac['extracted_bytes'],'artifact_inventory_projection_sha256':ac['inventory_sha256'],
 'source_count':len(f['source_inputs']),'source_digest':f['source_inputs_sha256'],
 'sdk':{'count':22,'sha256':'bc03288599ece5612cc4dce8b80fc404942584e0477ec9333bd39c0fa7d352d0'},
 'adapter':{'count':24,'sha256':'ee9414d3b68f9d66ba275c93339018e5eaebb161a7dc25d7056538c652305d89'},
 'consumers':6,'java_sources_per_consumer':18,'classfiles_per_consumer':one['class_count'],
 'member_references_per_consumer':one['member_count'],'binary_member_references_compared_total':sum(v['member_count'] for v in consumers.values()),
 'dex_definitions_per_consumer':one['dex_class_count'],'class_inventory_sha256':one['class_inventory_sha256'],'consumer_inventory_sha256':one['consumer_inventory_sha256'],'dex':one['dex'],
 'bootstrap_commands':13,'integration_commands':79,'tamper_cases':12,'tamper_invocations':24,
 'policy_controls':{'bootstrap':28,'sparse_checkout':12},'all_seven_jobs_successful':'Captured metadata only; this review qualifies the generated-Java artifact only.',
 'checks':{'main':len(a['checks']),'supplemental':len(s['checks']),'total':len(a['checks'])+len(s['checks'])},
 'audit':ident(OUT/'audit.json'),'supplemental':ident(OUT/'supplemental.json'),'audit_script':ident(OUT/'audit.py'),'supplemental_script':ident(OUT/'supplemental.py'),
 'observed_budgets':{'bootstrap_command_span_seconds':f['bootstrap']['elapsed_seconds'],'bootstrap_output_bytes':f['bootstrap']['aggregate_output_bytes'],'integration_command_span_seconds':f['run_elapsed_seconds'],'integration_output_bytes':f['aggregate_output_bytes'],'admitted_free_bytes':146460831744,'minimum_free_bytes':12884901888,'producer_jobs':2},
 'limitations':a['limitations']+['All92 outer command records separately cover direct-child reap, stdout/stderr EOF, owned-group absence and terminal custody. Nested version/compiler processes rely on outer group records and frozen runner, not independent per-grandchild receipts.','Member coverage is constant-pool Fieldref/Methodref/InterfaceMethodref, including unused entries; dynamic/reflection targets and post-D8 rewriting are unqualified.','Official Swift package trust is the retained successful macOS pkgutil report; this review performs no new signature, certificate or revocation verification.','The bootstrap system-tool hashes are initial historical observations, not separately rehashed system-tool postflight receipts. The canonical five-distribution inspection, javap, source and Apple metadata have frozen-code postflight enforcement.'],
 'reader_closure':s['own_reader_closure'],'custody_scope':s['custody_scope'],
 'nonblocking_notes':s['nonblocking_notes']+['initial-audit-result.json preserves the adapted-audit stale pair8 expected-hash failure and its correction; it is not a hosted product failure.'],
 'not_granted':['API28 floor or linkage','runtime','APK','physical devices','application signing','immutable published package','FieldLog release','GA','new product-semantic qualification'],
 'prior_evidence_and_holds':'Prior pair8/signatureR2/localpair9R2/failedCI review evidence unchanged. Held PGIDs23663,20745,20770,20780,20817,20842,20851,20866 and FieldLog40802230894/PGID2424/PID2621 not probed or signalled; v5/frozen lanes/physical-phone holds preserved.',
 'execution':{'python':a['python'],'git':f['git_version'],'network':0,'product_code_execution':0,'compiler_jvm_swift_d8_native_ui_capture':0,'process_probes_or_signals':0,'child_agents':0,'commits':0,'pushes':0,'writes_only':str(OUT)},
 'reproduce':['python3 -B '+str(OUT/'audit.py'),'python3 -B '+str(OUT/'supplemental.py'),'python3 -B '+str(OUT/'finalize.py')],
 'required_inputs':['/tmp/mixer-ci96-generated-java.zip','verification/plan-continuation-2026-11-07/ci96-generated-java-actual/{acquisition.json,artifact-list.json,jobs.json,job.log,artifact/}','Git96f03ab65966a6374e958e780fa09a3eed814c0b source objects; Git25ac442c5213326b3601456a5fd62898f152111f only for owner diff','Prior review/failure directories named by audit.py, for unchanged-evidence checks'],
 'finished_utc':datetime.now(timezone.utc).isoformat()}
write('result.json',result)
report=f'''ACCEPT — no blocking findings for the completed hosted pair9 R2 Java17/D8 bootstrap and consumer evidence at `{result['reviewed_revision']}` (Git tree `{result['reviewed_git_tree']}`). This is an independent data review of this run; earlier pair8 acceptance is not inherited.

Exact captured identity: [run {ac['run']}, attempt {ac['attempt']}, job {ac['job']}]({ac['job_url']}); artifact **{ac['artifact']}**. Acquisition, GitHub metadata, job logs and upload metadata agree. All seven jobs are successful in captured metadata; only this generated-Java artifact is qualified here. ZIP **14,405,711 bytes**, SHA-256 `{ac['archive']['sha256']}`. Every ZIP entry passed read/CRC, unique safe-path and nonsymlink checks, and matches the extracted bytes and acquisition hashes: **1,532 files / 115,803,865 bytes**. Full capture/ZIP identities remained unchanged through audit; the supplemental pass rechecked the entire extracted inventory. No duplicate extraction was created.

All 101 owning files were independently read from frozen Git96f objects and matched the hosted source receipt before/after. Binding digests:

- Source101: `{result['source_digest']}`.
- SDK22: `{result['sdk']['sha256']}`.
- Adapter24: `{result['adapter']['sha256']}`.
- Class216 inventory: `{one['class_inventory_sha256']}`.
- DEX419548bytes: `{one['dex']['classes.dex']['sha256']}`.

The retained log has 28 bootstrap and 12 sparse-checkout passing controls. The negative low-disk `status: failed` text is an intentional passing control; the subsequent actual bootstrap completed. Actual admission records **146,460,831,744 free bytes** against the unchanged **12-GiB** floor. Both HTTPS downloads use unchanged official download.swift.org effective URLs, exact size bounds and retained hashes: host package1503529808bytes/SHA256ee82e57774d6650f94aa06302435d6f44a055b9411698db8ecb85d9a3bcc91d0; AndroidSDK333223533bytes/SHA256d160cc3206dd1886dae3fef2337af5e25ec034692cd0ec225721c56cc69da7f5. The latter is also enforced by frozen bootstrap code.

The complete 1,091-byte pkgutil report (SHA256a6c20c7320918c428ec649491fde14930b9d37d7b7a54e56eb7b49971d05b9c7) has exit 0, empty stderr and terminal custody before expansion. Independent full-report parsing confirms the Swift Open Source installer, positive notarization, trusted timestamp, all three exact certificate identities/fingerprints, valid signing/expiry ordering and no remaining diagnostics. Frozen bootstrap consumes combined stdout/stderr and fails closed. This is retained macOS trust evidence, not a fresh signature/revocation verification.

Private payload expansion, Android SDK extraction, image NDK 27.3.13750724 copy and official setup script completed. Host image is macos26/X64,20260824.0517.1. Explicit child environment selects Xcode 26.6/17F113 and SDK 26.5. Bootstrap plus integration pre/post canonical inspections agree across eleven tools, six metadata identities and all five full distribution hashes. Frozen inspection walks complete installed trees, including symlink identity and target file bytes. javap 25.0.4.1 version/hash and Apple/source identity postflight are enforced. Deleted tools/downloads and initial bootstrap system-tool identities cannot be rehashed now; recorded measurements and frozen code are the evidence.

Both actual CLI producers use pinned dependencies and clean matching dependency checks before/after. All six Debug/Release original/relocated/exported closures have **18 pinned product Java sources, 216 Java17 classfiles and4,976 constant-pool member references**. Each uses exact `javac --release 17 -Xlint:all -Werror -proc:none` with SDK37 and D8 `--min-api 28`. Python independently decodes all **1,296 classfiles / 29,856 member entries**, matching every retained javap scope/index/kind/member; all DEX checksums and 389 class definitions per consumer match dexdump and contain all 216 product classes. Six full file inventories, locks, class inventories and DEX bytes are identical within this hosted run. Empty Resources exists only in original/relocated as source specifies. Frozen runner performs actual CLI export and moves original before relocated compilation. Member coverage excludes reflection/dynamic targets and post-D8 rewriting.

All 12 tamper case/configurations are exercised through both real CLI and copied driver: **24 expected nonzero refusals**, exact diagnostics and no recorded staging. Frozen code mutates pinned bytes or profile/lock state and recomputes generic locks for applicable cases, so generic lock updates do not bypass source admission.

All **13 bootstrap + 79 integration** recorded outer commands have exact argv/cwd coverage and retained stdout/stderr hash checks. Each separately records direct-child reap, stdout EOF, stderr EOF, positive owned-group absence and terminal custody, with no stop/error/cleanup failure. All cleanup signals report already-absent. Bootstrap command span 159.567 s / output 7,357 bytes and integration 551.802 s / output 52,052,859 bytes fit the 1,200/2,400-second phase limits, 300/600-second command limits, 5-second cleanup limits and 64-MiB phase output bounds; producer concurrency stays 2. Frozen runner creates new sessions and requires previous terminal custody before proceeding. Nested tool/version processes rely on enclosing group records; no independent per-grandchild reap, escaped-descendant containment, present process state or full-worker disposal is claimed.

Bootstrap and integration report owned scratch removal after terminal custody. Frozen failure paths retain scratch if custody is unresolved and fail when cleanup does not complete. Removed producer binaries, generated directories, dependency checkouts and tamper trees rely on retained measurements and frozen execution code, not a fresh rehash. Acquisition reports its own urllib and ZIP readers closed. Reviewer filesystem readers and ZIP context close; no network reader was created. Provider-internal disposal remains unobserved.

The audit passes **{result['checks']['total']} checks** ({result['checks']['main']} main + {result['checks']['supplemental']} exact-command/source supplement) with Python 3.14.8 and Git 2.56.0. Main audit took {a['elapsed_seconds']} s. audit.json records commands, tools, inputs, frozen Git reads and assertions; supplemental.json completes command/reader/scope evidence; artifact-inventory.json binds all bytes; result.json is the compact verdict. frozen/ holds exact owning bootstrap, runner, controls, workflow and supporting source. initial-audit-result.json retains an adaptation failure caused by old pair8 expected bootstrap hashes; the frozen diff explains the digest/profile update. No artifact was changed. seal.json hashes every review file except itself.

Reproduce the three commands in result.json using the exact ZIP/capture, Git objects and prior-evidence directories listed there. The review writes only this directory. No artifact/product execution, compiler/JVM/D8/Swift/native/UI/capture run, network, child agent, commit or push occurred. Parent documents and other lanes were untouched. Prior failure/review bytes were checked unchanged. PGIDs23663,20745,20770,20780,20817,20842,20851,20866; FieldLog40802230894/PGID2424/PID2621; held v5 and frozen hosted lanes were untouched. Phones remain disconnected. **No GA, API28 floor/linkage, APK, runtime, application signing, published-package, FieldLog or additional product-semantic qualification is granted.**
'''
(OUT/'REVIEW.md').write_text(report)
files={p.relative_to(OUT).as_posix():ident(p) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='seal.json'}
projection=hashlib.sha256(''.join(k+'\0'+v['sha256']+'\n' for k,v in sorted(files.items())).encode()).hexdigest()
write('seal.json',{'schema':1,'scope':result['scope'],'reviewed_revision':result['reviewed_revision'],'run':ac['run'],'attempt':ac['attempt'],'job':ac['job'],'artifact':ac['artifact'],'archive':ac['archive'],'files':files,'file_count':len(files),'bytes':sum(v['bytes'] for v in files.values()),'sha256_path_projection':projection,'excluded':'seal.json itself; report checksum is returned to parent','finished_utc':result['finished_utc']})
print(json.dumps({'verdict':'ACCEPT','blocking_findings':[],'checks':result['checks'],'seal':ident(OUT/'seal.json'),'result':ident(OUT/'result.json'),'audit':result['audit'],'supplemental':result['supplemental'],'sealed_files':len(files),'sealed_bytes':sum(v['bytes'] for v in files.values())},indent=2))
