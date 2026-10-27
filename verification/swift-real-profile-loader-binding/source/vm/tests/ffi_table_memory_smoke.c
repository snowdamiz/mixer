#include "mixer_vm.h"
#include <assert.h>
#include <stdio.h>
_Static_assert(sizeof(MixerVmLimits)==32,"legacy limits ABI unchanged");
_Static_assert(sizeof(MixerVmReport)==352,"legacy report ABI unchanged");
int main(void){
    /* () -> i32 calls slot0, initialized to function1 returning42. */
    const uint8_t table[]={0,97,115,109,1,0,0,0,1,5,1,96,0,1,127,
        3,3,2,0,0,4,5,1,112,1,1,1,7,7,1,3,114,117,110,0,0,
        9,7,1,0,65,0,11,1,1,10,14,2,7,0,65,0,17,0,0,11,4,0,65,42,11};
    MixerVmReport report;
    assert(mixer_vm_validate(table,sizeof table,NULL,&report)==1);
    assert(mixer_vm_validate_numeric_v2(table,sizeof table,NULL,&report)==1);
    assert(mixer_vm_validate_table_memory_v3(table,sizeof table,NULL,&report)==0);
    assert(mixer_vm_invoke_table_memory_v3(table,sizeof table,(const uint8_t*)"run",3,NULL,0,NULL,&report)==0);
    assert(report.value_type==1&&report.value==42&&report.fuel_used==5);
    /* Fill one byte with0x1234; unsigned byte load returns0x34. */
    const uint8_t fill[]={0,97,115,109,1,0,0,0,1,5,1,96,0,1,127,
        3,2,1,0,5,4,1,1,1,1,7,7,1,3,114,117,110,0,0,
        10,19,1,17,0,65,0,65,180,36,65,1,252,11,0,65,0,45,0,0,11};
    assert(mixer_vm_invoke_table_memory_v3(fill,sizeof fill,(const uint8_t*)"run",3,NULL,0,NULL,&report)==0);
    assert(report.value==0x34&&report.fuel_used==8);
    puts("Table-memory-v3 C ABI smoke: passed; legacy struct layouts unchanged");return 0;
}
