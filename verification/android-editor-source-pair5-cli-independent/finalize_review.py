#!/usr/bin/env python3
"""Freeze this independent review only; never mutates the frozen candidate."""
import datetime,hashlib,json,pathlib,stat,subprocess,sys
O=pathlib.Path(__file__).resolve().parent;R=O.parents[1];P=R/'verification/android-editor-source-pair5-cli-integration';H=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def dump(n,x):(O/n).write_text(json.dumps(x,indent=2)+'\n')
def identity(p):return {'path':p.relative_to(O).as_posix(),'bytes':p.stat().st_size,'sha256':H(p)}
behavior=json.loads((O/'behavior.json').read_text());audit=json.loads((O/'evidence-audit.json').read_text());source=json.loads((O/'source-review.json').read_text());custody=json.loads((O/'custody.json').read_text())
dependency=json.loads((O/'elf-dependency-audit.json').read_text())
assert all(x['passed'] for x in [behavior,audit,source,custody,dependency]);assert not (O/'scratch').exists()
rows=[]
for f in sorted((O/'compiled/classes').rglob('*.class')):
 relative=f.relative_to(O/'compiled/classes');old=P/'artifacts/java-classes'/relative;rows.append({'path':str(relative),'bytes':f.stat().st_size,'fresh_sha256':H(f),'producer_sha256':H(old),'same':H(f)==H(old)})
assert len(rows)==212 and all(x['same'] for x in rows)
dump('compiled-class-comparison.json',{'class_members':len(rows),'all_byte_identical':True,'rows':rows})
dump('harness-failures.json',{'candidate_defects':[],'reviewer_harness_corrections':[{'retained':'custody-initial-review-harness-failure.json','cause':'Reviewer source projection included the source/ archive prefix; producer contract projects paths relative to source/. Corrected to sorted relative paths; no candidate change.'},{'retained':'attempt1/behavior.json and attempt1/evidence/positive-debug-export.log','cause':'Positive export intentionally received the negative fake swift sentinel environment. Product correctly refused compiler drift. Positive exports use real host swift version; all hostile controls keep fake tool sentinels.'},{'retained':'audit-attempt1/evidence-audit.json and audit-attempt1/evidence/independent-generated-debug-libmixer_android_jni.so-header.log','cause':'Reviewer looked for generated JNI at artifacts/generated/debug rather than retained artifacts/debug. Corrected using explicit archive mapping; all8 ELF inspections pass. Original compile/classes and failed path command are retained.'}],'producer_failures':'Candidate harness-failures.json and command-index.json remain immutable and preserved; initial timeouts/non-testable module/configuration failures are not claimed as passes.'})
failures=json.loads((O/'harness-failures.json').read_text())
for name in ['elf-dependency-initial-review-harness-failure.json','elf-dependency-second-review-harness-failure.json']:
 failures['reviewer_harness_corrections'].append({'retained':name,'cause':json.loads((O/name).read_text())['reason']})
dump('harness-failures.json',failures)
dump('cleanup.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'owned_scratch_removed':not (O/'scratch').exists(),'all_owned_command_groups_reaped':all(x['owned_child_reaped'] for x in behavior['rows']+audit['commands']),'compiled_classes_and_DEX':'Retained as closed review evidence; prior successful compile from reviewer path-error attempt retained separately. No build caches retained.','native_instances_started':0,'UI_or_capture_started':False,'process_inventory_performed':False,'other_projects_processes_or_data_touched':False,'original_python33_temporary_fixtures':'The copied unchanged host suites own /tmp fixtures and clean them using unittest cleanup. No new /tmp fixtures remain owned by review.'})
report={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':[sys.executable,*sys.argv],'python_version':sys.version,'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),'status':'independent-scoped-positive-review-complete','recommendation':'No candidate defects found; root may consider this exact isolated CLI derivative with other required lanes. Canonical promotion/coherent integration remain pending root review.','scope':'CLI/export selected profile5 source, admission/security ordering, host tests and offline unsigned consumer evidence only.','candidate':custody['candidate'],'rebinding':custody['rebinding'],'source_projection':custody['source_projection'],'source_members':162,'changed_canonical_targets':5,'canonical_sources_unchanged_at_final_audit':True,'source_policy':{'profile_id':'mixer.android-source-pair.5','SDK_members':22,'adapter_members':24,'Java_product_sources':18,'optional_canonical_only_members':3,'SDK_projection':'4c2e74bbdb1c060ffa2219ed378d11ed390e7a4454b95df4a2ee72074bb9b5a7','adapter_projection':'9d47585c18c325888c6d87914808449f1a92e4a3839d02ce5c4ae8f15801c10c','descriptor_sha256':'1aeab75c457c21e5c801ab8b446490971d510021c945d0841252360becd8ead3'},'fresh':{'behavior_commands':len(behavior['rows']),'actual_CLI_and_direct_driver_commands':190,'Python_tests':33,'behavior_assertions':len(behavior['assertions']),'source_security_checks':len(source['checks']),'audit_checks':len(audit['checks']),'ELF_dependency_identity_checks':len(dependency['checks']),'SDK_compiler_and_ELF_commands':len(audit['commands']),'total_recorded_commands':len(behavior['rows'])+len(audit['commands']),'four_sources_by_ten_mutation_types_at_four_entrypoints_commands':160,'positive_Debug_and_Release_relocated_exports':2,'SDK37_JDK_binary_version':'javac 25.0.4.1','javac_flags':['--release','17','-Xlint:all','-Werror','-proc:none','-sourcepath',''],'Java_product_sources':18,'emitted_classes':212,'emitted_classes_byte_identical_to_producer':True,'D8_min_api':28,'retained_ELF_reinspections':8},'producer_receipts_independently_audited':{'all_required_terminal_rows_pass':True,'CLI_Debug_functions':42,'CLI_Release_original_Xcode_context_functions':42,'release_cold_command_budget_seconds':180,'release_original_external_command_seconds':62.23981379088946,'cold_amendment_sha256':'8cef0df4db8ddaf9b9fefdc5b5a1b29298b3107f0243cb22867cd335e822f266','full_unsigned_driver_commands':47,'APK_bytes':28094174,'APK_sha256':'b52e60b07583ba095eab2c211a87fb64b87aa93641cd14cd74cfb8d73f2b1fe3','all_22_APK_member_hashes_match':True,'fresh_generated_and_relocated_app_owned_Swift_JNI_Debug_Release':'Retained source-bound commands/artifacts audited; not rebuilt in this independent lane.'},'security_reasoning':'source-review.json','behavior':'behavior.json','receipt_and_compiler_audit':'evidence-audit.json','ELF_exact_dependency_audit':'elf-dependency-audit.json','reviewer_harness_failures':'harness-failures.json','cleanup':'cleanup.json','candidate_defects':[],'limitations':['Full Swift Debug/Release42 suites and app-owned Swift/JNI/full47-command packaging were audited from the immutable producer packet, not independently rebuilt here. Fresh behavior used its sealed Debug/Release/old4 binaries.','ELF Android libc/libdl/libm dependencies are explicit Android system contracts; no physical runtime resolution is claimed. Other runtime/JNI AppAndroid dependencies were rehashed at their exact installed or sealed remapped identities.','Local observed source hashes are not an immutable build sandbox, signature verification or release authority. The installed CLI template/compiled policy is the trust boundary.','Other source/host-migration and compiled-boundary lanes require their own reviews; this review grants no combined integration acceptance.','Canonical promotion and integrated CI pending root.','Native runtime, physical iOS/Android, IME/focus/selection/composition/accessibility, published immutable FieldLog SDK, publicV2 routing, signing/stores/OTA/GA remain pending. No UI/capture/native runtime/process inventory was attempted.'],'memory_use':'Historical Mixer component-vs-product evidence boundary only; current scope and source facts were verified live.'}
dump('review.json',report)
(O/'README.md').write_text('''# Independent source-pair5 CLI review

The exact frozen candidate receives a scoped positive independent review: no
candidate defect was found. Canonical promotion, combined integration and CI
remain pending root acceptance. Read `review.json`, `source-review.json`,
`behavior.json`, `evidence-audit.json`, and `custody.json` for complete receipts.

Custody verifies all 1,217 candidate members (81,249,059 bytes), all 57 rebinding
members, the selected 162-file source projection, and exactly five declared CLI
changes. SDK22, adapter24/Java18, the descriptor and wire fields match the selected
profile5. The three independently optional canonical inputs stay separate from
product export. The exact bundled driver body and decoded profile are verified.

Fresh verification records 222 commands: 190 actual CLI/direct-driver operations,
Python33 plus its version command, and 30 SDK/compiler/ELF commands. All pass.
The four selected Java sources each receive all ten hostile mutations through
Debug build, Release export, creation and direct rendered build. Generic hash,
tool and output sentinels prove ordering. Two relocated Debug/Release exports,
optional copied-tree refusal, full-layout-before-content, old/new profiles and
prior rejected sources, stale4 rendered driver plus recomputed lock, raw marker
and raw inspect independence pass. Strict javac emits 212 classes, byte-identical
to producer output; D8 min28 passes with pinned SDK37. Actual compiler is JDK25.0.4.1;
--release17 is the bytecode/language target. All eight retained ELF artifacts pass
fresh header/dependency/symbol inspection. A further98 checks reconcile all
NEEDED/symbol sets and exact installed/remapped runtime identities; Android system
libraries remain explicitly labeled platform contracts.

The sealed producer full Debug42/Release42, original62.24-second Release command
under the root180-second cold-command amendment, full47-command unsigned driver,
generated/relocated ordinary Swift/JNI Debug/Release and 22-member unsigned APK
receipts are independently audited. Their expensive Swift compilation/packaging
was not replayed here. The APK is exactly28,094,174 bytes and its descriptor is
byte-identical. Prior producer failures remain immutable and are not passes.

Five reviewer harness mistakes and corrected outcomes are retained in
`harness-failures.json`. They changed no candidate source or assertion. All owned
scratch and child groups were cleaned/reaped. Compiled classes/DEX and failed
review-attempt output are retained evidence, not running processes or caches.
No UI, capture, native runtime, process inventory or other-project mutation occurred.

This is local host/source evidence. Combined integration, canonical changes, CI,
native/physical IME/focus/composition/accessibility, external published FieldLog
packages, publicV2, stores, signing, OTA and GA remain pending. Source hashing and
syntax review authorize no OTA release.
''')
files=[]
for p in sorted(O.rglob('*')):
 st=p.lstat();assert stat.S_ISREG(st.st_mode) or stat.S_ISDIR(st.st_mode),p
 if stat.S_ISREG(st.st_mode) and p.relative_to(O).as_posix() not in ['manifest.json','seal.json']:files.append(identity(p))
dump('manifest.json',{'schema':1,'scope':'Every independent ordinary output except manifest and self seal','members':files,'member_count':len(files),'member_bytes':sum(x['bytes'] for x in files)})
files=[identity(p) for p in sorted(O.rglob('*')) if p.is_file() and p.relative_to(O).as_posix()!='seal.json']
dump('seal.json',{'schema':1,'scope':'Closed independent CLI review only; no canonical/coherent/native/release/GA acceptance','member_count':len(files),'member_bytes':sum(x['bytes'] for x in files),'members':files})
print(json.dumps({'seal_sha256':H(O/'seal.json'),'members':len(files),'member_bytes':sum(x['bytes'] for x in files),'review':str(O/'review.json')},indent=2))
