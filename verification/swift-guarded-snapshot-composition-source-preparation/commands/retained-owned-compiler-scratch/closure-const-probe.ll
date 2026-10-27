; ModuleID = 'closure_const_probe.e79b13b149519df8-cgu.0'
source_filename = "closure_const_probe.e79b13b149519df8-cgu.0"
target datalayout = "e-m:o-p270:32:32-p271:32:32-p272:64:64-i64:64-i128:128-n32:64-S128-Fn32"
target triple = "arm64-apple-macosx11.0.0"

@_RNvCsjSPAuLO13Om_19closure_const_probe1B = constant ptr @_RNvCsjSPAuLO13Om_19closure_const_probe5probe, align 8, !guid !0
@llvm.used = appending global [1 x ptr] [ptr @_RNvCsjSPAuLO13Om_19closure_const_probe1B], section "llvm.metadata", !guid !1

; core::mem::size_of_val::<closure_const_probe::probe::{closure#0}>
; Function Attrs: inlinehint uwtable
define i64 @_RINvNtCsjIpoRzUjyHQ_4core3mem11size_of_valNCNvCsjSPAuLO13Om_19closure_const_probe5probe0EBI_(ptr align 8 %val) unnamed_addr #0 !guid !6 {
start:
  ret i64 8
}

; core::mem::align_of_val::<closure_const_probe::probe::{closure#0}>
; Function Attrs: inlinehint uwtable
define i64 @_RINvNtCsjIpoRzUjyHQ_4core3mem12align_of_valNCNvCsjSPAuLO13Om_19closure_const_probe5probe0EBJ_(ptr align 8 %val) unnamed_addr #0 !guid !7 {
start:
  ret i64 8
}

; closure_const_probe::probe
; Function Attrs: uwtable
define void @_RNvCsjSPAuLO13Om_19closure_const_probe5probe(ptr sret([16 x i8]) align 8 %_0, ptr align 8 %m) unnamed_addr #1 !guid !8 {
start:
  %c = alloca [8 x i8], align 8
  store ptr %m, ptr %c, align 8
; call core::mem::size_of_val::<closure_const_probe::probe::{closure#0}>
  %_3 = call i64 @_RINvNtCsjIpoRzUjyHQ_4core3mem11size_of_valNCNvCsjSPAuLO13Om_19closure_const_probe5probe0EBI_(ptr align 8 %c) #2
; call core::mem::align_of_val::<closure_const_probe::probe::{closure#0}>
  %_5 = call i64 @_RINvNtCsjIpoRzUjyHQ_4core3mem12align_of_valNCNvCsjSPAuLO13Om_19closure_const_probe5probe0EBJ_(ptr align 8 %c) #2
  %0 = getelementptr inbounds nuw i64, ptr %_0, i64 0
  store i64 %_3, ptr %0, align 8
  %1 = getelementptr inbounds nuw i64, ptr %_0, i64 1
  store i64 %_5, ptr %1, align 8
  ret void
}

attributes #0 = { inlinehint uwtable "frame-pointer"="non-leaf" "probe-stack"="inline-asm" "target-cpu"="apple-m1" }
attributes #1 = { uwtable "frame-pointer"="non-leaf" "probe-stack"="inline-asm" "target-cpu"="apple-m1" }
attributes #2 = { inlinehint }

!llvm.module.flags = !{!2, !3, !4}
!llvm.ident = !{!5}

!0 = !{i64 8955448124591847567}
!1 = !{i64 -2781390103448774006}
!2 = !{i32 8, !"PIC Level", i32 2}
!3 = !{i32 7, !"uwtable", i32 2}
!4 = !{i32 7, !"frame-pointer", i32 1}
!5 = !{!"rustc version 1.99.0 (b940084d7 2026-09-28)"}
!6 = !{i64 -6971613666430347056}
!7 = !{i64 -932565267724700537}
!8 = !{i64 4016453550606798655}
