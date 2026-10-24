import collect as c
code,attempt,out,err=c.run(['cargo','rustc','--lib','--offline','--locked','--features','experimental-swift-reactor','--release','--','--test','--emit=llvm-ir,mir','-Cdebuginfo=2','-Zprint-type-sizes'],env_extra={'RUSTC_BOOTSTRAP':'1'},label='unqualified-actual-pointer-debug-layout-probe')
c.save(c.HERE/'pointer-debug-probe.json',{'attempt':str(attempt.relative_to(c.HERE)),'exitCode':code,'purpose':'Compiler layout/DIType research only; no runtime/accounting acceptance'})
raise SystemExit(code)
