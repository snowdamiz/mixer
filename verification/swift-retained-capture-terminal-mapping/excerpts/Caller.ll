define hidden void @_RNvNtNtNtNtCscBrn2zMo5wc_8mixer_vm26experimental_swift_reactor5cache18initial_profile_v135trusted_local_host_account_entry_v127run_one_admitted_fixture_v1(ptr sret([13640 x i8]) align 8 %_0, ptr align 8 %account, ptr align 8 %fixture, ptr align 8 %attempt, ptr align 8 %expected) unnamed_addr #0 !dbg !242858 !guid !242892 {
start:
  %residual.dbg.spill6 = alloca [16 x i8], align 8
  %residual.dbg.spill = alloca [16 x i8], align 8
  %reservation.dbg.spill = alloca [16 x i8], align 8
  %val.dbg.spill3 = alloca [16 x i8], align 8
  %quote.dbg.spill = alloca [16 x i8], align 8
  %val.dbg.spill = alloca [16 x i8], align 8
  %expected.dbg.spill = alloca [8 x i8], align 8
  %fixture.dbg.spill = alloca [8 x i8], align 8
  %account.dbg.spill = alloca [8 x i8], align 8
  %_25 = alloca [48 x i8], align 8
  %_23 = alloca [13640 x i8], align 8
  %_15 = alloca [24 x i8], align 8
  %_14 = alloca [24 x i8], align 8
  %_7 = alloca [24 x i8], align 8
  %_6 = alloca [24 x i8], align 8
  store ptr %account, ptr %account.dbg.spill, align 8
    #dbg_declare(ptr %account.dbg.spill, !242876, !DIExpression(), !242893)
  store ptr %fixture, ptr %fixture.dbg.spill, align 8
    #dbg_declare(ptr %fixture.dbg.spill, !242877, !DIExpression(), !242894)
    #dbg_declare(ptr %attempt, !242878, !DIExpression(), !242895)
  store ptr %expected, ptr %expected.dbg.spill, align 8
    #dbg_declare(ptr %expected.dbg.spill, !242879, !DIExpression(), !242896)
; call mixer_vm::experimental_swift_reactor::cache::initial_profile_v1::trusted_local_host_account_entry_v1::host_account_v1::selected_whole_quote_v1
  call void @_RNvNtNtNtNtNtCscBrn2zMo5wc_8mixer_vm26experimental_swift_reactor5cache18initial_profile_v135trusted_local_host_account_entry_v115host_account_v123selected_whole_quote_v1(ptr sret([24 x i8]) align 8 %_7), !dbg !242897
; call <core::result::Result<mixer_vm::experimental_swift_reactor::cache::initial_profile_v1::trusted_local_host_account_entry_v1::host_account_v1::ReviewedWholeQuoteV1, mixer_vm::experimental_swift_reactor::cache::initial_profile_v1::trusted_local_host_account_entry_v1::host_account_v1::RefusalV1> as core::ops::try_trait::Try>::branch
  call void @_RNvXsp_NtCsjIpoRzUjyHQ_4core6resultINtB5_6ResultNtNtNtNtNtNtCscBrn2zMo5wc_8mixer_vm26experimental_swift_reactor5cache18initial_profile_v135trusted_local_host_account_entry_v115host_account_v120ReviewedWholeQuoteV1NtBM_9RefusalV1ENtNtNtB7_3ops9try_trait3Try6branchBW_(ptr sret([24 x i8]) align 8 %_6, ptr align 8 %_7) #31, !dbg !242897
  %_8 = load i64, ptr %_6, align 8, !dbg !242897
  %0 = trunc nuw i64 %_8 to i1, !dbg !242897
  br i1 %0, label %bb5, label %bb4, !dbg !242897

bb5:                                              ; preds = %start
  %1 = getelementptr inbounds i8, ptr %_6, i64 8, !dbg !242898
  %residual.04 = load i64, ptr %1, align 8, !dbg !242898
  %2 = getelementptr inbounds i8, ptr %1, i64 8, !dbg !242898
  %residual.15 = load i64, ptr %2, align 8, !dbg !242898
  store i64 %residual.04, ptr %residual.dbg.spill6, align 8, !dbg !242898
  %3 = getelementptr inbounds i8, ptr %residual.dbg.spill6, i64 8, !dbg !242898
  store i64 %residual.15, ptr %3, align 8, !dbg !242898
    #dbg_declare(ptr %residual.dbg.spill6, !242882, !DIExpression(), !242899)
; call <core::result::Result<mixer_vm::experimental_swift_reactor::cache::initial_profile_v1::trusted_local_host_account_entry_v1::host_account_v1::PrepaidOwnedV1<mixer_vm::experimental_swift_reactor::cache::initial_profile_v1::trusted_local_host_account_entry_v1::AdmittedFixtureOutcomeV1>, mixer_vm::experimental_swift_reactor::cache::initial_profile_v1::trusted_local_host_account_entry_v1::host_account_v1::RefusalV1> as core::ops::try_trait::FromResidual<core::result::Result<core::convert::Infallible, mixer_vm::experimental_swift_reactor::cache::initial_profile_v1::trusted_local_host_account_entry_v1::host_account_v1::RefusalV1>>>::from_residual
  call void @_RNvXsq_NtCsjIpoRzUjyHQ_4core6resultINtB5_6ResultINtNtNtNtNtNtCscBrn2zMo5wc_8mixer_vm26experimental_swift_reactor5cache18initial_profile_v135trusted_local_host_account_entry_v115host_account_v114PrepaidOwnedV1NtBP_24AdmittedFixtureOutcomeV1ENtBN_9RefusalV1EINtNtNtB7_3ops9try_trait12FromResidualIBy_NtNtB7_7convert10InfallibleB3Q_EE13from_residualBX_(ptr sret([13640 x i8]) align 8 %_0, i64 %residual.04, i64 %residual.15, ptr align 8 @alloc_45b24fd678542049ad91ef89703672fd) #31, !dbg !242900
  br label %bb13, !dbg !242901

bb4:                                              ; preds = %start
  %4 = getelementptr inbounds i8, ptr %_6, i64 8, !dbg !242897
  %val.0 = load i64, ptr %4, align 8, !dbg !242897
  %5 = getelementptr inbounds i8, ptr %4, i64 8, !dbg !242897
  %val.1 = load i64, ptr %5, align 8, !dbg !242897
  store i64 %val.0, ptr %val.dbg.spill, align 8, !dbg !242897
  %6 = getelementptr inbounds i8, ptr %val.dbg.spill, i64 8, !dbg !242897
  store i64 %val.1, ptr %6, align 8, !dbg !242897
    #dbg_declare(ptr %val.dbg.spill, !242884, !DIExpression(), !242903)
  store i64 %val.0, ptr %quote.dbg.spill, align 8, !dbg !242903
  %7 = getelementptr inbounds i8, ptr %quote.dbg.spill, i64 8, !dbg !242903
  store i64 %val.1, ptr %7, align 8, !dbg !242903
    #dbg_declare(ptr %quote.dbg.spill, !242880, !DIExpression(), !242904)
; call <mixer_vm::experimental_swift_reactor::cache::initial_profile_v1::trusted_local_host_account_entry_v1::host_account_v1::TrustedHostAccountV1>::reserve_whole_v1
  call void @_RNvMs_NtNtNtNtNtCscBrn2zMo5wc_8mixer_vm26experimental_swift_reactor5cache18initial_profile_v135trusted_local_host_account_entry_v115host_account_v1NtB4_20TrustedHostAccountV116reserve_whole_v1(ptr sret([24 x i8]) align 8 %_15, ptr align 8 %account, i64 %val.0, i64 %val.1), !dbg !242905
; call <core::result::Result<mixer_vm::experimental_swift_reactor::cache::initial_profile_v1::trusted_local_host_account_entry_v1::host_account_v1::ReservationV1, mixer_vm::experimental_swift_reactor::cache::initial_profile_v1::trusted_local_host_account_entry_v1::host_account_v1::RefusalV1> as core::ops::try_trait::Try>::branch
  call void @_RNvXsp_NtCsjIpoRzUjyHQ_4core6resultINtB5_6ResultNtNtNtNtNtNtCscBrn2zMo5wc_8mixer_vm26experimental_swift_reactor5cache18initial_profile_v135trusted_local_host_account_entry_v115host_account_v113ReservationV1NtBM_9RefusalV1ENtNtNtB7_3ops9try_trait3Try6branchBW_(ptr sret([24 x i8]) align 8 %_14, ptr align 8 %_15) #31, !dbg !242906
  %_18 = load i64, ptr %_14, align 8, !dbg !242906
  %8 = trunc nuw i64 %_18 to i1, !dbg !242906
  br i1 %8, label %bb10, label %bb9, !dbg !242906

bb10:                                             ; preds = %bb4
  %9 = getelementptr inbounds i8, ptr %_14, i64 8, !dbg !242907
  %residual.0 = load i64, ptr %9, align 8, !dbg !242907
  %10 = getelementptr inbounds i8, ptr %9, i64 8, !dbg !242907
  %residual.1 = load i64, ptr %10, align 8, !dbg !242907
  store i64 %residual.0, ptr %residual.dbg.spill, align 8, !dbg !242907
  %11 = getelementptr inbounds i8, ptr %residual.dbg.spill, i64 8, !dbg !242907
  store i64 %residual.1, ptr %11, align 8, !dbg !242907
    #dbg_declare(ptr %residual.dbg.spill, !242888, !DIExpression(), !242908)
; call <core::result::Result<mixer_vm::experimental_swift_reactor::cache::initial_profile_v1::trusted_local_host_account_entry_v1::host_account_v1::PrepaidOwnedV1<mixer_vm::experimental_swift_reactor::cache::initial_profile_v1::trusted_local_host_account_entry_v1::AdmittedFixtureOutcomeV1>, mixer_vm::experimental_swift_reactor::cache::initial_profile_v1::trusted_local_host_account_entry_v1::host_account_v1::RefusalV1> as core::ops::try_trait::FromResidual<core::result::Result<core::convert::Infallible, mixer_vm::experimental_swift_reactor::cache::initial_profile_v1::trusted_local_host_account_entry_v1::host_account_v1::RefusalV1>>>::from_residual
  call void @_RNvXsq_NtCsjIpoRzUjyHQ_4core6resultINtB5_6ResultINtNtNtNtNtNtCscBrn2zMo5wc_8mixer_vm26experimental_swift_reactor5cache18initial_profile_v135trusted_local_host_account_entry_v115host_account_v114PrepaidOwnedV1NtBP_24AdmittedFixtureOutcomeV1ENtBN_9RefusalV1EINtNtNtB7_3ops9try_trait12FromResidualIBy_NtNtB7_7convert10InfallibleB3Q_EE13from_residualBX_(ptr sret([13640 x i8]) align 8 %_0, i64 %residual.0, i64 %residual.1, ptr align 8 @alloc_58acb9d57b6b2ee970c2f24d5d712db0) #31, !dbg !242909
  br label %bb13, !dbg !242910

bb9:                                              ; preds = %bb4
  %12 = getelementptr inbounds i8, ptr %_14, i64 8, !dbg !242906
  %val.01 = load ptr, ptr %12, align 8, !dbg !242906
  %13 = getelementptr inbounds i8, ptr %12, i64 8, !dbg !242906
  %val.12 = load i64, ptr %13, align 8, !dbg !242906
  store ptr %val.01, ptr %val.dbg.spill3, align 8, !dbg !242906
  %14 = getelementptr inbounds i8, ptr %val.dbg.spill3, i64 8, !dbg !242906
  store i64 %val.12, ptr %14, align 8, !dbg !242906
    #dbg_declare(ptr %val.dbg.spill3, !242890, !DIExpression(), !242912)
  store ptr %val.01, ptr %reservation.dbg.spill, align 8, !dbg !242912
  %15 = getelementptr inbounds i8, ptr %reservation.dbg.spill, i64 8, !dbg !242912
  store i64 %val.12, ptr %15, align 8, !dbg !242912
    #dbg_declare(ptr %reservation.dbg.spill, !242886, !DIExpression(), !242913)
  store ptr %fixture, ptr %_25, align 8, !dbg !242914
  %16 = getelementptr inbounds i8, ptr %_25, i64 8, !dbg !242914
  call void @llvm.memcpy.p0.p0.i64(ptr align 8 %16, ptr align 8 %attempt, i64 32, i1 false), !dbg !242914
  %17 = getelementptr inbounds i8, ptr %_25, i64 40, !dbg !242914
  store ptr %expected, ptr %17, align 8, !dbg !242914
; call <mixer_vm::experimental_swift_reactor::cache::initial_profile_v1::trusted_local_host_account_entry_v1::host_account_v1::ReservationV1>::dispatch_v1::<mixer_vm::experimental_swift_reactor::cache::initial_profile_v1::trusted_local_host_account_entry_v1::AdmittedFixtureOutcomeV1, mixer_vm::experimental_swift_reactor::cache::initial_profile_v1::trusted_local_host_account_entry_v1::run_one_admitted_fixture_v1::{closure#0}>
  call void @_RINvMs0_NtNtNtNtNtCscBrn2zMo5wc_8mixer_vm26experimental_swift_reactor5cache18initial_profile_v135trusted_local_host_account_entry_v115host_account_v1NtB6_13ReservationV111dispatch_v1NtB8_24AdmittedFixtureOutcomeV1NCNvB8_27run_one_admitted_fixture_v10EBg_(ptr sret([13640 x i8]) align 8 %_23, ptr align 8 %val.01, i64 %val.12, ptr align 8 %_25), !dbg !242915
  call void @llvm.memcpy.p0.p0.i64(ptr align 8 %_0, ptr align 8 %_23, i64 13640, i1 false), !dbg !242916
  br label %bb14, !dbg !242917

bb14:                                             ; preds = %bb13, %bb9
  ret void, !dbg !242917

bb13:                                             ; preds = %bb5, %bb10
  br label %bb14, !dbg !242917

bb3:                                              ; No predecessors!
  unreachable, !dbg !242901
}
