/* Independently authored public-header C client and core Wasm binary encoder.
 * Host ABI evidence only: no Swift, UI renderer, device or release claim. */
#include "mixer_vm_guest_ui.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <limits.h>
_Static_assert(sizeof(void *) == 8, "qualified pointer width");
_Static_assert(sizeof(MixerVmLimits) == 32, "VM layout");
_Static_assert(sizeof(MixerVmCapabilityLimitsV1) == 32, "capability layout");
_Static_assert(sizeof(MixerVmReport) == 352, "report layout");
_Static_assert(offsetof(MixerVmReport, fuel_used) == 24, "fuel offset");
_Static_assert(offsetof(MixerVmReport, code) == 48, "code offset");
typedef uint32_t (*Validator)(const uint8_t *, size_t, const MixerVmLimits *, const MixerVmCapabilityLimitsV1 *, MixerVmReport *);
_Static_assert(_Generic(&mixer_vm_capability_guest_ui_validate_v1, Validator: 1, default: 0), "public signature");
typedef struct { uint8_t bytes[1024]; size_t length; } Bytes;
static void byte(Bytes *b, uint8_t v) { assert(b->length < sizeof(b->bytes)); b->bytes[b->length++] = v; }
static void u32(Bytes *b, uint32_t v) { do { uint8_t c = v & 127; v >>= 7; byte(b, c | (v ? 128 : 0)); } while (v); }
static void raw(Bytes *b, const void *p, size_t n) { assert(n <= sizeof(b->bytes)-b->length); memcpy(b->bytes+b->length,p,n); b->length+=n; }
static void name(Bytes *b, const char *s) { u32(b,(uint32_t)strlen(s)); raw(b,s,strlen(s)); }
static void section(Bytes *m, uint8_t id, Bytes b) { byte(m,id); u32(m,(uint32_t)b.length); raw(m,b.bytes,b.length); }
static Bytes program(unsigned defect) {
    Bytes m={0}, b={0}; const uint8_t header[]={0,97,115,109,1,0,0,0}; raw(&m,header,sizeof(header));
    const uint8_t types[]={3,0x60,0,1,0x7f,0x60,1,0x7f,1,0x7f,0x60,0,0}; raw(&b,types,sizeof(types)); section(&m,1,b);
    b.length=0; byte(&b,3); byte(&b,defect==2 ? 2 : 0); byte(&b,1); byte(&b,2); section(&m,3,b);
    b.length=0; const uint8_t memory[]={1,1,1,1}; raw(&b,memory,sizeof(memory)); section(&m,5,b);
    b.length=0; byte(&b,defect==1 ? 2 : 3); const char *labels[]={"mixer_guest_ui_start_v1","mixer_guest_ui_event_v1","mixer_guest_capability_ready_v1"};
    for (unsigned i=0;i<3;i++) { if(defect==1&&i==1) continue; name(&b,labels[i]); byte(&b,defect==3&&i==1 ? 2 : 0); u32(&b,defect==3&&i==1 ? 0 : i); } section(&m,7,b);
    if(defect==4) { b.length=0; byte(&b,2); section(&m,8,b); }
    b.length=0; byte(&b,3);
    /* Startup intentionally traps if run; validate-only must still succeed. */
    const uint8_t start[]={0,0,0x0b}; u32(&b,sizeof(start)); raw(&b,start,sizeof(start));
    const uint8_t event[]={0,0x20,0,0x0b}; u32(&b,sizeof(event)); raw(&b,event,sizeof(event));
    const uint8_t ready[]={0,0x0b}; u32(&b,sizeof(ready)); raw(&b,ready,sizeof(ready)); section(&m,10,b); return m;
}
static unsigned checks;
static void status(uint32_t got, uint32_t want, const MixerVmReport *r) {
    if(got!=want) fprintf(stderr,"status=%u expected=%u code=%s\n",got,want,r->code);
    assert(got==want&&r->status==want); assert(r->abi_version==1&&r->reserved==0);
    assert(r->value_type==0&&r->value==0&&r->fuel_used==0&&r->host_calls_used==0); checks++;
}
int main(void) {
    Validator validate=&mixer_vm_capability_guest_ui_validate_v1; MixerVmReport r;
    for(unsigned i=0;i<=4;i++) { Bytes m=program(i); status(validate(m.bytes,m.length,NULL,NULL,&r),i==0?0:1,&r);
        if(i>=1&&i<=3) { assert(strcmp((const char*)r.code,"capability_export")==0); assert(r.function==UINT32_MAX&&r.offset==0); }
        if(i==4) assert(strcmp((const char*)r.code,"unsupported")==0);
    }
    Bytes m=program(0); uint8_t storage[2048], original[2048]; memset(storage,0xa5,sizeof(storage)); memcpy(original,storage,sizeof(storage));
    MixerVmReport *out=(MixerVmReport*)(void*)(storage+1025);
    assert(validate(NULL,1,NULL,NULL,out)==3); assert(memcmp(storage,original,sizeof(storage))==0); checks++;
    assert(validate((const uint8_t*)UINTPTR_MAX,1,NULL,NULL,out)==3); assert(memcmp(storage,original,sizeof(storage))==0); checks++;
    assert(validate((const uint8_t*)1,4*1024*1024+1,NULL,NULL,out)==3); assert(memcmp(storage,original,sizeof(storage))==0); checks++;
    assert(validate(m.bytes,m.length,(const MixerVmLimits*)UINTPTR_MAX,NULL,out)==3); assert(memcmp(storage,original,sizeof(storage))==0); checks++;
    assert(validate(m.bytes,m.length,NULL,(const MixerVmCapabilityLimitsV1*)UINTPTR_MAX,out)==3); assert(memcmp(storage,original,sizeof(storage))==0); checks++;
    assert(validate(m.bytes,m.length,NULL,NULL,NULL)==3); checks++;
    assert(validate((const uint8_t*)out,8,NULL,NULL,out)==3); assert(memcmp(storage,original,sizeof(storage))==0); checks++;
    assert(validate(m.bytes,m.length,(const MixerVmLimits*)out,NULL,out)==3); assert(memcmp(storage,original,sizeof(storage))==0); checks++;
    assert(validate(m.bytes,m.length,NULL,(const MixerVmCapabilityLimitsV1*)out,out)==3); assert(memcmp(storage,original,sizeof(storage))==0); checks++;
    MixerVmLimits vm={32,1,1000000,64,4096,64,1024}; MixerVmCapabilityLimitsV1 cap={32,1,8,30000,50,0,8388608};
    memcpy(storage+1,&vm,sizeof(vm)); memcpy(storage+65,&cap,sizeof(cap));
    uint32_t s=validate(m.bytes,m.length,(const MixerVmLimits*)(void*)(storage+1),(const MixerVmCapabilityLimitsV1*)(void*)(storage+65),out);
    memcpy(&r,out,sizeof(r)); status(s,0,&r); assert(storage[0]==0xa5&&storage[64]==0xa5&&storage[1024]==0xa5);
    uint64_t handles[16]; const uint8_t empty[]={0,97,115,109,1,0,0,0};
    for(unsigned i=0;i<16;i++) assert(mixer_vm_session_create_v1(1,empty,sizeof(empty),NULL,&handles[i],&r)==0);
    status(validate(m.bytes,m.length,NULL,NULL,&r),0,&r);
    for(unsigned i=0;i<16;i++) assert(mixer_vm_session_close_v1(handles[i],&r)==0);
    printf("guest-UI public C ABI: %u checks passed; pointer/layout/export/no-execution/full-registry host evidence\n",checks); return 0;
}
