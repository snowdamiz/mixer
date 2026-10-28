define hidden void @_RNvNtNtNtNtCscBrn2zMo5wc_8mixer_vm26experimental_swift_reactor5cache18initial_profile_v135trusted_local_host_account_entry_v131run_prepaid_admitted_fixture_v1(ptr sret([13624 x i8]) align 8 %_0, ptr align 8 %fixture, ptr align 8 %attempt, ptr align 8 %expected) unnamed_addr #0 personality ptr @rust_eh_personality !dbg !242918 !guid !242955 {
start:
  %0 = alloca [16 x i8], align 8
  %snapshot.dbg.spill = alloca [4 x i8], align 4
  %rows.dbg.spill = alloca [4 x i8], align 4
  %session.dbg.spill = alloca [4 x i8], align 4
  %build.dbg.spill = alloca [4 x i8], align 4
  %source.dbg.spill = alloca [4 x i8], align 4
  %binding.dbg.spill = alloca [8 x i8], align 8
  %root.dbg.spill = alloca [8 x i8], align 8
  %expected.dbg.spill = alloca [8 x i8], align 8
  %fixture.dbg.spill = alloca [8 x i8], align 8
  %_66 = alloca [1 x i8], align 1
  %_65 = alloca [1 x i8], align 1
  %_64 = alloca [1 x i8], align 1
  %_63 = alloca [1 x i8], align 1
  %_62 = alloca [1 x i8], align 1
  %_61 = alloca [1 x i8], align 1
  %_60 = alloca [1 x i8], align 1
  %_58 = alloca [13616 x i8], align 8
  %_57 = alloca [13616 x i8], align 8
  %_56 = alloca [424 x i8], align 8
  %_55 = alloca [1288 x i8], align 8
  %complete = alloca [13616 x i8], align 8
  %_52 = alloca [136 x i8], align 8
  %_49 = alloca [256 x i8], align 1
  %_48 = alloca [8 x i8], align 8
  %_47 = alloca [4 x i8], align 4
  %_46 = alloca [4 x i8], align 4
  %args = alloca [424 x i8], align 8
  %_43 = alloca [1264 x i8], align 8
  %_42 = alloca [32 x i8], align 8
  %correlated = alloca [1288 x i8], align 8
  %_40 = alloca [1264 x i8], align 8
  %original_carrier = alloca [1264 x i8], align 8
  %_36 = alloca [40 x i8], align 8
  %complete_original = alloca [1264 x i8], align 8
  %cancellation = alloca [8 x i8], align 8
  %_29 = alloca [40 x i8], align 8
  %_28 = alloca [13616 x i8], align 8
  %refused = alloca [40 x i8], align 8
  %_13 = alloca [40 x i8], align 8
  %_12 = alloca [20 x i8], align 4
  %snapshot = alloca [4 x i8], align 4
  %rows = alloca [4 x i8], align 4
  %session = alloca [4 x i8], align 4
  %build = alloca [4 x i8], align 4
  %source = alloca [4 x i8], align 4
  store ptr %fixture, ptr %fixture.dbg.spill, align 8
    #dbg_declare(ptr %fixture.dbg.spill, !242922, !DIExpression(), !242956)
    #dbg_declare(ptr %attempt, !242923, !DIExpression(), !242957)
  store ptr %expected, ptr %expected.dbg.spill, align 8
    #dbg_declare(ptr %expected.dbg.spill, !242924, !DIExpression(), !242958)
    #dbg_declare(ptr %source, !242929, !DIExpression(), !242959)
    #dbg_declare(ptr %build, !242931, !DIExpression(), !242960)
    #dbg_declare(ptr %session, !242932, !DIExpression(), !242961)
    #dbg_declare(ptr %rows, !242933, !DIExpression(), !242962)
    #dbg_declare(ptr %snapshot, !242934, !DIExpression(), !242963)
    #dbg_declare(ptr %refused, !242941, !DIExpression(), !242964)
    #dbg_declare(ptr %cancellation, !242943, !DIExpression(), !242965)
    #dbg_declare(ptr %complete_original, !242945, !DIExpression(), !242966)
    #dbg_declare(ptr %original_carrier, !242947, !DIExpression(), !242967)
    #dbg_declare(ptr %correlated, !242949, !DIExpression(), !242968)
    #dbg_declare(ptr %args, !242951, !DIExpression(), !242969)
    #dbg_declare(ptr %complete, !242953, !DIExpression(), !242970)
  store i8 0, ptr %_66, align 1, !dbg !242971
  store i8 0, ptr %_65, align 1, !dbg !242971
  store i8 0, ptr %_64, align 1, !dbg !242971
  store i8 0, ptr %_63, align 1, !dbg !242971
  store i8 0, ptr %_62, align 1, !dbg !242971
  store i8 0, ptr %_61, align 1, !dbg !242971
  store i8 0, ptr %_60, align 1, !dbg !242971
; call <mixer_vm::experimental_swift_reactor::retained_profile_loader_v1::prepaid_input_owner_v1::PrepaidCorrelationAttemptV1>::original_root_v1
  %root = call align 8 ptr @_RNvMs6_NtNtNtCscBrn2zMo5wc_8mixer_vm26experimental_swift_reactor26retained_profile_loader_v122prepaid_input_owner_v1NtB5_27PrepaidCorrelationAttemptV116original_root_v1(ptr align 8 %attempt), !dbg !242972
  store ptr %root, ptr %root.dbg.spill, align 8, !dbg !242972
    #dbg_declare(ptr %root.dbg.spill, !242925, !DIExpression(), !242973)
  store ptr %fixture, ptr %binding.dbg.spill, align 8, !dbg !242974
    #dbg_declare(ptr %binding.dbg.spill, !242927, !DIExpression(), !242975)
; call mixer_vm::experimental_swift_reactor::cache::initial_profile_v1::trusted_local_host_account_entry_v1::setup_files_once_v1
  call void @_RNvNtNtNtNtCscBrn2zMo5wc_8mixer_vm26experimental_swift_reactor5cache18initial_profile_v135trusted_local_host_account_entry_v119setup_files_once_v1(ptr sret([40 x i8]) align 8 %_13, ptr align 8 %fixture), !dbg !242976
  %1 = load i32, ptr %_13, align 8, !dbg !242976
  %_15 = zext i32 %1 to i64, !dbg !242976
  %2 = icmp eq i64 %_15, 0, !dbg !242977
  br i1 %2, label %bb4, label %bb3, !dbg !242977

bb4:                                              ; preds = %start
  %3 = getelementptr inbounds i8, ptr %_13, i64 4, !dbg !242978
  %source1 = load i32, ptr %3, align 4, !dbg !242978
  store i32 %source1, ptr %source.dbg.spill, align 4, !dbg !242978
    #dbg_declare(ptr %source.dbg.spill, !242935, !DIExpression(), !242979)
  %4 = getelementptr inbounds i8, ptr %_13, i64 8, !dbg !242980
  %build2 = load i32, ptr %4, align 8, !dbg !242980
  store i32 %build2, ptr %build.dbg.spill, align 4, !dbg !242980
    #dbg_declare(ptr %build.dbg.spill, !242937, !DIExpression(), !242981)
  %5 = getelementptr inbounds i8, ptr %_13, i64 12, !dbg !242982
  %session3 = load i32, ptr %5, align 4, !dbg !242982
  store i32 %session3, ptr %session.dbg.spill, align 4, !dbg !242982
    #dbg_declare(ptr %session.dbg.spill, !242938, !DIExpression(), !242983)
  %6 = getelementptr inbounds i8, ptr %_13, i64 16, !dbg !242984
  %rows4 = load i32, ptr %6, align 8, !dbg !242984
  store i32 %rows4, ptr %rows.dbg.spill, align 4, !dbg !242984
    #dbg_declare(ptr %rows.dbg.spill, !242939, !DIExpression(), !242985)
  %7 = getelementptr inbounds i8, ptr %_13, i64 20, !dbg !242986
  %snapshot5 = load i32, ptr %7, align 4, !dbg !242986
  store i32 %snapshot5, ptr %snapshot.dbg.spill, align 4, !dbg !242986
    #dbg_declare(ptr %snapshot.dbg.spill, !242940, !DIExpression(), !242987)
  store i32 %source1, ptr %_12, align 4, !dbg !242988
  %8 = getelementptr inbounds i8, ptr %_12, i64 4, !dbg !242988
  store i32 %build2, ptr %8, align 4, !dbg !242988
  %9 = getelementptr inbounds i8, ptr %_12, i64 8, !dbg !242988
  store i32 %session3, ptr %9, align 4, !dbg !242988
  %10 = getelementptr inbounds i8, ptr %_12, i64 12, !dbg !242988
  store i32 %rows4, ptr %10, align 4, !dbg !242988
  %11 = getelementptr inbounds i8, ptr %_12, i64 16, !dbg !242988
  store i32 %snapshot5, ptr %11, align 4, !dbg !242988
  store i8 1, ptr %_66, align 1, !dbg !242989
  %12 = load i32, ptr %_12, align 4, !dbg !242989
  store i32 %12, ptr %source, align 4, !dbg !242989
  store i8 1, ptr %_65, align 1, !dbg !242990
  %13 = getelementptr inbounds i8, ptr %_12, i64 4, !dbg !242990
  %14 = load i32, ptr %13, align 4, !dbg !242990
  store i32 %14, ptr %build, align 4, !dbg !242990
  store i8 1, ptr %_64, align 1, !dbg !242991
  %15 = getelementptr inbounds i8, ptr %_12, i64 8, !dbg !242991
  %16 = load i32, ptr %15, align 4, !dbg !242991
  store i32 %16, ptr %session, align 4, !dbg !242991
  store i8 1, ptr %_63, align 1, !dbg !242992
  %17 = getelementptr inbounds i8, ptr %_12, i64 12, !dbg !242992
  %18 = load i32, ptr %17, align 4, !dbg !242992
  store i32 %18, ptr %rows, align 4, !dbg !242992
  store i8 1, ptr %_62, align 1, !dbg !242993
  %19 = getelementptr inbounds i8, ptr %_12, i64 16, !dbg !242993
  %20 = load i32, ptr %19, align 4, !dbg !242993
  store i32 %20, ptr %snapshot, align 4, !dbg !242993
  %21 = load i32, ptr %_13, align 8, !dbg !242994
  %_67 = zext i32 %21 to i64, !dbg !242994
  %22 = icmp eq i64 %_67, 0, !dbg !242994
  br i1 %22, label %bb5, label %bb22, !dbg !242994

bb3:                                              ; preds = %start
  call void @llvm.memcpy.p0.p0.i64(ptr align 8 %refused, ptr align 8 %_13, i64 40, i1 false), !dbg !242995
  call void @llvm.memcpy.p0.p0.i64(ptr align 8 %_29, ptr align 8 %refused, i64 40, i1 false), !dbg !242996
  %23 = getelementptr inbounds i8, ptr %_28, i64 8, !dbg !242997
  call void @llvm.memcpy.p0.p0.i64(ptr align 8 %23, ptr align 8 %_29, i64 40, i1 false), !dbg !242997
  store i64 -1, ptr %_28, align 8, !dbg !242997
  call void @llvm.memcpy.p0.p0.i64(ptr align 8 %_0, ptr align 8 %_28, i64 13616, i1 false), !dbg !242998
  %24 = getelementptr inbounds i8, ptr %_0, i64 13616, !dbg !242998
  store ptr %root, ptr %24, align 8, !dbg !242998
  br label %bb13, !dbg !242999

bb5:                                              ; preds = %bb22, %bb4
; invoke <mixer_vm::execute::Cancellation as core::default::Default>::default
  %25 = invoke ptr @_RNvXs2_NtCscBrn2zMo5wc_8mixer_vm7executeNtB5_12CancellationNtNtCsjIpoRzUjyHQ_4core7default7Default7defaultB7_()
          to label %bb6 unwind label %cleanup, !dbg !243000

bb22:                                             ; preds = %bb4
; invoke core::ptr::drop_glue::<mixer_vm::experimental_swift_reactor::cache::initial_profile_v1::trusted_local_host_account_entry_v1::SetupOutcomeV1>
  invoke void @_RINvNtCsjIpoRzUjyHQ_4core3ptr9drop_glueNtNtNtNtNtCscBrn2zMo5wc_8mixer_vm26experimental_swift_reactor5cache18initial_profile_v135trusted_local_host_account_entry_v114SetupOutcomeV1EBL_(ptr align 8 %_13)
          to label %bb5 unwind label %cleanup, !dbg !242994

bb28:                                             ; preds = %bb25, %bb26, %cleanup
  %26 = load i8, ptr %_62, align 1, !dbg !243001
  %27 = trunc nuw i8 %26 to i1, !dbg !243001
  br i1 %27, label %bb27, label %bb17, !dbg !243001

cleanup:                                          ; preds = %bb5, %bb22
  %28 = landingpad { ptr, i32 }
          cleanup
  %29 = extractvalue { ptr, i32 } %28, 0
  %30 = extractvalue { ptr, i32 } %28, 1
  store ptr %29, ptr %0, align 8
  %31 = getelementptr inbounds i8, ptr %0, i64 8
  store i32 %30, ptr %31, align 8
  br label %bb28

bb6:                                              ; preds = %bb5
  store ptr %25, ptr %cancellation, align 8, !dbg !243000
  store i8 1, ptr %_61, align 1, !dbg !243002
  store i8 0, ptr %_66, align 1, !dbg !243003
  %_33 = load i32, ptr %source, align 4, !dbg !243003
  store i8 0, ptr %_65, align 1, !dbg !243004
  %_34 = load i32, ptr %build, align 4, !dbg !243004
  store i8 0, ptr %_64, align 1, !dbg !243005
  %_35 = load i32, ptr %session, align 4, !dbg !243005
  %32 = getelementptr inbounds i8, ptr %fixture, i64 336, !dbg !243006
  call void @llvm.memcpy.p0.p0.i64(ptr align 8 %_36, ptr align 8 %32, i64 40, i1 false), !dbg !243006
; invoke mixer_vm::experimental_swift_reactor::retained_profile_loader_v1::load_selected_retained_profile_v1
  invoke void @_RNvNtNtCscBrn2zMo5wc_8mixer_vm26experimental_swift_reactor26retained_profile_loader_v133load_selected_retained_profile_v1(ptr sret([1264 x i8]) align 8 %complete_original, i32 %_33, i32 %_34, i32 %_35, ptr align 8 %_36, ptr align 8 %cancellation)
          to label %bb7 unwind label %cleanup6, !dbg !243007

bb26:                                             ; preds = %bb23, %bb24, %cleanup6
  %33 = load i8, ptr %_61, align 1, !dbg !243008
  %34 = trunc nuw i8 %33 to i1, !dbg !243008
  br i1 %34, label %bb25, label %bb28, !dbg !243008

cleanup6:                                         ; preds = %bb8, %bb7, %bb6
  %35 = landingpad { ptr, i32 }
          cleanup
  %36 = extractvalue { ptr, i32 } %35, 0
  %37 = extractvalue { ptr, i32 } %35, 1
  store ptr %36, ptr %0, align 8
  %38 = getelementptr inbounds i8, ptr %0, i64 8
  store i32 %37, ptr %38, align 8
  br label %bb26

bb7:                                              ; preds = %bb6
  call void @llvm.memcpy.p0.p0.i64(ptr align 8 %_40, ptr align 8 %complete_original, i64 1264, i1 false), !dbg !243009
; invoke <mixer_vm::experimental_swift_reactor::retained_profile_loader_v1::prepaid_input_owner_v1::SuppliedLoaderCarrierV1>::retain_complete_v1
  invoke void @_RNvMs9_NtNtNtCscBrn2zMo5wc_8mixer_vm26experimental_swift_reactor26retained_profile_loader_v122prepaid_input_owner_v1NtB5_23SuppliedLoaderCarrierV118retain_complete_v1(ptr sret([1264 x i8]) align 8 %original_carrier, ptr align 8 %_40)
          to label %bb8 unwind label %cleanup6, !dbg !243010

bb8:                                              ; preds = %bb7
  call void @llvm.memcpy.p0.p0.i64(ptr align 8 %_42, ptr align 8 %attempt, i64 32, i1 false), !dbg !243011
  call void @llvm.memcpy.p0.p0.i64(ptr align 8 %_43, ptr align 8 %original_carrier, i64 1264, i1 false), !dbg !243012
; invoke mixer_vm::experimental_swift_reactor::retained_profile_loader_v1::prepaid_input_owner_v1::correlate_admitted_loader_v1
  invoke void @_RNvNtNtNtCscBrn2zMo5wc_8mixer_vm26experimental_swift_reactor26retained_profile_loader_v122prepaid_input_owner_v128correlate_admitted_loader_v1(ptr sret([1288 x i8]) align 8 %correlated, ptr align 8 %_42, ptr align 8 %_43, ptr align 8 %expected)
          to label %bb9 unwind label %cleanup6, !dbg !243013

bb9:                                              ; preds = %bb8
  store i8 1, ptr %_60, align 1, !dbg !243014
  store i8 0, ptr %_63, align 1, !dbg !243015
  %39 = load i32, ptr %rows, align 4, !dbg !243015
  store i32 %39, ptr %_46, align 4, !dbg !243015
  store i8 0, ptr %_62, align 1, !dbg !243016
  %40 = load i32, ptr %snapshot, align 4, !dbg !243016
  store i32 %40, ptr %_47, align 4, !dbg !243016
  store i8 0, ptr %_61, align 1, !dbg !243017
  %41 = load ptr, ptr %cancellation, align 8, !dbg !243017
  store ptr %41, ptr %_48, align 8, !dbg !243017
  %_51 = getelementptr inbounds i8, ptr %fixture, i64 80, !dbg !243018
; invoke mixer_vm::experimental_swift_reactor::cache::initial_profile_v1::trusted_local_host_account_entry_v1::copy_claims_v1
  invoke void @_RNvNtNtNtNtCscBrn2zMo5wc_8mixer_vm26experimental_swift_reactor5cache18initial_profile_v135trusted_local_host_account_entry_v114copy_claims_v1(ptr sret([256 x i8]) align 1 %_49, ptr %_51)
          to label %bb10 unwind label %cleanup7, !dbg !243019

bb14:                                             ; preds = %cleanup7
; invoke core::ptr::drop_glue::<mixer_vm::execute::Cancellation>
  invoke void @_RINvNtCsjIpoRzUjyHQ_4core3ptr9drop_glueNtNtCscBrn2zMo5wc_8mixer_vm7execute12CancellationEBF_(ptr align 8 %_48) #34
          to label %bb15 unwind label %terminate, !dbg !243020

cleanup7:                                         ; preds = %bb10, %bb9
  %42 = landingpad { ptr, i32 }
          cleanup
  %43 = extractvalue { ptr, i32 } %42, 0
  %44 = extractvalue { ptr, i32 } %42, 1
  store ptr %43, ptr %0, align 8
  %45 = getelementptr inbounds i8, ptr %0, i64 8
  store i32 %44, ptr %45, align 8
  br label %bb14

bb10:                                             ; preds = %bb9
  %46 = getelementptr inbounds i8, ptr %fixture, i64 376, !dbg !243021
  call void @llvm.memcpy.p0.p0.i64(ptr align 8 %_52, ptr align 8 %46, i64 136, i1 false), !dbg !243021
; invoke <std::time::Instant>::now
  %47 = invoke { i64, i32 } @_RNvMNtCs1SSuMAdGM58_3std4timeNtB2_7Instant3now()
          to label %bb11 unwind label %cleanup7, !dbg !243022

bb11:                                             ; preds = %bb10
  %_53.0 = extractvalue { i64, i32 } %47, 0, !dbg !243022
  %_53.1 = extractvalue { i64, i32 } %47, 1, !dbg !243022
  %48 = load i32, ptr %_46, align 4, !dbg !243023
  %49 = getelementptr inbounds i8, ptr %args, i64 416, !dbg !243023
  store i32 %48, ptr %49, align 8, !dbg !243023
  %50 = load i32, ptr %_47, align 4, !dbg !243023
  %51 = getelementptr inbounds i8, ptr %args, i64 420, !dbg !243023
  store i32 %50, ptr %51, align 4, !dbg !243023
  %52 = load ptr, ptr %_48, align 8, !dbg !243023
  %53 = getelementptr inbounds i8, ptr %args, i64 16, !dbg !243023
  store ptr %52, ptr %53, align 8, !dbg !243023
  %54 = getelementptr inbounds i8, ptr %args, i64 24, !dbg !243023
  call void @llvm.memcpy.p0.p0.i64(ptr align 8 %54, ptr align 1 %_49, i64 256, i1 false), !dbg !243023
  %55 = getelementptr inbounds i8, ptr %args, i64 280, !dbg !243023
  call void @llvm.memcpy.p0.p0.i64(ptr align 8 %55, ptr align 8 %_52, i64 136, i1 false), !dbg !243023
  store i64 %_53.0, ptr %args, align 8, !dbg !243023
  %56 = getelementptr inbounds i8, ptr %args, i64 8, !dbg !243023
  store i32 %_53.1, ptr %56, align 8, !dbg !243023
  store i8 0, ptr %_60, align 1, !dbg !243024
  call void @llvm.memcpy.p0.p0.i64(ptr align 8 %_55, ptr align 8 %correlated, i64 1288, i1 false), !dbg !243024
  call void @llvm.memcpy.p0.p0.i64(ptr align 8 %_56, ptr align 8 %args, i64 424, i1 false), !dbg !243025
; invoke <mixer_vm::experimental_swift_reactor::retained_profile_loader_v1::prepaid_input_owner_v1::OwnedCorrelationOutcomeV1>::run_fixture_once_v1
  invoke void @_RNvMse_NtNtNtCscBrn2zMo5wc_8mixer_vm26experimental_swift_reactor26retained_profile_loader_v122prepaid_input_owner_v1NtB5_25OwnedCorrelationOutcomeV119run_fixture_once_v1(ptr sret([13616 x i8]) align 8 %complete, ptr align 8 %_55, ptr align 8 %_56)
          to label %bb12 unwind label %cleanup8, !dbg !243026

bb24:                                             ; preds = %bb16, %cleanup8
  %57 = load i8, ptr %_60, align 1, !dbg !243027
  %58 = trunc nuw i8 %57 to i1, !dbg !243027
  br i1 %58, label %bb23, label %bb26, !dbg !243027

cleanup8:                                         ; preds = %bb11
  %59 = landingpad { ptr, i32 }
          cleanup
  %60 = extractvalue { ptr, i32 } %59, 0
  %61 = extractvalue { ptr, i32 } %59, 1
  store ptr %60, ptr %0, align 8
  %62 = getelementptr inbounds i8, ptr %0, i64 8
  store i32 %61, ptr %62, align 8
  br label %bb24

bb12:                                             ; preds = %bb11
  call void @llvm.memcpy.p0.p0.i64(ptr align 8 %_58, ptr align 8 %complete, i64 13616, i1 false), !dbg !243028
  call void @llvm.memcpy.p0.p0.i64(ptr align 8 %_57, ptr align 8 %_58, i64 13616, i1 false), !dbg !243029
  call void @llvm.memcpy.p0.p0.i64(ptr align 8 %_0, ptr align 8 %_57, i64 13616, i1 false), !dbg !243030
  %63 = getelementptr inbounds i8, ptr %_0, i64 13616, !dbg !243030
  store ptr %root, ptr %63, align 8, !dbg !243030
  store i8 0, ptr %_60, align 1, !dbg !243027
  store i8 0, ptr %_61, align 1, !dbg !243008
  store i8 0, ptr %_62, align 1, !dbg !243001
  store i8 0, ptr %_63, align 1, !dbg !243001
  store i8 0, ptr %_64, align 1, !dbg !243001
  store i8 0, ptr %_65, align 1, !dbg !243001
  store i8 0, ptr %_66, align 1, !dbg !243001
  br label %bb13, !dbg !242999

bb13:                                             ; preds = %bb3, %bb12
  ret void, !dbg !242999

terminate:                                        ; preds = %bb32, %bb31, %bb30, %bb29, %bb27, %bb25, %bb23, %bb16, %bb15, %bb14
  %64 = landingpad { ptr, i32 }
          filter [0 x ptr] zeroinitializer
; call core::panicking::panic_in_cleanup
  call void @_RNvNtCsjIpoRzUjyHQ_4core9panicking16panic_in_cleanup() #35, !dbg !243031
  unreachable, !dbg !243031

bb15:                                             ; preds = %bb14
; invoke core::ptr::drop_glue::<std::fs::File>
  invoke void @_RINvNtCsjIpoRzUjyHQ_4core3ptr9drop_glueNtNtCs1SSuMAdGM58_3std2fs4FileECscBrn2zMo5wc_8mixer_vm(ptr align 4 %_47) #34
          to label %bb16 unwind label %terminate, !dbg !243020

bb16:                                             ; preds = %bb15
; invoke core::ptr::drop_glue::<std::fs::File>
  invoke void @_RINvNtCsjIpoRzUjyHQ_4core3ptr9drop_glueNtNtCs1SSuMAdGM58_3std2fs4FileECscBrn2zMo5wc_8mixer_vm(ptr align 4 %_46) #34
          to label %bb24 unwind label %terminate, !dbg !243020

bb23:                                             ; preds = %bb24
; invoke core::ptr::drop_glue::<mixer_vm::experimental_swift_reactor::retained_profile_loader_v1::prepaid_input_owner_v1::OwnedCorrelationOutcomeV1>
  invoke void @_RINvNtCsjIpoRzUjyHQ_4core3ptr9drop_glueNtNtNtNtCscBrn2zMo5wc_8mixer_vm26experimental_swift_reactor26retained_profile_loader_v122prepaid_input_owner_v125OwnedCorrelationOutcomeV1EBJ_(ptr align 8 %correlated) #34
          to label %bb26 unwind label %terminate, !dbg !243027

bb25:                                             ; preds = %bb26
; invoke core::ptr::drop_glue::<mixer_vm::execute::Cancellation>
  invoke void @_RINvNtCsjIpoRzUjyHQ_4core3ptr9drop_glueNtNtCscBrn2zMo5wc_8mixer_vm7execute12CancellationEBF_(ptr align 8 %cancellation) #34
          to label %bb28 unwind label %terminate, !dbg !243008

bb17:                                             ; preds = %bb27, %bb28
  %65 = load i8, ptr %_63, align 1, !dbg !243001
  %66 = trunc nuw i8 %65 to i1, !dbg !243001
  br i1 %66, label %bb29, label %bb18, !dbg !243001

bb27:                                             ; preds = %bb28
; invoke core::ptr::drop_glue::<std::fs::File>
  invoke void @_RINvNtCsjIpoRzUjyHQ_4core3ptr9drop_glueNtNtCs1SSuMAdGM58_3std2fs4FileECscBrn2zMo5wc_8mixer_vm(ptr align 4 %snapshot) #34
          to label %bb17 unwind label %terminate, !dbg !243001

bb18:                                             ; preds = %bb29, %bb17
  %67 = load i8, ptr %_64, align 1, !dbg !243001
  %68 = trunc nuw i8 %67 to i1, !dbg !243001
  br i1 %68, label %bb30, label %bb19, !dbg !243001

bb29:                                             ; preds = %bb17
; invoke core::ptr::drop_glue::<std::fs::File>
  invoke void @_RINvNtCsjIpoRzUjyHQ_4core3ptr9drop_glueNtNtCs1SSuMAdGM58_3std2fs4FileECscBrn2zMo5wc_8mixer_vm(ptr align 4 %rows) #34
          to label %bb18 unwind label %terminate, !dbg !243001

bb19:                                             ; preds = %bb30, %bb18
  %69 = load i8, ptr %_65, align 1, !dbg !243001
  %70 = trunc nuw i8 %69 to i1, !dbg !243001
  br i1 %70, label %bb31, label %bb20, !dbg !243001

bb30:                                             ; preds = %bb18
; invoke core::ptr::drop_glue::<std::fs::File>
  invoke void @_RINvNtCsjIpoRzUjyHQ_4core3ptr9drop_glueNtNtCs1SSuMAdGM58_3std2fs4FileECscBrn2zMo5wc_8mixer_vm(ptr align 4 %session) #34
          to label %bb19 unwind label %terminate, !dbg !243001

bb20:                                             ; preds = %bb31, %bb19
  %71 = load i8, ptr %_66, align 1, !dbg !243001
  %72 = trunc nuw i8 %71 to i1, !dbg !243001
  br i1 %72, label %bb32, label %bb21, !dbg !243001

bb31:                                             ; preds = %bb19
; invoke core::ptr::drop_glue::<std::fs::File>
  invoke void @_RINvNtCsjIpoRzUjyHQ_4core3ptr9drop_glueNtNtCs1SSuMAdGM58_3std2fs4FileECscBrn2zMo5wc_8mixer_vm(ptr align 4 %build) #34
          to label %bb20 unwind label %terminate, !dbg !243001

bb21:                                             ; preds = %bb32, %bb20
  %73 = load ptr, ptr %0, align 8, !dbg !243031
  %74 = getelementptr inbounds i8, ptr %0, i64 8, !dbg !243031
  %75 = load i32, ptr %74, align 8, !dbg !243031
  %76 = insertvalue { ptr, i32 } poison, ptr %73, 0, !dbg !243031
  %77 = insertvalue { ptr, i32 } %76, i32 %75, 1, !dbg !243031
  resume { ptr, i32 } %77, !dbg !243031

bb32:                                             ; preds = %bb20
; invoke core::ptr::drop_glue::<std::fs::File>
  invoke void @_RINvNtCsjIpoRzUjyHQ_4core3ptr9drop_glueNtNtCs1SSuMAdGM58_3std2fs4FileECscBrn2zMo5wc_8mixer_vm(ptr align 4 %source) #34
          to label %bb21 unwind label %terminate, !dbg !243001
}
