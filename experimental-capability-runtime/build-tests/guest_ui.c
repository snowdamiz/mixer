/* Original C consumer of the additive UI validator and the shared registry. */
#include "mixer_vm_guest_ui.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

_Static_assert(MIXER_VM_GUEST_UI_ABI_VERSION==1u,"guest UI ABI");
typedef struct { uint8_t data[1024];size_t size; } Wasm;
static void byte(Wasm *w,uint8_t b) { assert(w->size<sizeof(w->data));w->data[w->size++]=b; }
static void count(Wasm *w,unsigned n) { do {byte(w,(uint8_t)((n&127)|(n>127?128:0)));n>>=7;}while(n); }
static void text(Wasm *w,const char *s) { count(w,(unsigned)strlen(s));while(*s)byte(w,(uint8_t)*s++); }
static void section(Wasm *w,uint8_t id,const Wasm *s) { byte(w,id);count(w,(unsigned)s->size);for(size_t i=0;i<s->size;i++)byte(w,s->data[i]); }
static Wasm program(unsigned wrong_event) {
    Wasm w={{0,97,115,109,1,0,0,0},8},s={{0},0};
    /* () -> i32; (i32) -> i32; () -> (). No imports or start section. */
    const uint8_t types[]={3,0x60,0,1,0x7f,0x60,1,0x7f,1,0x7f,0x60,0,0};
    for(size_t i=0;i<sizeof(types);i++)byte(&s,types[i]);section(&w,1,&s);
    s.size=0;byte(&s,3);byte(&s,0);byte(&s,1);byte(&s,2);section(&w,3,&s);
    s.size=0;byte(&s,1);byte(&s,1);byte(&s,1);byte(&s,1);section(&w,5,&s);
    s.size=0;byte(&s,3);
    text(&s,"mixer_guest_ui_start_v1");byte(&s,0);byte(&s,0);
    text(&s,"mixer_guest_ui_event_v1");byte(&s,0);byte(&s,wrong_event?0:1);
    text(&s,"mixer_guest_capability_ready_v1");byte(&s,0);byte(&s,2);section(&w,7,&s);
    /* Start returns zero, event returns its argument, ready does nothing. */
    const uint8_t bodies[]={3,4,0,0x41,0,0x0b,4,0,0x20,0,0x0b,2,0,0x0b};
    s.size=0;for(size_t i=0;i<sizeof(bodies);i++)byte(&s,bodies[i]);section(&w,10,&s);
    return w;
}
static unsigned checks;
static void valid(const Wasm *w) {
    MixerVmReport r;
    uint32_t status=mixer_vm_capability_guest_ui_validate_v1(w->data,w->size,NULL,NULL,&r);
    if(status)fprintf(stderr,"UI validate status%u code=%s message=%s\n",status,r.code,r.message);
    assert(status==0&&r.status==0&&r.abi_version==1);
    assert(r.fuel_used==0&&r.host_calls_used==0&&r.value_type==0&&r.value==0);checks++;
}
int main(void) {
    Wasm w=program(0),wrong=program(1);MixerVmReport r;
    valid(&w);
    assert(mixer_vm_capability_guest_ui_validate_v1(wrong.data,wrong.size,NULL,NULL,&r)==1);
    assert(r.status==1&&strcmp((const char*)r.code,"capability_export")==0&&r.function==UINT32_MAX&&r.offset==0);
    assert(r.fuel_used==0&&r.host_calls_used==0);checks++;
    /* The same valid Wasm still passes the unchanged capability validator. */
    const uint8_t *start=(const uint8_t*)"mixer_guest_ui_start_v1";
    assert(mixer_vm_capability_validate_v1(wrong.data,wrong.size,start,23,NULL,NULL,&r)==0);checks++;
    uint8_t storage[1024],before[1024];memset(storage,0xa5,sizeof(storage));memcpy(before,storage,sizeof(storage));
    MixerVmReport *unaligned=(MixerVmReport*)(void*)(storage+1);
    assert(mixer_vm_capability_guest_ui_validate_v1(NULL,w.size,NULL,NULL,unaligned)==3);
    assert(memcmp(storage,before,sizeof(storage))==0);checks++;
    assert(mixer_vm_capability_guest_ui_validate_v1(storage+1,8,NULL,NULL,unaligned)==3);
    assert(memcmp(storage,before,sizeof(storage))==0);checks++;
    assert(mixer_vm_capability_guest_ui_validate_v1(w.data,w.size,NULL,NULL,NULL)==3);checks++;
    assert(mixer_vm_capability_guest_ui_validate_v1(w.data,w.size,NULL,NULL,unaligned)==0);
    memcpy(&r,storage+1,sizeof(r));assert(r.status==0&&r.fuel_used==0&&r.host_calls_used==0);checks++;
    /* Validation cannot reserve a session: all sixteen mixed slots remain free. */
    uint64_t handles[16]={0};
    for(unsigned i=0;i<16;i++) {
        uint32_t status=i%2?mixer_vm_capability_session_create_v1(w.data,w.size,start,23,NULL,NULL,&handles[i],&r):mixer_vm_session_create_v1(3,w.data,w.size,NULL,&handles[i],&r);
        assert(status==0&&handles[i]!=0);checks++;
    }
    valid(&w); /* No registry reservation is required even at capacity. */
    uint64_t extra=99;
    assert(mixer_vm_capability_session_create_v1(w.data,w.size,start,23,NULL,NULL,&extra,&r)==3&&extra==0);checks++;
    for(unsigned i=0;i<16;i++) {
        uint32_t status=i%2?mixer_vm_capability_session_close_v1(handles[i],&r):mixer_vm_session_close_v1(handles[i],&r);
        assert(status==0);checks++;
    }
    valid(&w);
    printf("Guest UI public C smoke: passed%u checks; validate-only ABI and one shared registry\n",checks);
    return 0;
}
