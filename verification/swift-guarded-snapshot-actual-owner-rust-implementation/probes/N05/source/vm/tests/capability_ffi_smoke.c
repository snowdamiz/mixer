/* Original public C consumer, with its own compact Wasm binary builder. */
#include "mixer_vm_capability.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#define OFF(T,F,N) _Static_assert(offsetof(T,F)==(N),#T "." #F)
_Static_assert(sizeof(void*)==8,"LP64 client required");
_Static_assert(sizeof(MixerVmCapabilityLimitsV1)==32,"limits size");
_Static_assert(_Alignof(MixerVmCapabilityLimitsV1)==8,"limits alignment");
OFF(MixerVmCapabilityLimitsV1,struct_size,0);OFF(MixerVmCapabilityLimitsV1,abi_version,4);
OFF(MixerVmCapabilityLimitsV1,maximum_requests,8);OFF(MixerVmCapabilityLimitsV1,timeout_milliseconds,12);
OFF(MixerVmCapabilityLimitsV1,turn_milliseconds,16);OFF(MixerVmCapabilityLimitsV1,reserved,20);OFF(MixerVmCapabilityLimitsV1,reservation_bytes,24);
_Static_assert(sizeof(MixerVmCapabilityMessageV1)==40,"message size");
_Static_assert(_Alignof(MixerVmCapabilityMessageV1)==8,"message alignment");
OFF(MixerVmCapabilityMessageV1,struct_size,0);OFF(MixerVmCapabilityMessageV1,abi_version,4);
OFF(MixerVmCapabilityMessageV1,kind,8);OFF(MixerVmCapabilityMessageV1,operation,12);OFF(MixerVmCapabilityMessageV1,token,16);
OFF(MixerVmCapabilityMessageV1,remaining_milliseconds,24);OFF(MixerVmCapabilityMessageV1,payload_length,28);OFF(MixerVmCapabilityMessageV1,reserved,32);
_Static_assert(sizeof(MixerVmCapabilityResultV1)==24,"result size");
_Static_assert(_Alignof(MixerVmCapabilityResultV1)==8,"result alignment");
OFF(MixerVmCapabilityResultV1,struct_size,0);OFF(MixerVmCapabilityResultV1,abi_version,4);OFF(MixerVmCapabilityResultV1,kind,8);
OFF(MixerVmCapabilityResultV1,remaining_milliseconds,12);OFF(MixerVmCapabilityResultV1,reserved,16);
typedef struct Buffer { uint8_t data[4096];size_t len; } Buffer;
static void append(Buffer *b,const void *src,size_t n) {assert(b->len+n<=sizeof(b->data));memcpy(b->data+b->len,src,n);b->len+=n;}
static void byte(Buffer *b,uint8_t n) {append(b,&n,1);}
static void leb(Buffer *b,uint32_t n) {do {uint8_t c=n&127;n>>=7;byte(b,c|(n?128:0));}while(n);}
static void name(Buffer *b,const char *s) {size_t n=strlen(s);leb(b,(uint32_t)n);append(b,s,n);}
static void section(Buffer *m,uint8_t id,const Buffer *b) {byte(m,id);leb(m,(uint32_t)b->len);append(m,b->data,b->len);}
static Buffer module(void) {
    Buffer m={.len=0};const uint8_t header[]={0,97,115,109,1,0,0,0};append(&m,header,sizeof(header));
    const uint8_t types[]={4,0x60,3,0x7f,0x7f,0x7f,1,0x7f,0x60,1,0x7e,1,0x7f,0x60,4,0x7e,0x7f,0x7f,0x7f,1,0x7f,0x60,0,0};
    Buffer b={.len=0};append(&b,types,sizeof(types));section(&m,1,&b);
    b.len=0;byte(&b,3);const char *imports[]={"storage_get","cancel","poll"};for(uint32_t i=0;i<3;i++){name(&b,"mixer.capability.v1");name(&b,imports[i]);byte(&b,0);leb(&b,i);}section(&m,2,&b);
    b.len=0;const uint8_t functions[]={3,3,3,3};append(&b,functions,sizeof(functions));section(&m,3,&b);
    b.len=0;const uint8_t memory[]={1,1,1,1};append(&b,memory,sizeof(memory));section(&m,5,&b);
    b.len=0;byte(&b,6);const char *exports[]={"get","cancel","poll","start","mixer_guest_capability_ready_v1","trap"};for(uint32_t i=0;i<6;i++){name(&b,exports[i]);byte(&b,0);leb(&b,i);}section(&m,7,&b);
    b.len=0;const uint8_t code[]={3,2,0,0x0b,2,0,0x0b,3,0,0,0x0b};append(&b,code,sizeof(code));section(&m,10,&b);
    b.len=0;const uint8_t data[]={1,0,0x41,0,0x0b,4,'a','r','g','s'};append(&b,data,sizeof(data));section(&m,11,&b);return m;
}
static unsigned checks;
static void status(uint32_t got,uint32_t expected,const MixerVmReport *report) {if(got!=expected){fprintf(stderr,"status%u expected%u code=%s message=%s\n",got,expected,report->code,report->message);}assert(got==expected);assert(report->status==expected);checks++;}
int main(void) {
    Buffer m=module();MixerVmReport r;uint64_t h=0;const uint8_t startup[]="start";
    status(mixer_vm_capability_validate_v1(m.data,m.len,startup,5,NULL,NULL,&r),0,&r);
    status(mixer_vm_validate_table_memory_v3(m.data,m.len,NULL,&r),1,&r);
    status(mixer_vm_capability_session_create_v1(m.data,m.len,startup,5,NULL,NULL,&h,&r),0,&r);assert(h!=0);
    status(mixer_vm_session_cancel_v1(h,&r),3,&r);
    status(mixer_vm_capability_session_enable_v1(h,&r),3,&r);
    status(mixer_vm_capability_session_startup_v1(h,&r),0,&r);
    status(mixer_vm_capability_session_enable_v1(h,&r),0,&r);assert(r.fuel_used==0&&r.host_calls_used==0);
    status(mixer_vm_capability_session_enable_v1(h,&r),0,&r);
    uint32_t did=7;status(mixer_vm_capability_session_wake_v1(h,&did,&r),0,&r);assert(did==0&&r.fuel_used==0);
    MixerVmValue args[]={{1,0,0},{1,0,4},{1,0,32}};
    status(mixer_vm_capability_session_invoke_v1(h,(const uint8_t*)"get",3,args,3,&r),0,&r);assert(r.value_type==1&&r.value==0);
    MixerVmCapabilityMessageV1 msg;uint8_t output[512];
    status(mixer_vm_capability_take_v1(h,&msg,NULL,0,&r),0,&r);assert(msg.kind==3&&msg.payload_length==4&&msg.token==0);
    status(mixer_vm_capability_take_v1(h,&msg,output,sizeof(output),&r),0,&r);assert(msg.kind==1&&msg.operation==2&&msg.payload_length==4&&memcmp(output,"args",4)==0);
    uint64_t token=msg.token;MixerVmCapabilityResultV1 result;
    status(mixer_vm_capability_post_v1(h,token,3,(const uint8_t*)"reply",5,&result,&r),3,&r);
    status(mixer_vm_capability_post_v1(h,token,2,(const uint8_t*)"reply",5,&result,&r),0,&r);assert(result.kind==0);
    status(mixer_vm_capability_ack_exit_v1(h,token,2,&result,&r),0,&r);assert(result.kind==0);
    status(mixer_vm_capability_ack_exit_v1(h,token,2,&result,&r),0,&r);assert(result.kind==2);
    status(mixer_vm_capability_post_v1(h,token,2,(const uint8_t*)"again",5,&result,&r),0,&r);assert(result.kind==1);
    status(mixer_vm_capability_limit_deadline_v1(h,token,2,1,&result,&r),0,&r);assert(result.kind==1&&result.remaining_milliseconds==0);
    MixerVmValue poll[]={{2,0,(int64_t)token},{1,0,256},{1,0,512},{1,0,48}};
    status(mixer_vm_capability_session_invoke_v1(h,(const uint8_t*)"poll",4,poll,4,&r),0,&r);assert(r.value==0);
    status(mixer_vm_capability_session_read_v1(h,256,output,5,&r),0,&r);assert(memcmp(output,"reply",5)==0);
    status(mixer_vm_capability_ack_exit_v1(h,token,2,&result,&r),3,&r);
    status(mixer_vm_capability_session_write_v1(h,65536,NULL,0,&r),0,&r);
    status(mixer_vm_capability_session_write_v1(h,65537,NULL,0,&r),3,&r);
    status(mixer_vm_capability_session_close_v1(h,&r),0,&r);
    status(mixer_vm_capability_expire_v1(h,&r),3,&r);
    /* Report alias rejection must not touch even one sentinel byte. No pointer
       is dereferenced by C at this deliberately unaligned address. */
    uint8_t sentinel[1024],original[1024];memset(sentinel,0xa5,sizeof(sentinel));memcpy(original,sentinel,sizeof(sentinel));MixerVmReport *unaligned=(MixerVmReport*)(void*)(sentinel+1);
    assert(mixer_vm_capability_validate_v1((uint8_t*)unaligned,8,startup,5,NULL,NULL,unaligned)==3);assert(memcmp(sentinel,original,sizeof(sentinel))==0);checks++;
    assert(mixer_vm_capability_take_v1(0,(MixerVmCapabilityMessageV1*)(void*)(sentinel+1),NULL,0,unaligned)==3);assert(memcmp(sentinel,original,sizeof(sentinel))==0);checks++;
    printf("Capability native C smoke: passed%u status/alias checks; complete C/Rust fixed layouts asserted separately\n",checks);return 0;
}
