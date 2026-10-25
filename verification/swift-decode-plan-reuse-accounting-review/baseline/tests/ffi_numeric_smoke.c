#include "mixer_vm.h"
#include <assert.h>
#include <fenv.h>
#include <stdio.h>
#include <string.h>
int main(void){
    const uint8_t module[]={0,97,115,109,1,0,0,0,1,5,1,96,0,1,124,
        3,2,1,0,7,7,1,3,114,117,110,0,0,10,13,1,11,0,68,0,0,0,0,0,0,248,63,11};
    MixerVmReport report;
    assert(mixer_vm_validate(module,sizeof module,NULL,&report)==1);
    assert(mixer_vm_validate_numeric_v2(module,sizeof module,NULL,&report)==0);
    assert(mixer_vm_invoke_numeric_v2(module,sizeof module,(const uint8_t*)"run",3,NULL,0,NULL,&report)==0);
    assert(report.abi_version==1 && report.value_type==4 && (uint64_t)report.value==UINT64_C(0x3ff8000000000000) && report.fuel_used==2);
    const uint8_t identity[]={0,97,115,109,1,0,0,0,1,6,1,96,1,125,1,125,
        3,2,1,0,7,7,1,3,114,117,110,0,0,10,6,1,4,0,32,0,11};
    MixerVmValue value={3,0,UINT32_C(0xff812345)};
    assert(mixer_vm_invoke(identity,sizeof identity,(const uint8_t*)"run",3,&value,1,NULL,&report)==3);
    assert(mixer_vm_invoke_numeric_v2(identity,sizeof identity,(const uint8_t*)"run",3,&value,1,NULL,&report)==0);
    assert(report.value_type==3 && (uint64_t)report.value==UINT64_C(0xff812345));
    int saved=fegetround();assert(fesetround(FE_UPWARD)==0);
    assert(mixer_vm_invoke_numeric_v2(module,sizeof module,(const uint8_t*)"run",3,NULL,0,NULL,&report)==2);
    assert(strcmp((const char*)report.code,"unsupported_float_environment")==0);
    assert(fesetround(saved)==0);
#if defined(__APPLE__) && defined(__arm64__)
    fenv_t original,changed;assert(fegetenv(&original)==0);changed=original;changed.__fpcr|=__fpcr_flush_to_zero;assert(fesetenv(&changed)==0);
    assert(mixer_vm_invoke_numeric_v2(module,sizeof module,(const uint8_t*)"run",3,NULL,0,NULL,&report)==2);
    assert(strcmp((const char*)report.code,"unsupported_float_environment")==0);assert(fesetenv(&original)==0);
    changed=original;changed.__fpcr|=__fpcr_trap_invalid;assert(fesetenv(&changed)==0);assert(fegetenv(&changed)==0);
    int trap_exercised=0;
    if(changed.__fpcr&__fpcr_trap_invalid){trap_exercised=1;assert(mixer_vm_invoke_numeric_v2(module,sizeof module,(const uint8_t*)"run",3,NULL,0,NULL,&report)==2);assert(strcmp((const char*)report.code,"unsupported_float_environment")==0);}
    assert(fesetenv(&original)==0);
    puts("FP flush-to-zero rejection: exercised");
    puts(trap_exercised?"FP hardware invalid-trap rejection: exercised":"FP hardware invalid-trap rejection: unavailable on observed CPU");
#else
    puts("FP flush/trap-specific tests: unqualified target");
#endif
    puts("Numeric-v2 C ABI smoke: passed");
    return 0;
}
