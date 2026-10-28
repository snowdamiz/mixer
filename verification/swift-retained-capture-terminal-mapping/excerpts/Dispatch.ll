define hidden void @_RINvMs0_NtNtNtNtNtCscBrn2zMo5wc_8mixer_vm26experimental_swift_reactor5cache18initial_profile_v135trusted_local_host_account_entry_v115host_account_v1NtB6_13ReservationV111dispatch_v1NtB8_24AdmittedFixtureOutcomeV1NCNvB8_27run_one_admitted_fixture_v10EBg_(ptr sret([13640 x i8]) align 8 %_0, ptr align 8 %self.0, i64 %self.1, ptr align 8 %action) unnamed_addr #0 !dbg !36320 !guid !36419 {
start:
  %self.dbg.spill = alloca [16 x i8], align 8
  %_7 = alloca [13624 x i8], align 8
  %_6 = alloca [13624 x i8], align 8
  %_4 = alloca [48 x i8], align 8
  %owned = alloca [13624 x i8], align 8
  store ptr %self.0, ptr %self.dbg.spill, align 8
  %0 = getelementptr inbounds i8, ptr %self.dbg.spill, i64 8
  store i64 %self.1, ptr %0, align 8
    #dbg_declare(ptr %self.dbg.spill, !36415, !DIExpression(), !36420)
    #dbg_declare(ptr %action, !36416, !DIExpression(), !36421)
    #dbg_declare(ptr %owned, !36417, !DIExpression(), !36422)
  call void @llvm.memcpy.p0.p0.i64(ptr align 8 %_4, ptr align 8 %action, i64 48, i1 false), !dbg !36423
; call mixer_vm::experimental_swift_reactor::cache::initial_profile_v1::trusted_local_host_account_entry_v1::run_one_admitted_fixture_v1::{closure#0}
  call void @_RNCNvNtNtNtNtCscBrn2zMo5wc_8mixer_vm26experimental_swift_reactor5cache18initial_profile_v135trusted_local_host_account_entry_v127run_one_admitted_fixture_v10Bb_(ptr sret([13624 x i8]) align 8 %owned, ptr align 8 %_4) #31, !dbg !36423
  br label %bb1, !dbg !36423

bb1:                                              ; preds = %start
  call void @llvm.memcpy.p0.p0.i64(ptr align 8 %_7, ptr align 8 %owned, i64 13624, i1 false), !dbg !36424
  call void @llvm.memcpy.p0.p0.i64(ptr align 8 %_6, ptr align 8 %_7, i64 13624, i1 false), !dbg !36425
  call void @llvm.memcpy.p0.p0.i64(ptr align 8 %_0, ptr align 8 %_6, i64 13624, i1 false), !dbg !36426
  %1 = getelementptr inbounds i8, ptr %_0, i64 13624, !dbg !36426
  store ptr %self.0, ptr %1, align 8, !dbg !36426
  %2 = getelementptr inbounds i8, ptr %1, i64 8, !dbg !36426
  store i64 %self.1, ptr %2, align 8, !dbg !36426
  ret void, !dbg !36427

bb2:                                              ; No predecessors!
  unreachable
}
