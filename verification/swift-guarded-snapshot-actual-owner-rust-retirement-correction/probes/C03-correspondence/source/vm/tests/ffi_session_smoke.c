#include "mixer_vm.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
_Static_assert(sizeof(MixerVmLimits)==32,"legacy limits ABI unchanged");
_Static_assert(sizeof(MixerVmValue)==16,"legacy value ABI unchanged");
_Static_assert(sizeof(MixerVmReport)==352,"legacy report ABI unchanged");
int main(void) {
    const uint8_t counter[]={0,97,115,109,1,0,0,0,
        1,5,1,96,0,1,127,3,2,1,0,5,4,1,1,1,1,
        6,6,1,127,1,65,0,11,7,7,1,3,114,117,110,0,0,
        10,20,1,18,0,35,0,65,1,106,36,0,65,0,35,0,54,2,0,35,0,11};
    uint64_t handle=0;
    MixerVmReport report;
    assert(mixer_vm_session_create_v1(1,counter,sizeof counter,NULL,&handle,&report)==0);
    assert(handle!=0);
    for(int i=1;i<=3;i++) {
        assert(mixer_vm_session_invoke_v1(handle,(const uint8_t*)"run",3,NULL,0,&report)==0);
        assert(report.value_type==1&&report.value==i&&report.fuel_used==9);
    }
    uint8_t bytes[4]={0};
    assert(mixer_vm_session_read_v1(handle,0,bytes,sizeof bytes,&report)==0);
    assert(bytes[0]==3&&bytes[1]==0&&bytes[2]==0&&bytes[3]==0);
    const uint8_t replacement[4]={9,8,7,6};
    assert(mixer_vm_session_write_v1(handle,0,replacement,sizeof replacement,&report)==0);
    assert(mixer_vm_session_read_v1(handle,0,bytes,sizeof bytes,&report)==0);
    assert(memcmp(bytes,replacement,4)==0);
    assert(mixer_vm_session_write_v1(handle,65534,replacement,4,&report)==3);
    assert(mixer_vm_session_cancel_v1(handle,&report)==0);
    assert(mixer_vm_session_invoke_v1(handle,(const uint8_t*)"run",3,NULL,0,&report)==2);
    assert(strcmp((const char*)report.code,"session_terminal")==0);
    assert(mixer_vm_session_close_v1(handle,&report)==0);
    assert(mixer_vm_session_close_v1(handle,&report)==3);
    /* Existing entry point still creates fresh state. */
    assert(mixer_vm_invoke(counter,sizeof counter,(const uint8_t*)"run",3,NULL,0,NULL,&report)==0);
    assert(report.value==1);
    puts("Persistent session C ABI smoke: passed; legacy layouts and one-shot state unchanged");
    return 0;
}
