/* Original one-archive public C registry probe. No native I/O or VM imports. */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "mixer_vm_capability.h"
typedef struct { uint8_t bytes[512]; size_t count; } Bytes;
static void byte(Bytes *b,uint8_t value) { assert(b->count<sizeof(b->bytes)); b->bytes[b->count++]=value; }
static void number(Bytes *b,unsigned value) { do { byte(b,(uint8_t)((value&127)|(value>127?128:0)));value>>=7; } while(value); }
static void name(Bytes *b,const char *value) { size_t n=strlen(value);number(b,(unsigned)n);for(size_t i=0;i<n;i++)byte(b,(uint8_t)value[i]); }
static void section(Bytes *m,uint8_t id,const Bytes *s) { byte(m,id);number(m,(unsigned)s->count);for(size_t i=0;i<s->count;i++)byte(m,s->bytes[i]); }
static Bytes guest(void) {
    Bytes m={{0,97,115,109,1,0,0,0},8},s={{0},0};
    byte(&s,1);byte(&s,0x60);byte(&s,0);byte(&s,0);section(&m,1,&s);
    s.count=0;byte(&s,2);byte(&s,0);byte(&s,0);section(&m,3,&s);
    s.count=0;byte(&s,1);byte(&s,1);byte(&s,1);byte(&s,1);section(&m,5,&s);
    s.count=0;byte(&s,2);name(&s,"start");byte(&s,0);byte(&s,0);name(&s,"mixer_guest_capability_ready_v1");byte(&s,0);byte(&s,1);section(&m,7,&s);
    s.count=0;byte(&s,2);for(unsigned i=0;i<2;i++){byte(&s,2);byte(&s,0);byte(&s,0x0b);}section(&m,10,&s);
    return m;
}
int main(void) {
    Bytes module=guest();MixerVmReport report;uint64_t handles[16]={0};unsigned checks=0;
    for(unsigned i=0;i<16;i++) {
        uint32_t status=i%2?mixer_vm_capability_session_create_v1(module.bytes,module.count,(const uint8_t*)"start",5,NULL,NULL,&handles[i],&report):mixer_vm_session_create_v1(3,module.bytes,module.count,NULL,&handles[i],&report);
        if(status)fprintf(stderr,"create index%u status%u code=%s message=%s\n",i,status,report.code,report.message);
        assert(status==0&&report.status==0&&handles[i]!=0);checks++;
    }
    uint64_t extra=99;
    assert(mixer_vm_session_create_v1(3,module.bytes,module.count,NULL,&extra,&report)==2&&extra==0);checks++;
    extra=99;assert(mixer_vm_capability_session_create_v1(module.bytes,module.count,(const uint8_t*)"start",5,NULL,NULL,&extra,&report)==2&&extra==0);checks++;
    for(unsigned i=0;i<16;i++) {
        uint32_t wrong=i%2?mixer_vm_session_close_v1(handles[i],&report):mixer_vm_capability_session_close_v1(handles[i],&report);
        assert(wrong==3);checks++;
        uint32_t status=i%2?mixer_vm_capability_session_close_v1(handles[i],&report):mixer_vm_session_close_v1(handles[i],&report);
        assert(status==0);checks++;
    }
    assert(mixer_vm_capability_session_create_v1(module.bytes,module.count,(const uint8_t*)"start",5,NULL,NULL,&extra,&report)==0);checks++;
    assert(mixer_vm_capability_session_close_v1(extra,&report)==0);checks++;
    printf("One archive mixed registry: passed%u checks; shared16 slots and distinct handle families\n",checks);
    return 0;
}
