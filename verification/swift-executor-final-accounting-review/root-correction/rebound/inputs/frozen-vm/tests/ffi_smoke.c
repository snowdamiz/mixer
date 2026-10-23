/* Independently authored ABI fixture: one exported () -> i32 returning 42. */
#include "mixer_vm.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
_Static_assert(sizeof(MixerVmLimits)==32,"limits layout");
_Static_assert(sizeof(MixerVmValue)==16,"value layout");
_Static_assert(sizeof(MixerVmReport)==352,"report layout");
int main(void) {
    const uint8_t module[]={0,97,115,109,1,0,0,0,1,5,1,96,0,1,127,
        3,2,1,0,7,7,1,3,114,117,110,0,0,10,6,1,4,0,65,42,11};
    MixerVmReport report;
    assert(mixer_vm_validate(module,sizeof module,NULL,&report)==0);
    assert(report.abi_version==MIXER_VM_ABI_VERSION);
    assert(mixer_vm_invoke(module,sizeof module,(const uint8_t *)"run",3,NULL,0,NULL,&report)==0);
    assert(report.value_type==1 && report.value==42 && report.fuel_used==2);
    MixerVmLimits limits={sizeof limits,1,0,64,4096,64,1024};
    assert(mixer_vm_invoke(module,sizeof module,(const uint8_t *)"run",3,NULL,0,&limits,&report)==2);
    assert(strcmp((const char *)report.code,"fuel_exhausted")==0);
    assert(report.function==0 && report.offset>8);
    assert(mixer_vm_validate(NULL,1,NULL,&report)==3);
    assert(mixer_vm_validate(module,sizeof module,NULL,NULL)==3);
    puts("C ABI smoke: passed");
    return 0;
}
