define hidden void @_RNCNvNtNtNtNtCscBrn2zMo5wc_8mixer_vm26experimental_swift_reactor5cache18initial_profile_v135trusted_local_host_account_entry_v127run_one_admitted_fixture_v10Bb_(ptr sret([13624 x i8]) align 8 %_0, ptr align 8 %_1) unnamed_addr #1 !dbg !145131 !guid !145138 {
start:
  %_3 = alloca [32 x i8], align 8
    #dbg_declare(ptr %_1, !145135, !DIExpression(), !145139)
    #dbg_declare(ptr %_1, !145136, !DIExpression(DW_OP_plus_uconst, 8), !145140)
    #dbg_declare(ptr %_1, !145137, !DIExpression(DW_OP_plus_uconst, 40, DW_OP_deref), !145141)
  %_2 = load ptr, ptr %_1, align 8, !dbg !145142
  %0 = getelementptr inbounds i8, ptr %_1, i64 8, !dbg !145143
  call void @llvm.memcpy.p0.p0.i64(ptr align 8 %_3, ptr align 8 %0, i64 32, i1 false), !dbg !145143
  %1 = getelementptr inbounds i8, ptr %_1, i64 40, !dbg !145144
  %_5 = load ptr, ptr %1, align 8, !dbg !145144
; call mixer_vm::experimental_swift_reactor::cache::initial_profile_v1::trusted_local_host_account_entry_v1::run_prepaid_admitted_fixture_v1
  call void @_RNvNtNtNtNtCscBrn2zMo5wc_8mixer_vm26experimental_swift_reactor5cache18initial_profile_v135trusted_local_host_account_entry_v131run_prepaid_admitted_fixture_v1(ptr sret([13624 x i8]) align 8 %_0, ptr align 8 %_2, ptr align 8 %_3, ptr align 8 %_5), !dbg !145145
  ret void, !dbg !145146
}
