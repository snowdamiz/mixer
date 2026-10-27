; ModuleID = 'mixer_cancellation_backing_probe.c03e0af6f6aa3d94-cgu.0'
source_filename = "mixer_cancellation_backing_probe.c03e0af6f6aa3d94-cgu.0"
target datalayout = "e-m:o-p270:32:32-p271:32:32-p272:64:64-i64:64-i128:128-n32:64-S128-Fn32"
target triple = "arm64-apple-macosx11.0.0"

@alloc_9778b29bb092c0993288f5533477a993 = private unnamed_addr constant [81 x i8] c"/rustc/b940084d7eb6a299eb4bfeb8e34901bc051e7ac4/library/core/src/ptr/non_null.rs\00", align 1, !guid !0
@alloc_89d05837d276d0cdfd4c260831511c04 = private unnamed_addr constant <{ ptr, [16 x i8] }> <{ ptr @alloc_9778b29bb092c0993288f5533477a993, [16 x i8] c"P\00\00\00\00\00\00\00s\05\00\00\12\00\00\00" }>, align 8, !guid !1
@alloc_42d21bfaec1bba234f156b2b56f45133 = private unnamed_addr constant <{ ptr, [16 x i8] }> <{ ptr @alloc_9778b29bb092c0993288f5533477a993, [16 x i8] c"P\00\00\00\00\00\00\00\1A\01\00\00\1B\00\00\00" }>, align 8, !guid !2
@anon.6aa94c750093c64b32c6e50bc28cbe52.0 = private unnamed_addr constant <{ [8 x i8], [8 x i8] }> <{ [8 x i8] zeroinitializer, [8 x i8] undef }>, align 8, !guid !3
@alloc_0625062a5eee489a7813ee965a38d15a = private unnamed_addr constant [198 x i8] c"unsafe precondition(s) violated: Alignment::new_unchecked requires a power of two\0A\0AThis indicates a bug in the program. This Undefined Behavior check is optional, and cannot be relied on for safety.", align 1, !guid !4
@alloc_8cf3531fd3c828ab298b686071a40c17 = private unnamed_addr constant [259 x i8] c"unsafe precondition(s) violated: Layout::from_size_alignment_unchecked requires that the rounded-up allocation size does not exceed isize::MAX\0A\0AThis indicates a bug in the program. This Undefined Behavior check is optional, and cannot be relied on for safety.", align 1, !guid !5
@alloc_560a59ed819b9d9a5841f6e731c4c8e5 = private unnamed_addr constant [210 x i8] c"unsafe precondition(s) violated: NonNull::new_unchecked requires that the pointer is non-null\0A\0AThis indicates a bug in the program. This Undefined Behavior check is optional, and cannot be relied on for safety.", align 1, !guid !6
@alloc_901a36ead99fe1463b370edb0a355d15 = private unnamed_addr constant [82 x i8] c"/rustc/b940084d7eb6a299eb4bfeb8e34901bc051e7ac4/library/core/src/mem/alignment.rs\00", align 1, !guid !7
@alloc_21638e96aac27d76ebe40436bb00eaf1 = private unnamed_addr constant <{ ptr, [16 x i8] }> <{ ptr @alloc_901a36ead99fe1463b370edb0a355d15, [16 x i8] c"Q\00\00\00\00\00\00\00\A1\00\00\00\12\00\00\00" }>, align 8, !guid !8
@alloc_88aa0571be7aec206dfc028f1aad5be8 = private unnamed_addr constant [81 x i8] c"/rustc/b940084d7eb6a299eb4bfeb8e34901bc051e7ac4/library/core/src/alloc/layout.rs\00", align 1, !guid !9
@alloc_e75a54210833615cb5b769aaa07a68b3 = private unnamed_addr constant <{ ptr, [16 x i8] }> <{ ptr @alloc_88aa0571be7aec206dfc028f1aad5be8, [16 x i8] c"P\00\00\00\00\00\00\00\07\01\00\00\12\00\00\00" }>, align 8, !guid !10

; core::ptr::drop_glue::<alloc::boxed::Box<core::mem::maybe_uninit::MaybeUninit<alloc::sync::ArcInner<core::sync::atomic::Atomic<bool>>>>>
; Function Attrs: uwtable
define void @_RINvNtCsjIpoRzUjyHQ_4core3ptr9drop_glueINtNtCs6zY7rJBZy9D_5alloc5boxed3BoxINtNtNtB4_3mem12maybe_uninit11MaybeUninitINtNtBG_4sync8ArcInnerINtNtNtB4_4sync6atomic6AtomicbEEEEECsgviH8iF24Iq_32mixer_cancellation_backing_probe(ptr align 8 %_1) unnamed_addr #0 personality ptr @rust_eh_personality !guid !15 {
start:
  %0 = alloca [16 x i8], align 8
  %_6 = load ptr, ptr %_1, align 8
  br label %bb3

bb3:                                              ; preds = %start
; call <alloc::boxed::Box<core::mem::maybe_uninit::MaybeUninit<alloc::sync::ArcInner<core::sync::atomic::Atomic<bool>>>> as core::ops::drop::Drop>::drop
  call void @_RNvXs8_NtCs6zY7rJBZy9D_5alloc5boxedINtB5_3BoxINtNtNtCsjIpoRzUjyHQ_4core3mem12maybe_uninit11MaybeUninitINtNtB7_4sync8ArcInnerINtNtNtBO_4sync6atomic6AtomicbEEEENtNtNtBO_3ops4drop4Drop4dropCsgviH8iF24Iq_32mixer_cancellation_backing_probe(ptr align 8 %_1) #13
  ret void

bb4:                                              ; No predecessors!
; invoke <alloc::boxed::Box<core::mem::maybe_uninit::MaybeUninit<alloc::sync::ArcInner<core::sync::atomic::Atomic<bool>>>> as core::ops::drop::Drop>::drop
  invoke void @_RNvXs8_NtCs6zY7rJBZy9D_5alloc5boxedINtB5_3BoxINtNtNtCsjIpoRzUjyHQ_4core3mem12maybe_uninit11MaybeUninitINtNtB7_4sync8ArcInnerINtNtNtBO_4sync6atomic6AtomicbEEEENtNtNtBO_3ops4drop4Drop4dropCsgviH8iF24Iq_32mixer_cancellation_backing_probe(ptr align 8 %_1) #14
          to label %bb2 unwind label %terminate

terminate:                                        ; preds = %bb4
  %1 = landingpad { ptr, i32 }
          filter [0 x ptr] zeroinitializer
; call core::panicking::panic_in_cleanup
  call void @_RNvNtCsjIpoRzUjyHQ_4core9panicking16panic_in_cleanup() #15
  unreachable

bb2:                                              ; preds = %bb4
  %2 = load ptr, ptr %0, align 8
  %3 = getelementptr inbounds i8, ptr %0, i64 8
  %4 = load i32, ptr %3, align 8
  %5 = insertvalue { ptr, i32 } poison, ptr %2, 0
  %6 = insertvalue { ptr, i32 } %5, i32 %4, 1
  resume { ptr, i32 } %6
}

; <alloc::alloc::Global>::alloc_impl_runtime
; Function Attrs: inlinehint uwtable
define internal { ptr, i64 } @_RNvMs0_NtCs6zY7rJBZy9D_5alloc5allocNtB5_6Global18alloc_impl_runtimeCsgviH8iF24Iq_32mixer_cancellation_backing_probe(i64 %layout.0, i64 %layout.1, i1 zeroext %zeroed) unnamed_addr #1 !guid !16 {
start:
  %self1 = alloca [8 x i8], align 8
  %self = alloca [8 x i8], align 8
  %_9 = alloca [8 x i8], align 8
  %raw_ptr = alloca [8 x i8], align 8
  %_0 = alloca [16 x i8], align 8
  %0 = icmp eq i64 %layout.1, 0
  br i1 %0, label %bb2, label %bb1

bb2:                                              ; preds = %start
  %self2 = inttoptr i64 %layout.0 to ptr
  %self3 = inttoptr i64 %layout.0 to ptr
  br label %bb8

bb1:                                              ; preds = %start
  br i1 %zeroed, label %bb3, label %bb4

bb8:                                              ; preds = %bb2
  %_19 = inttoptr i64 %layout.0 to ptr
; call <core::ptr::non_null::NonNull<_>>::new_unchecked::precondition_check
  call void @_RNvNvMs1_NtNtCsjIpoRzUjyHQ_4core3ptr8non_nullINtB7_7NonNullpE13new_unchecked18precondition_checkCsgviH8iF24Iq_32mixer_cancellation_backing_probe(ptr %_19, ptr align 8 @alloc_89d05837d276d0cdfd4c260831511c04) #16
  br label %bb10

bb10:                                             ; preds = %bb8
  store ptr %self3, ptr %_0, align 8
  %1 = getelementptr inbounds i8, ptr %_0, i64 8
  store i64 0, ptr %1, align 8
  br label %bb6

bb6:                                              ; preds = %bb22, %bb10
  br label %bb7

bb4:                                              ; preds = %bb1
; call __rustc::__rust_no_alloc_shim_is_unstable_v2
  call void @_RNvCsdtSMxSA38aw_7___rustc35___rust_no_alloc_shim_is_unstable_v2() #17
; call __rustc::__rust_alloc
  %2 = call ptr @_RNvCsdtSMxSA38aw_7___rustc12___rust_alloc(i64 %layout.1, i64 %layout.0) #17
  store ptr %2, ptr %raw_ptr, align 8
  br label %bb5

bb3:                                              ; preds = %bb1
; call __rustc::__rust_no_alloc_shim_is_unstable_v2
  call void @_RNvCsdtSMxSA38aw_7___rustc35___rust_no_alloc_shim_is_unstable_v2() #17
; call __rustc::__rust_alloc_zeroed
  %3 = call ptr @_RNvCsdtSMxSA38aw_7___rustc19___rust_alloc_zeroed(i64 %layout.1, i64 %layout.0) #17
  store ptr %3, ptr %raw_ptr, align 8
  br label %bb5

bb5:                                              ; preds = %bb3, %bb4
  %4 = load ptr, ptr %raw_ptr, align 8
  %_30 = ptrtoint ptr %4 to i64
  %_28 = icmp eq i64 %_30, 0
  br i1 %_28, label %bb15, label %bb16

bb16:                                             ; preds = %bb5
  br label %bb17

bb15:                                             ; preds = %bb5
  store ptr null, ptr %self1, align 8
  store ptr null, ptr %self, align 8
  %5 = load ptr, ptr @anon.6aa94c750093c64b32c6e50bc28cbe52.0, align 8
  %6 = load i64, ptr getelementptr inbounds (i8, ptr @anon.6aa94c750093c64b32c6e50bc28cbe52.0, i64 8), align 8
  store ptr %5, ptr %_0, align 8
  %7 = getelementptr inbounds i8, ptr %_0, i64 8
  store i64 %6, ptr %7, align 8
  br label %bb7

bb17:                                             ; preds = %bb16
  %_32 = load ptr, ptr %raw_ptr, align 8
; call <core::ptr::non_null::NonNull<_>>::new_unchecked::precondition_check
  call void @_RNvNvMs1_NtNtCsjIpoRzUjyHQ_4core3ptr8non_nullINtB7_7NonNullpE13new_unchecked18precondition_checkCsgviH8iF24Iq_32mixer_cancellation_backing_probe(ptr %_32, ptr align 8 @alloc_42d21bfaec1bba234f156b2b56f45133) #16
  br label %bb19

bb19:                                             ; preds = %bb17
  %_29 = load ptr, ptr %raw_ptr, align 8
  store ptr %_29, ptr %self1, align 8
  %v = load ptr, ptr %self1, align 8
  store ptr %v, ptr %self, align 8
  %v4 = load ptr, ptr %self, align 8
  store ptr %v4, ptr %_9, align 8
  %ptr = load ptr, ptr %_9, align 8
  br label %bb20

bb20:                                             ; preds = %bb19
; call <core::ptr::non_null::NonNull<_>>::new_unchecked::precondition_check
  call void @_RNvNvMs1_NtNtCsjIpoRzUjyHQ_4core3ptr8non_nullINtB7_7NonNullpE13new_unchecked18precondition_checkCsgviH8iF24Iq_32mixer_cancellation_backing_probe(ptr %ptr, ptr align 8 @alloc_89d05837d276d0cdfd4c260831511c04) #16
  br label %bb22

bb22:                                             ; preds = %bb20
  store ptr %ptr, ptr %_0, align 8
  %8 = getelementptr inbounds i8, ptr %_0, i64 8
  store i64 %layout.1, ptr %8, align 8
  br label %bb6

bb7:                                              ; preds = %bb15, %bb6
  %9 = load ptr, ptr %_0, align 8
  %10 = getelementptr inbounds i8, ptr %_0, i64 8
  %11 = load i64, ptr %10, align 8
  %12 = insertvalue { ptr, i64 } poison, ptr %9, 0
  %13 = insertvalue { ptr, i64 } %12, i64 %11, 1
  ret { ptr, i64 } %13
}

; alloc::boxed::box_new_uninit
; Function Attrs: inlinehint uwtable
define internal ptr @_RNvNtCs6zY7rJBZy9D_5alloc5boxed14box_new_uninitCsgviH8iF24Iq_32mixer_cancellation_backing_probe(i64 %layout.0, i64 %layout.1) unnamed_addr #1 !guid !17 {
start:
  %_2 = alloca [16 x i8], align 8
; call <alloc::alloc::Global>::alloc_impl_runtime
  %0 = call { ptr, i64 } @_RNvMs0_NtCs6zY7rJBZy9D_5alloc5allocNtB5_6Global18alloc_impl_runtimeCsgviH8iF24Iq_32mixer_cancellation_backing_probe(i64 %layout.0, i64 %layout.1, i1 zeroext false) #13
  %1 = extractvalue { ptr, i64 } %0, 0
  %2 = extractvalue { ptr, i64 } %0, 1
  store ptr %1, ptr %_2, align 8
  %3 = getelementptr inbounds i8, ptr %_2, i64 8
  store i64 %2, ptr %3, align 8
  %4 = load ptr, ptr %_2, align 8
  %5 = getelementptr inbounds i8, ptr %_2, i64 8
  %6 = load i64, ptr %5, align 8
  %7 = ptrtoint ptr %4 to i64
  %8 = icmp eq i64 %7, 0
  %_3 = select i1 %8, i64 1, i64 0
  %9 = trunc nuw i64 %_3 to i1
  br i1 %9, label %bb2, label %bb3

bb2:                                              ; preds = %start
; call alloc::alloc::handle_alloc_error
  call void @_RNvNtCs6zY7rJBZy9D_5alloc5alloc18handle_alloc_error(i64 %layout.0, i64 %layout.1) #18
  unreachable

bb3:                                              ; preds = %start
  %ptr.0 = load ptr, ptr %_2, align 8
  %10 = getelementptr inbounds i8, ptr %_2, i64 8
  %ptr.1 = load i64, ptr %10, align 8
  ret ptr %ptr.0

bb1:                                              ; No predecessors!
  unreachable
}

; <core::mem::alignment::Alignment>::new_unchecked::precondition_check
; Function Attrs: inlinehint nounwind uwtable
define internal void @_RNvNvMNtNtCsjIpoRzUjyHQ_4core3mem9alignmentNtB4_9Alignment13new_unchecked18precondition_checkCsgviH8iF24Iq_32mixer_cancellation_backing_probe(i64 %align, ptr align 8 %0) unnamed_addr #2 !guid !18 {
start:
  %1 = call i64 @llvm.ctpop.i64(i64 %align)
  %_6 = trunc i64 %1 to i32
  %_2 = icmp eq i32 %_6, 1
  br i1 %_2, label %bb1, label %bb2

bb2:                                              ; preds = %start
; call core::panicking::panic_nounwind_fmt
  call void @_RNvNtCsjIpoRzUjyHQ_4core9panicking18panic_nounwind_fmt(ptr @alloc_0625062a5eee489a7813ee965a38d15a, ptr inttoptr (i64 397 to ptr), i1 zeroext false, ptr align 8 %0) #19
  unreachable

bb1:                                              ; preds = %start
  ret void
}

; <core::alloc::layout::Layout>::from_size_alignment_unchecked::precondition_check
; Function Attrs: inlinehint nounwind uwtable
define internal void @_RNvNvMNtNtCsjIpoRzUjyHQ_4core5alloc6layoutNtB4_6Layout29from_size_alignment_unchecked18precondition_checkCsgviH8iF24Iq_32mixer_cancellation_backing_probe(i64 %size, i64 %alignment, ptr align 8 %0) unnamed_addr #2 !guid !19 {
start:
  %_7 = sub nuw i64 -9223372036854775808, %alignment
  %_3 = icmp ule i64 %size, %_7
  br i1 %_3, label %bb1, label %bb2

bb2:                                              ; preds = %start
; call core::panicking::panic_nounwind_fmt
  call void @_RNvNtCsjIpoRzUjyHQ_4core9panicking18panic_nounwind_fmt(ptr @alloc_8cf3531fd3c828ab298b686071a40c17, ptr inttoptr (i64 519 to ptr), i1 zeroext false, ptr align 8 %0) #19
  unreachable

bb1:                                              ; preds = %start
  ret void
}

; <core::ptr::non_null::NonNull<_>>::new_unchecked::precondition_check
; Function Attrs: inlinehint nounwind uwtable
define internal void @_RNvNvMs1_NtNtCsjIpoRzUjyHQ_4core3ptr8non_nullINtB7_7NonNullpE13new_unchecked18precondition_checkCsgviH8iF24Iq_32mixer_cancellation_backing_probe(ptr %ptr, ptr align 8 %0) unnamed_addr #2 !guid !20 {
start:
  %_6 = ptrtoint ptr %ptr to i64
  %_2 = icmp eq i64 %_6, 0
  br i1 %_2, label %bb1, label %bb2

bb2:                                              ; preds = %start
  ret void

bb1:                                              ; preds = %start
; call core::panicking::panic_nounwind_fmt
  call void @_RNvNtCsjIpoRzUjyHQ_4core9panicking18panic_nounwind_fmt(ptr @alloc_560a59ed819b9d9a5841f6e731c4c8e5, ptr inttoptr (i64 421 to ptr), i1 zeroext false, ptr align 8 %0) #19
  unreachable
}

; <mixer_cancellation_backing_probe::Cancellation as core::clone::Clone>::clone
; Function Attrs: inlinehint uwtable
define internal ptr @_RNvXCsgviH8iF24Iq_32mixer_cancellation_backing_probeNtB2_12CancellationNtNtCsjIpoRzUjyHQ_4core5clone5Clone5cloneB2_(ptr align 8 %self) unnamed_addr #1 !guid !21 {
start:
; call <alloc::sync::Arc<core::sync::atomic::Atomic<bool>> as core::clone::Clone>::clone
  %_2 = call ptr @_RNvXsu_NtCs6zY7rJBZy9D_5alloc4syncINtB5_3ArcINtNtNtCsjIpoRzUjyHQ_4core4sync6atomic6AtomicbEENtNtBN_5clone5Clone5cloneCsgviH8iF24Iq_32mixer_cancellation_backing_probe(ptr align 8 %self) #13
  ret ptr %_2
}

; <core::sync::atomic::Atomic<bool> as core::default::Default>::default
; Function Attrs: inlinehint uwtable
define internal i8 @_RNvXs0_NtNtCsjIpoRzUjyHQ_4core4sync6atomicINtB5_6AtomicbENtNtB9_7default7Default7defaultCsgviH8iF24Iq_32mixer_cancellation_backing_probe() unnamed_addr #1 !guid !22 {
start:
  %_0 = alloca [1 x i8], align 1
  store i8 0, ptr %_0, align 1
  %0 = load i8, ptr %_0, align 1
  ret i8 %0
}

; <alloc::alloc::Global as core::alloc::Allocator>::deallocate
; Function Attrs: inlinehint uwtable
define internal void @_RNvXs1_NtCs6zY7rJBZy9D_5alloc5allocNtB5_6GlobalNtNtCsjIpoRzUjyHQ_4core5alloc9Allocator10deallocateCsgviH8iF24Iq_32mixer_cancellation_backing_probe(ptr %self, ptr %ptr, i64 %layout.0, i64 %layout.1) unnamed_addr #1 !guid !23 {
start:
  %0 = icmp eq i64 %layout.1, 0
  br i1 %0, label %bb2, label %bb1

bb2:                                              ; preds = %bb1, %start
  ret void

bb1:                                              ; preds = %start
; call __rustc::__rust_dealloc
  call void @_RNvCsdtSMxSA38aw_7___rustc14___rust_dealloc(ptr %ptr, i64 %layout.1, i64 %layout.0) #17
  br label %bb2
}

; <alloc::alloc::Global as core::clone::Clone>::clone
; Function Attrs: inlinehint uwtable
define internal void @_RNvXs5_NtCs6zY7rJBZy9D_5alloc5allocNtB5_6GlobalNtNtCsjIpoRzUjyHQ_4core5clone5Clone5cloneCsgviH8iF24Iq_32mixer_cancellation_backing_probe(ptr %self) unnamed_addr #1 !guid !24 {
start:
  ret void
}

; <alloc::boxed::Box<core::mem::maybe_uninit::MaybeUninit<alloc::sync::ArcInner<core::sync::atomic::Atomic<bool>>>> as core::ops::drop::Drop>::drop
; Function Attrs: inlinehint uwtable
define void @_RNvXs8_NtCs6zY7rJBZy9D_5alloc5boxedINtB5_3BoxINtNtNtCsjIpoRzUjyHQ_4core3mem12maybe_uninit11MaybeUninitINtNtB7_4sync8ArcInnerINtNtNtBO_4sync6atomic6AtomicbEEEENtNtNtBO_3ops4drop4Drop4dropCsgviH8iF24Iq_32mixer_cancellation_backing_probe(ptr align 8 %self) unnamed_addr #1 !guid !25 {
start:
  %ptr = load ptr, ptr %self, align 8
  br label %bb6

bb6:                                              ; preds = %start
; call <core::mem::alignment::Alignment>::new_unchecked::precondition_check
  call void @_RNvNvMNtNtCsjIpoRzUjyHQ_4core3mem9alignmentNtB4_9Alignment13new_unchecked18precondition_checkCsgviH8iF24Iq_32mixer_cancellation_backing_probe(i64 8, ptr align 8 @alloc_21638e96aac27d76ebe40436bb00eaf1) #16
  br label %bb7

bb7:                                              ; preds = %bb6
  br label %bb8

bb8:                                              ; preds = %bb7
; call <core::alloc::layout::Layout>::from_size_alignment_unchecked::precondition_check
  call void @_RNvNvMNtNtCsjIpoRzUjyHQ_4core5alloc6layoutNtB4_6Layout29from_size_alignment_unchecked18precondition_checkCsgviH8iF24Iq_32mixer_cancellation_backing_probe(i64 24, i64 8, ptr align 8 @alloc_e75a54210833615cb5b769aaa07a68b3) #16
  br label %bb9

bb9:                                              ; preds = %bb8
  br label %bb1

bb1:                                              ; preds = %bb9
  %_7 = getelementptr inbounds i8, ptr %self, i64 8
; call <alloc::alloc::Global as core::alloc::Allocator>::deallocate
  call void @_RNvXs1_NtCs6zY7rJBZy9D_5alloc5allocNtB5_6GlobalNtNtCsjIpoRzUjyHQ_4core5alloc9Allocator10deallocateCsgviH8iF24Iq_32mixer_cancellation_backing_probe(ptr %_7, ptr %ptr, i64 8, i64 24) #13
  br label %bb3

bb3:                                              ; preds = %bb1
  ret void
}

; <alloc::sync::Arc<core::sync::atomic::Atomic<bool>> as core::default::Default>::default
; Function Attrs: uwtable
define ptr @_RNvXsY_NtCs6zY7rJBZy9D_5alloc4syncINtB5_3ArcINtNtNtCsjIpoRzUjyHQ_4core4sync6atomic6AtomicbEENtNtBN_7default7Default7defaultCsgviH8iF24Iq_32mixer_cancellation_backing_probe() unnamed_addr #0 personality ptr @rust_eh_personality !guid !26 {
start:
  %0 = alloca [1 x i8], align 1
  %1 = alloca [16 x i8], align 8
  %_11 = alloca [24 x i8], align 8
  %_10 = alloca [24 x i8], align 8
  %_9 = alloca [24 x i8], align 8
  %_6 = alloca [1 x i8], align 1
  %_5 = alloca [8 x i8], align 8
  %value = alloca [24 x i8], align 8
  %boxed = alloca [8 x i8], align 8
; call alloc::boxed::box_new_uninit
  %_7 = call ptr @_RNvNtCs6zY7rJBZy9D_5alloc5boxed14box_new_uninitCsgviH8iF24Iq_32mixer_cancellation_backing_probe(i64 8, i64 24) #13
  store ptr %_7, ptr %boxed, align 8
  store i64 1, ptr %_5, align 8
; invoke <core::sync::atomic::Atomic<bool> as core::default::Default>::default
  %2 = invoke i8 @_RNvXs0_NtNtCsjIpoRzUjyHQ_4core4sync6atomicINtB5_6AtomicbENtNtB9_7default7Default7defaultCsgviH8iF24Iq_32mixer_cancellation_backing_probe()
          to label %bb1 unwind label %cleanup

bb3:                                              ; preds = %cleanup
; invoke core::ptr::drop_glue::<alloc::boxed::Box<core::mem::maybe_uninit::MaybeUninit<alloc::sync::ArcInner<core::sync::atomic::Atomic<bool>>>>>
  invoke void @_RINvNtCsjIpoRzUjyHQ_4core3ptr9drop_glueINtNtCs6zY7rJBZy9D_5alloc5boxed3BoxINtNtNtB4_3mem12maybe_uninit11MaybeUninitINtNtBG_4sync8ArcInnerINtNtNtB4_4sync6atomic6AtomicbEEEEECsgviH8iF24Iq_32mixer_cancellation_backing_probe(ptr align 8 %boxed) #14
          to label %bb2 unwind label %terminate

cleanup:                                          ; preds = %start
  %3 = landingpad { ptr, i32 }
          cleanup
  %4 = extractvalue { ptr, i32 } %3, 0
  %5 = extractvalue { ptr, i32 } %3, 1
  store ptr %4, ptr %1, align 8
  %6 = getelementptr inbounds i8, ptr %1, i64 8
  store i32 %5, ptr %6, align 8
  br label %bb3

bb1:                                              ; preds = %start
  store i8 %2, ptr %0, align 1
  call void @llvm.memcpy.p0.p0.i64(ptr align 1 %_6, ptr align 1 %0, i64 1, i1 false)
  call void @llvm.memcpy.p0.p0.i64(ptr align 8 %value, ptr align 8 %_5, i64 8, i1 false)
  %7 = getelementptr inbounds i8, ptr %value, i64 8
  call void @llvm.memcpy.p0.p0.i64(ptr align 8 %7, ptr align 8 %_5, i64 8, i1 false)
  %8 = getelementptr inbounds i8, ptr %value, i64 16
  call void @llvm.memcpy.p0.p0.i64(ptr align 8 %8, ptr align 1 %_6, i64 1, i1 false)
  %self = load ptr, ptr %boxed, align 8
  call void @llvm.memcpy.p0.p0.i64(ptr align 8 %_11, ptr align 8 %value, i64 24, i1 false)
  call void @llvm.memcpy.p0.p0.i64(ptr align 8 %_10, ptr align 8 %_11, i64 24, i1 false)
  call void @llvm.memcpy.p0.p0.i64(ptr align 8 %_9, ptr align 8 %_10, i64 24, i1 false)
  call void @llvm.memcpy.p0.p0.i64(ptr align 8 %self, ptr align 8 %_9, i64 24, i1 false)
  %b = load ptr, ptr %boxed, align 8
  ret ptr %b

terminate:                                        ; preds = %bb3
  %9 = landingpad { ptr, i32 }
          filter [0 x ptr] zeroinitializer
; call core::panicking::panic_in_cleanup
  call void @_RNvNtCsjIpoRzUjyHQ_4core9panicking16panic_in_cleanup() #15
  unreachable

bb2:                                              ; preds = %bb3
  %10 = load ptr, ptr %1, align 8
  %11 = getelementptr inbounds i8, ptr %1, i64 8
  %12 = load i32, ptr %11, align 8
  %13 = insertvalue { ptr, i32 } poison, ptr %10, 0
  %14 = insertvalue { ptr, i32 } %13, i32 %12, 1
  resume { ptr, i32 } %14
}

; <mixer_cancellation_backing_probe::Cancellation as core::default::Default>::default
; Function Attrs: inlinehint uwtable
define internal ptr @_RNvXs_CsgviH8iF24Iq_32mixer_cancellation_backing_probeNtB4_12CancellationNtNtCsjIpoRzUjyHQ_4core7default7Default7defaultB4_() unnamed_addr #1 !guid !27 {
start:
; call <alloc::sync::Arc<core::sync::atomic::Atomic<bool>> as core::default::Default>::default
  %_1 = call ptr @_RNvXsY_NtCs6zY7rJBZy9D_5alloc4syncINtB5_3ArcINtNtNtCsjIpoRzUjyHQ_4core4sync6atomic6AtomicbEENtNtBN_7default7Default7defaultCsgviH8iF24Iq_32mixer_cancellation_backing_probe()
  ret ptr %_1
}

; <alloc::sync::Arc<core::sync::atomic::Atomic<bool>> as core::clone::Clone>::clone
; Function Attrs: inlinehint uwtable
define ptr @_RNvXsu_NtCs6zY7rJBZy9D_5alloc4syncINtB5_3ArcINtNtNtCsjIpoRzUjyHQ_4core4sync6atomic6AtomicbEENtNtBN_5clone5Clone5cloneCsgviH8iF24Iq_32mixer_cancellation_backing_probe(ptr align 8 %self) unnamed_addr #1 !guid !28 {
start:
  %_10 = load ptr, ptr %self, align 8
  %old_size = atomicrmw add ptr %_10, i64 1 monotonic, align 8
  %_4 = icmp ugt i64 %old_size, 9223372036854775807
  br i1 %_4, label %bb1, label %bb2

bb2:                                              ; preds = %start
  %ptr = load ptr, ptr %self, align 8
  %_8 = getelementptr inbounds i8, ptr %self, i64 8
; call <alloc::alloc::Global as core::clone::Clone>::clone
  call void @_RNvXs5_NtCs6zY7rJBZy9D_5alloc5allocNtB5_6GlobalNtNtCsjIpoRzUjyHQ_4core5clone5Clone5cloneCsgviH8iF24Iq_32mixer_cancellation_backing_probe(ptr %_8) #13
  ret ptr %ptr

bb1:                                              ; preds = %start
  call void @llvm.trap()
  unreachable
}

; Function Attrs: uwtable
define ptr @mixer_probe_cancellation_clone(ptr align 8 %value) unnamed_addr #0 !guid !29 {
start:
; call <mixer_cancellation_backing_probe::Cancellation as core::clone::Clone>::clone
  %_0 = call ptr @_RNvXCsgviH8iF24Iq_32mixer_cancellation_backing_probeNtB2_12CancellationNtNtCsjIpoRzUjyHQ_4core5clone5Clone5cloneB2_(ptr align 8 %value) #13
  ret ptr %_0
}

; Function Attrs: uwtable
define ptr @mixer_probe_cancellation_default() unnamed_addr #0 !guid !30 {
start:
; call <mixer_cancellation_backing_probe::Cancellation as core::default::Default>::default
  %_0 = call ptr @_RNvXs_CsgviH8iF24Iq_32mixer_cancellation_backing_probeNtB4_12CancellationNtNtCsjIpoRzUjyHQ_4core7default7Default7defaultB4_() #13
  ret ptr %_0
}

; Function Attrs: nounwind uwtable
declare i32 @rust_eh_personality(i32, i32, i64, ptr, ptr) unnamed_addr #3

; core::panicking::panic_in_cleanup
; Function Attrs: cold minsize noinline noreturn nounwind optsize uwtable
declare void @_RNvNtCsjIpoRzUjyHQ_4core9panicking16panic_in_cleanup() unnamed_addr #4

; __rustc::__rust_no_alloc_shim_is_unstable_v2
; Function Attrs: nounwind uwtable
declare void @_RNvCsdtSMxSA38aw_7___rustc35___rust_no_alloc_shim_is_unstable_v2() unnamed_addr #3

; __rustc::__rust_alloc
; Function Attrs: nounwind allockind("alloc,uninitialized,aligned") allocsize(0) uwtable
declare noalias ptr @_RNvCsdtSMxSA38aw_7___rustc12___rust_alloc(i64, i64 allocalign) unnamed_addr #5

; __rustc::__rust_alloc_zeroed
; Function Attrs: nounwind allockind("alloc,zeroed,aligned") allocsize(0) uwtable
declare noalias ptr @_RNvCsdtSMxSA38aw_7___rustc19___rust_alloc_zeroed(i64, i64 allocalign) unnamed_addr #6

; alloc::alloc::handle_alloc_error
; Function Attrs: cold minsize noreturn optsize uwtable
declare void @_RNvNtCs6zY7rJBZy9D_5alloc5alloc18handle_alloc_error(i64, i64) unnamed_addr #7

; Function Attrs: nocallback nocreateundeforpoison nofree nosync nounwind speculatable willreturn memory(none)
declare i64 @llvm.ctpop.i64(i64) #8

; core::panicking::panic_nounwind_fmt
; Function Attrs: cold noinline noreturn nounwind uwtable
declare void @_RNvNtCsjIpoRzUjyHQ_4core9panicking18panic_nounwind_fmt(ptr, ptr, i1 zeroext, ptr align 8) unnamed_addr #9

; __rustc::__rust_dealloc
; Function Attrs: nounwind allockind("free") uwtable
declare void @_RNvCsdtSMxSA38aw_7___rustc14___rust_dealloc(ptr allocptr captures(address), i64, i64) unnamed_addr #10

; Function Attrs: nocallback nofree nosync nounwind willreturn memory(argmem: readwrite)
declare void @llvm.memcpy.p0.p0.i64(ptr noalias writeonly captures(none), ptr noalias readonly captures(none), i64, i1 immarg) #11

; Function Attrs: cold noreturn nounwind memory(inaccessiblemem: write)
declare void @llvm.trap() #12

attributes #0 = { uwtable "frame-pointer"="non-leaf" "probe-stack"="inline-asm" "target-cpu"="apple-m1" }
attributes #1 = { inlinehint uwtable "frame-pointer"="non-leaf" "probe-stack"="inline-asm" "target-cpu"="apple-m1" }
attributes #2 = { inlinehint nounwind uwtable "frame-pointer"="non-leaf" "probe-stack"="inline-asm" "target-cpu"="apple-m1" }
attributes #3 = { nounwind uwtable "frame-pointer"="non-leaf" "probe-stack"="inline-asm" "target-cpu"="apple-m1" }
attributes #4 = { cold minsize noinline noreturn nounwind optsize uwtable "frame-pointer"="non-leaf" "probe-stack"="inline-asm" "target-cpu"="apple-m1" }
attributes #5 = { nounwind allockind("alloc,uninitialized,aligned") allocsize(0) uwtable "alloc-family"="__rust_alloc" "alloc-variant-zeroed"="_RNvCsdtSMxSA38aw_7___rustc19___rust_alloc_zeroed" "frame-pointer"="non-leaf" "probe-stack"="inline-asm" "target-cpu"="apple-m1" }
attributes #6 = { nounwind allockind("alloc,zeroed,aligned") allocsize(0) uwtable "alloc-family"="__rust_alloc" "frame-pointer"="non-leaf" "probe-stack"="inline-asm" "target-cpu"="apple-m1" }
attributes #7 = { cold minsize noreturn optsize uwtable "frame-pointer"="non-leaf" "probe-stack"="inline-asm" "target-cpu"="apple-m1" }
attributes #8 = { nocallback nocreateundeforpoison nofree nosync nounwind speculatable willreturn memory(none) }
attributes #9 = { cold noinline noreturn nounwind uwtable "frame-pointer"="non-leaf" "probe-stack"="inline-asm" "target-cpu"="apple-m1" }
attributes #10 = { nounwind allockind("free") uwtable "alloc-family"="__rust_alloc" "frame-pointer"="non-leaf" "probe-stack"="inline-asm" "target-cpu"="apple-m1" }
attributes #11 = { nocallback nofree nosync nounwind willreturn memory(argmem: readwrite) }
attributes #12 = { cold noreturn nounwind memory(inaccessiblemem: write) }
attributes #13 = { inlinehint }
attributes #14 = { cold }
attributes #15 = { cold noreturn nounwind }
attributes #16 = { inlinehint nounwind }
attributes #17 = { nounwind }
attributes #18 = { noreturn }
attributes #19 = { noinline noreturn nounwind }

!llvm.module.flags = !{!11, !12, !13}
!llvm.ident = !{!14}

!0 = !{i64 5371713162448827385}
!1 = !{i64 1185099059228407235}
!2 = !{i64 1619801905755976542}
!3 = !{i64 -8498120133485010640}
!4 = !{i64 -9000513820923601385}
!5 = !{i64 -7112607756971278406}
!6 = !{i64 2220844092492561971}
!7 = !{i64 -8630652618744957639}
!8 = !{i64 -4675217706760704551}
!9 = !{i64 -7533492919664561563}
!10 = !{i64 4018603388805164471}
!11 = !{i32 8, !"PIC Level", i32 2}
!12 = !{i32 7, !"uwtable", i32 2}
!13 = !{i32 7, !"frame-pointer", i32 1}
!14 = !{!"rustc version 1.99.0 (b940084d7 2026-09-28)"}
!15 = !{i64 7236707351219789763}
!16 = !{i64 1932719672453064525}
!17 = !{i64 -2146286769743881281}
!18 = !{i64 6937364270502244611}
!19 = !{i64 -6010148107751704107}
!20 = !{i64 -7680373692641989659}
!21 = !{i64 -4766644964573361685}
!22 = !{i64 -2298326498067988237}
!23 = !{i64 5360907334034304810}
!24 = !{i64 -789977563726300672}
!25 = !{i64 -3615081746243870262}
!26 = !{i64 7178879669883684991}
!27 = !{i64 8549433727210629593}
!28 = !{i64 -7750864022120768994}
!29 = !{i64 768164572889939174}
!30 = !{i64 6338420004696795789}
