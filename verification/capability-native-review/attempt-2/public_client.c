/* Independently authored public C client. No internal Rust access/test hooks. */
#include "mixer_vm_capability.h"
#include <inttypes.h>
#include <limits.h>
#include <pthread.h>
#include <sched.h>
#include <stdalign.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static _Atomic unsigned checks;
#define CHECK(expr) do { atomic_fetch_add_explicit(&checks,1,memory_order_relaxed); if (!(expr)) { fprintf(stderr,"check failed at %s:%d: %s\n",__FILE__,__LINE__,#expr); exit(1); } } while(0)
#define STATUS(expr,want) do { uint32_t actual_=(expr); CHECK(actual_==(want)); CHECK(report.status==actual_); } while(0)
static const uint8_t startup_name[]="startup";
static const uint8_t arguments[]={ '{','"','n','a','m','e','s','p','a','c','e','"',':','"','n','"',',','"','k','e','y','"',':','"','k','"','}' };
static const uint8_t completion[]="{\"abi\":1,\"capability\":\"storage.keyValue.v1\",\"operation\":\"get\",\"outcome\":{\"kind\":\"success\",\"value\":{\"found\":false,\"valueBase64\":\"\"}},\"schemaHash\":\"4a311222c978ddd0982e8dfbcf3d4864b856a80bcc1efb3b725adede7f8e22fd\"}";
struct Buffer { uint8_t *bytes; size_t length; };
static struct Buffer cap_module, old_module;
static struct Buffer load(const char *path) {
    FILE *f=fopen(path,"rb"); CHECK(f!=NULL); CHECK(fseek(f,0,SEEK_END)==0); long n=ftell(f); CHECK(n>0&&n<4096); rewind(f);
    struct Buffer b={malloc((size_t)n),(size_t)n}; CHECK(b.bytes!=NULL); CHECK(fread(b.bytes,1,b.length,f)==b.length); CHECK(fclose(f)==0); return b;
}
static uint64_t little(const uint8_t *p) { uint64_t v=0; for(unsigned i=0;i<8;i++) v|=(uint64_t)p[i]<<(i*8); return v; }
static MixerVmValue integer32(uint32_t n) { MixerVmValue v={1,0,(int64_t)n}; return v; }
static MixerVmValue integer64(uint64_t n) { MixerVmValue v={2,0,0}; memcpy(&v.value,&n,8); return v; }
static uint64_t create_cap(void) {
    MixerVmReport report; uint64_t handle=UINT64_MAX;
    STATUS(mixer_vm_capability_session_create_v1(cap_module.bytes,cap_module.length,startup_name,sizeof(startup_name)-1,NULL,NULL,&handle,&report),0);
    CHECK(handle!=0); return handle;
}
static uint64_t ready_cap(void) {
    uint64_t h=create_cap(); MixerVmReport report;
    STATUS(mixer_vm_capability_session_enable_v1(h,&report),3);
    STATUS(mixer_vm_capability_session_startup_v1(h,&report),0);
    STATUS(mixer_vm_capability_session_enable_v1(h,&report),0);
    STATUS(mixer_vm_capability_session_enable_v1(h,&report),0); return h;
}
static uint64_t create_old(void) {
    MixerVmReport report; uint64_t h=0;
    STATUS(mixer_vm_session_create_v1(3,old_module.bytes,old_module.length,NULL,&h,&report),0); CHECK(h!=0); return h;
}
static void close_cap(uint64_t h) { MixerVmReport report; STATUS(mixer_vm_capability_session_close_v1(h,&report),0); }
static void close_old(uint64_t h) { MixerVmReport report; STATUS(mixer_vm_session_close_v1(h,&report),0); }
static uint64_t enqueue(uint64_t h) {
    MixerVmReport report; uint8_t raw[8];
    STATUS(mixer_vm_capability_session_write_v1(h,128,arguments,sizeof(arguments),&report),0);
    MixerVmValue args[3]={integer32(128),integer32(sizeof(arguments)),integer32(1024)};
    STATUS(mixer_vm_capability_session_invoke_v1(h,(const uint8_t *)"enqueue",7,args,3,&report),0); CHECK(report.value_type==1&&report.value==0);
    STATUS(mixer_vm_capability_session_read_v1(h,1024,raw,sizeof(raw),&report),0); return little(raw);
}
static MixerVmCapabilityMessageV1 take_call(uint64_t h,uint64_t token) {
    MixerVmReport report; MixerVmCapabilityMessageV1 message; uint8_t bytes[256]; memset(bytes,0xa5,sizeof(bytes));
    STATUS(mixer_vm_capability_take_v1(h,&message,bytes,sizeof(bytes),&report),0);
    CHECK(message.kind==1&&message.operation==2&&message.token==token&&message.payload_length==sizeof(arguments));
    CHECK(message.struct_size==40&&message.abi_version==1&&message.reserved==0&&message.remaining_milliseconds>0);
    CHECK(memcmp(bytes,arguments,sizeof(arguments))==0&&bytes[sizeof(arguments)]==0xa5); return message;
}
static void ack(uint64_t h,uint64_t token,uint32_t want,uint32_t kind) {
    MixerVmReport report; MixerVmCapabilityResultV1 result; memset(&result,0xa5,sizeof(result));
    STATUS(mixer_vm_capability_ack_exit_v1(h,token,2,&result,&report),want);
    CHECK(result.struct_size==24&&result.abi_version==1&&result.reserved==0); if(want==0) CHECK(result.kind==kind);
}
static void poll_payload(uint64_t h,uint64_t token,const uint8_t *expected,size_t length) {
    MixerVmReport report; uint8_t output[512], raw[4];
    MixerVmValue args[4]={integer64(token),integer32(2048),integer32(sizeof(output)),integer32(4096)};
    STATUS(mixer_vm_capability_session_invoke_v1(h,(const uint8_t *)"poll",4,args,4,&report),0); CHECK(report.value_type==1&&report.value==0);
    STATUS(mixer_vm_capability_session_read_v1(h,4096,raw,4,&report),0);
    uint32_t n=(uint32_t)raw[0]|(uint32_t)raw[1]<<8|(uint32_t)raw[2]<<16|(uint32_t)raw[3]<<24; CHECK(n==length&&n<=sizeof(output));
    STATUS(mixer_vm_capability_session_read_v1(h,2048,output,n,&report),0); CHECK(memcmp(output,expected,n)==0);
}
static void layouts(void) {
    CHECK(sizeof(void*)==8&&sizeof(size_t)==8);
    CHECK(sizeof(MixerVmLimits)==32&&sizeof(MixerVmValue)==16&&sizeof(MixerVmReport)==352);
    CHECK(sizeof(MixerVmCapabilityLimitsV1)==32&&alignof(MixerVmCapabilityLimitsV1)==8);
    CHECK(sizeof(MixerVmCapabilityMessageV1)==40&&alignof(MixerVmCapabilityMessageV1)==8);
    CHECK(sizeof(MixerVmCapabilityResultV1)==24&&alignof(MixerVmCapabilityResultV1)==8);
    CHECK(offsetof(MixerVmCapabilityLimitsV1,reservation_bytes)==24&&offsetof(MixerVmCapabilityLimitsV1,reserved)==20);
    CHECK(offsetof(MixerVmCapabilityMessageV1,token)==16&&offsetof(MixerVmCapabilityMessageV1,remaining_milliseconds)==24&&offsetof(MixerVmCapabilityMessageV1,payload_length)==28&&offsetof(MixerVmCapabilityMessageV1,reserved)==32);
    CHECK(offsetof(MixerVmCapabilityResultV1,kind)==8&&offsetof(MixerVmCapabilityResultV1,remaining_milliseconds)==12&&offsetof(MixerVmCapabilityResultV1,reserved)==16);
}
static void lifecycle(void) {
    MixerVmReport report; uint64_t h=ready_cap(), token=enqueue(h); MixerVmCapabilityMessageV1 message;
    STATUS(mixer_vm_capability_take_v1(h,&message,(uint8_t*)&report,0,&report),0); CHECK(message.kind==3&&message.payload_length==sizeof(arguments)&&message.token==0&&message.operation==0);
    /* Mutation of guest memory after enqueue cannot change the retained snapshot. */
    uint8_t changed=0; STATUS(mixer_vm_capability_session_write_v1(h,128,&changed,1,&report),0); take_call(h,token);
    MixerVmCapabilityResultV1 result;
    STATUS(mixer_vm_capability_post_v1(h,token,2,completion,sizeof(completion)-1,&result,&report),0); CHECK(result.kind==0);
    STATUS(mixer_vm_capability_post_v1(h,token,2,completion,sizeof(completion)-1,&result,&report),0); CHECK(result.kind==1);
    ack(h,token,0,0); ack(h,token,0,2);
    /* Frozen mailbox precedence: existing unconsumed terminal wins after ack. */
    STATUS(mixer_vm_capability_post_v1(h,token,2,completion,sizeof(completion)-1,&result,&report),0); CHECK(result.kind==1);
    STATUS(mixer_vm_capability_limit_deadline_v1(h,token,2,1000,&result,&report),0); CHECK(result.kind==1&&result.remaining_milliseconds==0);
    poll_payload(h,token,completion,sizeof(completion)-1); ack(h,token,3,0);
    STATUS(mixer_vm_capability_post_v1(h,token,2,completion,sizeof(completion)-1,&result,&report),3);
    uint64_t next=enqueue(h); CHECK(next!=token); take_call(h,next); ack(h,token,3,0);
    close_cap(h); STATUS(mixer_vm_capability_take_v1(h,&message,NULL,0,&report),3); ack(h,next,0,0); ack(h,next,3,0);
    h=ready_cap(); token=enqueue(h); take_call(h,token); ack(h,token,0,0); ack(h,token,0,2);
    STATUS(mixer_vm_capability_post_v1(h,token,2,completion,sizeof(completion)-1,&result,&report),3);
    STATUS(mixer_vm_capability_limit_deadline_v1(h,token,2,1000,&result,&report),3); close_cap(h); ack(h,token,3,0);
}
static void cancellation_and_stale_ack(void) {
    MixerVmReport report; uint64_t h=ready_cap(),a=enqueue(h),b=enqueue(h); take_call(h,a); take_call(h,b);
    MixerVmValue value=integer64(a); STATUS(mixer_vm_capability_session_invoke_v1(h,(const uint8_t*)"cancel",6,&value,1,&report),0); CHECK(report.value==0);
    MixerVmCapabilityMessageV1 message; STATUS(mixer_vm_capability_take_v1(h,&message,NULL,0,&report),0);
    CHECK(message.kind==2&&message.token==a&&message.operation==2&&message.payload_length==0&&message.remaining_milliseconds==0);
    close_cap(h); ack(h,a,0,0); ack(h,a,3,0); /* Session still retained by b, but a's mailbox identity is released. */
    ack(h,b,0,0); ack(h,b,3,0);
    h=ready_cap(); a=enqueue(h); take_call(h,a);
    STATUS(mixer_vm_capability_session_invoke_v1(h,(const uint8_t*)"trap",4,NULL,0,&report),2);
    STATUS(mixer_vm_capability_take_v1(h,&message,NULL,0,&report),2); close_cap(h); ack(h,a,0,0);
}
static void mixed_pool_and_family(void) {
    MixerVmReport report; uint64_t old[8],cap[8];
    for(unsigned i=0;i<8;i++) {old[i]=create_old();cap[i]=ready_cap();}
    uint64_t extra=99;
    STATUS(mixer_vm_capability_session_create_v1(cap_module.bytes,cap_module.length,startup_name,7,NULL,NULL,&extra,&report),3); CHECK(extra==0);
    extra=99; STATUS(mixer_vm_session_create_v1(3,old_module.bytes,old_module.length,NULL,&extra,&report),3); CHECK(extra==0);
    STATUS(mixer_vm_session_cancel_v1(cap[1],&report),3); STATUS(mixer_vm_session_close_v1(cap[1],&report),3);
    STATUS(mixer_vm_session_read_v1(cap[1],0,NULL,0,&report),3); STATUS(mixer_vm_session_write_v1(cap[1],0,NULL,0,&report),3);
    STATUS(mixer_vm_session_invoke_v1(cap[1],(const uint8_t*)"run",3,NULL,0,&report),3);
    STATUS(mixer_vm_capability_session_cancel_v1(old[1],&report),3); STATUS(mixer_vm_capability_session_close_v1(old[1],&report),3);
    STATUS(mixer_vm_capability_session_startup_v1(old[1],&report),3); STATUS(mixer_vm_capability_session_enable_v1(old[1],&report),3);
    uint64_t pending=enqueue(cap[0]); take_call(cap[0],pending); uint64_t closed=cap[0]; close_cap(closed);
    extra=99; STATUS(mixer_vm_capability_session_create_v1(cap_module.bytes,cap_module.length,startup_name,7,NULL,NULL,&extra,&report),3); CHECK(extra==0);
    ack(closed,pending,0,0); cap[0]=ready_cap(); CHECK((uint32_t)cap[0]==(uint32_t)closed&&(cap[0]>>32)>(closed>>32)); ack(closed,pending,3,0);
    for(unsigned i=0;i<8;i++) {close_cap(cap[i]);close_old(old[i]);}
    extra=99; STATUS(mixer_vm_session_create_v1(4,cap_module.bytes,cap_module.length,NULL,&extra,&report),3); CHECK(extra==0);
    STATUS(mixer_vm_validate_table_memory_v3(cap_module.bytes,cap_module.length,NULL,&report),1);
}
static void limit_validation(void) {
    MixerVmReport report; MixerVmCapabilityLimitsV1 valid={32,1,8,30000,50,0,8388608};
    for(unsigned field=0;field<7;field++) {
        for(unsigned boundary=0;boundary<2;boundary++) {
            MixerVmCapabilityLimitsV1 cap=valid;
            switch(field) {
            case 0: cap.struct_size=boundary?33:31;break;
            case 1: cap.abi_version=boundary?2:0;break;
            case 2: cap.maximum_requests=boundary?9:0;break;
            case 3: cap.timeout_milliseconds=boundary?30001:0;break;
            case 4: cap.turn_milliseconds=boundary?51:0;break;
            case 5: cap.reserved=boundary?UINT32_MAX:1;break;
            default: cap.reservation_bytes=boundary?8388609:0;break;
            }
            uint64_t h=99;
            STATUS(mixer_vm_capability_validate_v1(cap_module.bytes,cap_module.length,startup_name,7,NULL,&cap,&report),3);
            STATUS(mixer_vm_capability_session_create_v1(cap_module.bytes,cap_module.length,startup_name,7,NULL,&cap,&h,&report),3);CHECK(h==0);
        }
    }
    uint8_t storage[34],handles[10],reports[354];memcpy(storage+1,&valid,sizeof(valid));memset(handles,0xa5,sizeof(handles));memset(reports,0xa5,sizeof(reports));
    CHECK(mixer_vm_capability_session_create_v1(cap_module.bytes,cap_module.length,startup_name,7,NULL,(const MixerVmCapabilityLimitsV1*)(storage+1),(uint64_t*)(handles+1),(MixerVmReport*)(reports+1))==0);
    uint64_t h;memcpy(&h,handles+1,8);memcpy(&report,reports+1,sizeof(report));CHECK(h!=0&&report.status==0&&handles[0]==0xa5&&handles[9]==0xa5&&reports[0]==0xa5&&reports[353]==0xa5);close_cap(h);
}
static void bounds_and_unaligned(void) {
    MixerVmReport report; uint64_t h=ready_cap();
    STATUS(mixer_vm_capability_session_read_v1(h,65536,(uint8_t*)&report,0,&report),0);
    STATUS(mixer_vm_capability_session_write_v1(h,65536,(uint8_t*)&report,0,&report),0);
    STATUS(mixer_vm_capability_session_read_v1(h,65537,NULL,0,&report),3);
    STATUS(mixer_vm_capability_session_write_v1(h,65537,NULL,0,&report),3);
    uint8_t sentinel[8]; memset(sentinel,0xa5,8);
    STATUS(mixer_vm_capability_session_read_v1(h,65532,sentinel,8,&report),3); for(unsigned i=0;i<8;i++) CHECK(sentinel[i]==0xa5);
    STATUS(mixer_vm_capability_session_write_v1(h,UINT32_MAX,sentinel,8,&report),3);
    uint8_t rs[sizeof(MixerVmReport)+2],ms[sizeof(MixerVmCapabilityMessageV1)+2]; memset(rs,0xa5,sizeof(rs));memset(ms,0xa5,sizeof(ms));
    CHECK(mixer_vm_capability_take_v1(h,(MixerVmCapabilityMessageV1*)(ms+1),NULL,0,(MixerVmReport*)(rs+1))==0);
    MixerVmCapabilityMessageV1 message; memcpy(&message,ms+1,sizeof(message)); memcpy(&report,rs+1,sizeof(report));
    CHECK(message.kind==0&&message.struct_size==40&&report.status==0&&rs[0]==0xa5&&rs[sizeof(rs)-1]==0xa5&&ms[0]==0xa5&&ms[sizeof(ms)-1]==0xa5);
    close_cap(h);
}
static void alias_preflight(void) {
    alignas(16) uint8_t arena[2048],before[2048];
    uint8_t *module=arena+16,*name=arena+64,*vm=arena+128,*cap=arena+192,*handle=arena+256,*msg=arena+320,*payload=arena+400,*result=arena+480,*rep=arena+768;
#define NO_WRITE(call) do { memset(arena,0xa5,sizeof(arena)); memcpy(before,arena,sizeof(arena)); CHECK((call)==3); CHECK(memcmp(arena,before,sizeof(arena))==0); } while(0)
    /* Each create output against each borrowed input and against each other. */
    uint8_t *inputs[]={module,name,vm,cap};
    for(unsigned i=0;i<4;i++) {
        NO_WRITE(mixer_vm_capability_session_create_v1(module,8,name,7,(const MixerVmLimits*)vm,(const MixerVmCapabilityLimitsV1*)cap,(uint64_t*)inputs[i],(MixerVmReport*)rep));
        NO_WRITE(mixer_vm_capability_session_create_v1(module,8,name,7,(const MixerVmLimits*)vm,(const MixerVmCapabilityLimitsV1*)cap,(uint64_t*)handle,(MixerVmReport*)inputs[i]));
    }
    NO_WRITE(mixer_vm_capability_session_create_v1(module,8,name,7,NULL,NULL,(uint64_t*)(rep+sizeof(MixerVmReport)-1),(MixerVmReport*)rep));
    NO_WRITE(mixer_vm_capability_validate_v1(module,8,name,7,NULL,NULL,(MixerVmReport*)module));
    NO_WRITE(mixer_vm_capability_validate_v1(module,8,name,7,NULL,NULL,(MixerVmReport*)name));
    NO_WRITE(mixer_vm_capability_session_invoke_v1(0,name,7,(const MixerVmValue*)rep,1,(MixerVmReport*)rep));
    NO_WRITE(mixer_vm_capability_session_invoke_v1(0,rep,7,NULL,0,(MixerVmReport*)rep));
    NO_WRITE(mixer_vm_capability_session_wake_v1(0,(uint32_t*)(rep+sizeof(MixerVmReport)-1),(MixerVmReport*)rep));
    NO_WRITE(mixer_vm_capability_session_read_v1(0,0,rep+sizeof(MixerVmReport)-1,2,(MixerVmReport*)rep));
    NO_WRITE(mixer_vm_capability_session_write_v1(0,0,rep+sizeof(MixerVmReport)-1,2,(MixerVmReport*)rep));
    /* All three take outputs participate, including full payload capacity. */
    NO_WRITE(mixer_vm_capability_take_v1(0,(MixerVmCapabilityMessageV1*)msg,msg+39,8,(MixerVmReport*)rep));
    NO_WRITE(mixer_vm_capability_take_v1(0,(MixerVmCapabilityMessageV1*)(rep+351),payload,8,(MixerVmReport*)rep));
    NO_WRITE(mixer_vm_capability_take_v1(0,(MixerVmCapabilityMessageV1*)msg,rep+351,8,(MixerVmReport*)rep));
    NO_WRITE(mixer_vm_capability_post_v1(0,0,2,payload,16,(MixerVmCapabilityResultV1*)(payload+15),(MixerVmReport*)rep));
    NO_WRITE(mixer_vm_capability_post_v1(0,0,2,rep+351,16,(MixerVmCapabilityResultV1*)result,(MixerVmReport*)rep));
    NO_WRITE(mixer_vm_capability_post_v1(0,0,2,payload,16,(MixerVmCapabilityResultV1*)(rep+351),(MixerVmReport*)rep));
    NO_WRITE(mixer_vm_capability_ack_exit_v1(0,0,2,(MixerVmCapabilityResultV1*)(rep+351),(MixerVmReport*)rep));
    NO_WRITE(mixer_vm_capability_limit_deadline_v1(0,0,2,1,(MixerVmCapabilityResultV1*)(rep+351),(MixerVmReport*)rep));
    /* Address wraps and byte/count ceilings reject before access or any report write. */
    const uint8_t *wrapped=(const uint8_t*)(UINTPTR_MAX-3);
    NO_WRITE(mixer_vm_capability_validate_v1(wrapped,8,name,7,NULL,NULL,(MixerVmReport*)rep));
    NO_WRITE(mixer_vm_capability_session_create_v1(module,8,wrapped,8,NULL,NULL,(uint64_t*)handle,(MixerVmReport*)rep));
    NO_WRITE(mixer_vm_capability_session_create_v1(module,8,name,7,(const MixerVmLimits*)(UINTPTR_MAX-3),NULL,(uint64_t*)handle,(MixerVmReport*)rep));
    NO_WRITE(mixer_vm_capability_session_create_v1(module,8,name,7,NULL,(const MixerVmCapabilityLimitsV1*)(UINTPTR_MAX-3),(uint64_t*)handle,(MixerVmReport*)rep));
    NO_WRITE(mixer_vm_capability_session_create_v1(module,8,name,7,NULL,NULL,(uint64_t*)(UINTPTR_MAX-3),(MixerVmReport*)rep));
    NO_WRITE(mixer_vm_capability_session_invoke_v1(0,name,7,(const MixerVmValue*)(UINTPTR_MAX-3),1,(MixerVmReport*)rep));
    NO_WRITE(mixer_vm_capability_session_invoke_v1(0,name,7,(const MixerVmValue*)payload,SIZE_MAX,(MixerVmReport*)rep));
    NO_WRITE(mixer_vm_capability_session_read_v1(0,0,(uint8_t*)wrapped,8,(MixerVmReport*)rep));
    NO_WRITE(mixer_vm_capability_session_write_v1(0,0,wrapped,8,(MixerVmReport*)rep));
    NO_WRITE(mixer_vm_capability_take_v1(0,(MixerVmCapabilityMessageV1*)(UINTPTR_MAX-3),payload,16,(MixerVmReport*)rep));
    NO_WRITE(mixer_vm_capability_post_v1(0,0,2,wrapped,8,(MixerVmCapabilityResultV1*)result,(MixerVmReport*)rep));
    NO_WRITE(mixer_vm_capability_session_wake_v1(0,(uint32_t*)(UINTPTR_MAX-1),(MixerVmReport*)rep));
    NO_WRITE(mixer_vm_capability_session_startup_v1(0,(MixerVmReport*)(UINTPTR_MAX-3)));
    NO_WRITE(mixer_vm_capability_validate_v1(module,4194305,name,7,NULL,NULL,(MixerVmReport*)rep));
    NO_WRITE(mixer_vm_capability_session_invoke_v1(0,name,4097,NULL,0,(MixerVmReport*)rep));
    NO_WRITE(mixer_vm_capability_session_read_v1(0,0,payload,1048577,(MixerVmReport*)rep));
    NO_WRITE(mixer_vm_capability_take_v1(0,(MixerVmCapabilityMessageV1*)msg,payload,524289,(MixerVmReport*)rep));
    NO_WRITE(mixer_vm_capability_post_v1(0,0,2,payload,524289,(MixerVmCapabilityResultV1*)result,(MixerVmReport*)rep));
    NO_WRITE(mixer_vm_capability_ack_exit_v1(0,0,2,(MixerVmCapabilityResultV1*)result,NULL));
    NO_WRITE(mixer_vm_capability_limit_deadline_v1(0,0,2,1,(MixerVmCapabilityResultV1*)result,NULL));
    NO_WRITE(mixer_vm_capability_session_wake_v1(0,(uint32_t*)result,NULL));
    NO_WRITE(mixer_vm_capability_take_v1(0,(MixerVmCapabilityMessageV1*)msg,payload,16,NULL));
    NO_WRITE(mixer_vm_capability_session_create_v1(module,8,name,7,NULL,NULL,(uint64_t*)handle,NULL));
#undef NO_WRITE
    /* Null-report methods must not stop or close an otherwise valid live session. */
    uint64_t h=ready_cap(); MixerVmReport report;
    CHECK(mixer_vm_capability_session_cancel_v1(h,NULL)==3); CHECK(mixer_vm_capability_session_close_v1(h,NULL)==3);
    STATUS(mixer_vm_capability_session_read_v1(h,0,NULL,0,&report),0); close_cap(h);
}
struct Gate { pthread_mutex_t mutex; pthread_cond_t cond; unsigned arrived; };
static void gate_init(struct Gate *g) { CHECK(pthread_mutex_init(&g->mutex,NULL)==0); CHECK(pthread_cond_init(&g->cond,NULL)==0); g->arrived=0; }
static void gate_wait(struct Gate *g) {
    CHECK(pthread_mutex_lock(&g->mutex)==0); g->arrived++;
    if(g->arrived==2) CHECK(pthread_cond_broadcast(&g->cond)==0);
    while(g->arrived<2) CHECK(pthread_cond_wait(&g->cond,&g->mutex)==0);
    CHECK(pthread_mutex_unlock(&g->mutex)==0);
}
static void gate_destroy(struct Gate *g) { CHECK(pthread_cond_destroy(&g->cond)==0); CHECK(pthread_mutex_destroy(&g->mutex)==0); }
struct Race { struct Gate gate; uint64_t handle,token; uint32_t status; MixerVmCapabilityMessageV1 message; };
static void *race_take(void *opaque) {
    struct Race *r=opaque; MixerVmReport report; uint8_t bytes[256]; gate_wait(&r->gate);
    r->status=mixer_vm_capability_take_v1(r->handle,&r->message,bytes,sizeof(bytes),&report); CHECK(r->status==report.status);
    if(r->status==0&&r->message.kind==1) CHECK(r->message.token==r->token&&memcmp(bytes,arguments,sizeof(arguments))==0);
    return NULL;
}
static void *race_ack(void *opaque) {
    struct Race *r=opaque; MixerVmReport report; MixerVmCapabilityResultV1 result; gate_wait(&r->gate);
    r->status=mixer_vm_capability_ack_exit_v1(r->handle,r->token,2,&result,&report); CHECK(r->status==report.status); return NULL;
}
static void races(void) {
    for(unsigned i=0;i<48;i++) {
        struct Race race; memset(&race,0,sizeof(race)); gate_init(&race.gate); race.handle=ready_cap();race.token=enqueue(race.handle);
        pthread_t thread; CHECK(pthread_create(&thread,NULL,race_take,&race)==0); gate_wait(&race.gate); close_cap(race.handle); CHECK(pthread_join(thread,NULL)==0);
        if(race.status==0&&race.message.kind==1) ack(race.handle,race.token,0,0);
        else CHECK(race.status==2||race.status==3||race.message.kind==0);
        gate_destroy(&race.gate);
    }
    for(unsigned i=0;i<48;i++) {
        struct Race race; memset(&race,0,sizeof(race)); gate_init(&race.gate); race.handle=ready_cap();race.token=enqueue(race.handle);take_call(race.handle,race.token);
        pthread_t thread; CHECK(pthread_create(&thread,NULL,race_ack,&race)==0); gate_wait(&race.gate); close_cap(race.handle); CHECK(pthread_join(thread,NULL)==0); CHECK(race.status==0);
        ack(race.handle,race.token,3,0);gate_destroy(&race.gate);
    }
    /* All sixteen replacements must still fit after every race, catching leaks
       and proving the public global pool is reused rather than merely observed. */
    uint64_t handles[16]; for(unsigned i=0;i<16;i++) handles[i]=create_cap(); for(unsigned i=0;i<16;i++) close_cap(handles[i]);
}
int main(int argc,char **argv) {
    CHECK(argc==3); cap_module=load(argv[1]);old_module=load(argv[2]);
    layouts();alias_preflight();limit_validation();bounds_and_unaligned();lifecycle();cancellation_and_stale_ack();mixed_pool_and_family();races();
    free(cap_module.bytes);free(old_module.bytes);
    printf("{\"public_c_checks\":%u,\"passed\":true,\"take_close_races\":48,\"ack_close_races\":48}\n",atomic_load_explicit(&checks,memory_order_relaxed));return 0;
}
