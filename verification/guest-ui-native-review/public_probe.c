/* Original independent review probe: hand-encoded core Wasm, public C ABI only.
 * No VM fixture/builder source is included; no guest code is executed. */
#include "mixer_vm_guest_ui.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

typedef uint32_t (*UIValidator)(const uint8_t *, size_t,
    const MixerVmLimits *, const MixerVmCapabilityLimitsV1 *, MixerVmReport *);
_Static_assert(_Generic(&mixer_vm_capability_guest_ui_validate_v1,
    UIValidator: 1, default: 0), "guest UI public declaration");
_Static_assert(sizeof(MixerVmReport) == 352, "report size");
_Static_assert(sizeof(MixerVmLimits) == 32, "VM limits size");
_Static_assert(sizeof(MixerVmCapabilityLimitsV1) == 32, "cap limits size");

typedef struct { uint8_t p[16384]; size_t n; } Buffer;
static void put(Buffer *b, uint8_t v) { assert(b->n < sizeof(b->p)); b->p[b->n++] = v; }
static void copy(Buffer *b, const void *p, size_t n) {
    assert(n <= sizeof(b->p) - b->n); memcpy(b->p + b->n, p, n); b->n += n;
}
static void leb(Buffer *b, uint32_t v) {
    do { uint8_t a = v & 0x7f; v >>= 7; put(b, a | (v ? 0x80 : 0)); } while (v);
}
static void text(Buffer *b, const char *s) { leb(b, (uint32_t)strlen(s)); copy(b, s, strlen(s)); }
static void sec(Buffer *b, uint8_t id, const Buffer *contents) {
    put(b, id); leb(b, (uint32_t)contents->n); copy(b, contents->p, contents->n);
}
static const char *const labels[] = {
    "mixer_guest_ui_start_v1", "mixer_guest_ui_event_v1", "mixer_guest_capability_ready_v1"
};
/* Each row gives parameter count, parameter bytes, result count, result byte. */
static const uint8_t signature[][6] = {
    {0,0,0,0,1,0x7f}, {1,0x7f,0,0,1,0x7f}, {0,0,0,0,0,0},
    {0,0,0,0,1,0x7e}, {0,0,0,0,1,0x7d}, {0,0,0,0,1,0x7c},
    {1,0x7e,0,0,1,0x7f}, {1,0x7d,0,0,1,0x7f}, {1,0x7c,0,0,1,0x7f},
    {1,0x7f,0,0,0,0}, {2,0x7f,0x7f,0,1,0x7f}, {2,0x7f,0x7e,0,1,0x7f}
};
typedef struct {
    unsigned type[3]; int missing; int wrong_kind; int wrong_index;
    unsigned helper_defect; unsigned memory_defect; int start_section;
    int changed_name; int unknown_import;
} Shape;
static Shape ordinary(void) {
    Shape s = {{0,1,2},-1,-1,-1,0,0,0,-1,0}; return s;
}
static Buffer module(Shape s) {
    Buffer m = {{0},0}, b = {{0},0};
    const uint8_t magic[] = {0,97,115,109,1,0,0,0}; copy(&m, magic, sizeof(magic));
    leb(&b, (uint32_t)(sizeof(signature)/sizeof(signature[0])));
    for (unsigned i = 0; i < sizeof(signature)/sizeof(signature[0]); ++i) {
        put(&b,0x60); put(&b,signature[i][0]);
        copy(&b,signature[i]+1,signature[i][0]); put(&b,signature[i][4]);
        if(signature[i][4]) put(&b,signature[i][5]);
    }
    sec(&m,1,&b); b.n=0;
    put(&b,1); text(&b,"mixer"); text(&b,s.unknown_import ? "unapproved" : "checkpoint");
    put(&b,0); put(&b,2); sec(&m,2,&b); b.n=0;
    put(&b,4); for(unsigned i=0;i<3;i++) put(&b,(uint8_t)s.type[i]);
    put(&b,s.helper_defect==1 ? 0 : 2); sec(&m,3,&b); b.n=0;
    const uint8_t table[] = {1,0x70,1,1,1}; copy(&b,table,sizeof(table)); sec(&m,4,&b); b.n=0;
    if(s.memory_defect!=1) {
        put(&b,s.memory_defect==2 ? 2 : 1);
        put(&b,s.memory_defect==3 ? 3 : 1); put(&b,1); put(&b,1);
        if(s.memory_defect==2) {put(&b,1);put(&b,1);put(&b,1);}
        sec(&m,5,&b); b.n=0;
    }
    const uint8_t global[] = {1,0x7f,0,0x41,0,0x0b};
    copy(&b,global,sizeof(global)); sec(&m,6,&b); b.n=0;
    put(&b,s.missing>=0 ? 2 : 3);
    for(unsigned i=0;i<3;i++) {
        if((int)i==s.missing) continue;
        text(&b,(int)i==s.changed_name ? "mixer_guest_ui_event_v1_extra" : labels[i]);
        put(&b,(int)i==s.wrong_kind ? 3 : 0);
        put(&b,(int)i==s.wrong_kind || (int)i==s.wrong_index ? 0 : (uint8_t)(i+1));
    }
    sec(&m,7,&b); b.n=0;
    if(s.start_section) {put(&b,4);sec(&m,8,&b);b.n=0;}
    put(&b,4);
    /* unreachable/end is valid for every signature and would trap on invocation. */
    for(unsigned i=0;i<4;i++) {
        if(i==3 && s.helper_defect) {
            if(s.helper_defect==1) {const uint8_t body[]={0,0x42,0,0x0b};leb(&b,sizeof(body));copy(&b,body,sizeof(body));}
            else {const uint8_t body[]={0,0xfd,0x0b};leb(&b,sizeof(body));copy(&b,body,sizeof(body));}
        } else {put(&b,3);put(&b,0);put(&b,0);put(&b,0x0b);}
    }
    sec(&m,10,&b); return m;
}
static unsigned checks;
static void report_check(uint32_t status, uint32_t expected, const MixerVmReport *r) {
    if(status!=expected) fprintf(stderr,"case %u: status %u expected %u: %s\n",checks,status,expected,r->code);
    assert(status==expected && r->status==expected && r->abi_version==1 && r->reserved==0);
    assert(r->fuel_used==0 && r->host_calls_used==0 && r->value_type==0 && r->value==0);
    assert(memchr(r->code,0,sizeof(r->code)) && memchr(r->message,0,sizeof(r->message))); checks++;
}
static void check_shape(Shape s, uint32_t expected, const char *code) {
    Buffer b=module(s); MixerVmReport r;
    report_check(mixer_vm_capability_guest_ui_validate_v1(b.p,b.n,NULL,NULL,&r),expected,&r);
    if(code) assert(strcmp((const char *)r.code,code)==0);
    if(code && strcmp(code,"capability_export")==0) assert(r.function==UINT32_MAX && r.offset==0);
}
int main(void) {
    check_shape(ordinary(),0,NULL);
    for(unsigned required=0;required<3;required++) {
        for(unsigned t=0;t<sizeof(signature)/sizeof(signature[0]);t++) {
            Shape s=ordinary();s.type[required]=t;
            check_shape(s,t==required ? 0 : 1,t==required ? NULL : "capability_export");
            if(required==0 && t>=2 && t<=5) {
                Buffer b=module(s); MixerVmReport r;
                report_check(mixer_vm_capability_validate_v1(b.p,b.n,(const uint8_t *)labels[0],strlen(labels[0]),NULL,NULL,&r),0,&r);
            }
        }
        Shape s=ordinary();s.missing=(int)required;check_shape(s,1,"capability_export");
        s=ordinary();s.wrong_kind=(int)required;check_shape(s,1,"capability_export");
        s=ordinary();s.wrong_index=(int)required;check_shape(s,1,"capability_export");
        s=ordinary();s.changed_name=(int)required;check_shape(s,1,"capability_export");
    }
    Shape s=ordinary();s.missing=1;s.helper_defect=1;check_shape(s,1,"validation");
    s=ordinary();s.missing=1;s.helper_defect=2;check_shape(s,1,"unsupported");
    s=ordinary();s.missing=1;s.unknown_import=1;check_shape(s,1,"unsupported");
    s=ordinary();s.start_section=1;check_shape(s,1,"unsupported");
    for(unsigned mem=1;mem<=3;mem++){s=ordinary();s.memory_defect=mem;check_shape(s,1,NULL);}
    Buffer b=module(ordinary()); MixerVmReport r;
    uint8_t arena[2048], before[2048];memset(arena,0xa9,sizeof(arena));
    memcpy(before,arena,sizeof(arena));MixerVmReport *out=(MixerVmReport *)(void *)(arena+1025);
    /* Exercise both ends and the contained direction of report/read aliases. */
    for(unsigned kind=0;kind<3;kind++) for(unsigned side=0;side<3;side++) {
        size_t width=kind==0 ? 384 : 32;
        size_t address=side==0 ? 1025-width+1 : side==1 ? 1025+sizeof(MixerVmReport)-1 : 1026;
        const uint8_t *p=arena+address;
        uint32_t result=mixer_vm_capability_guest_ui_validate_v1(kind==0?p:b.p,kind==0?width:b.n,
            kind==1?(const MixerVmLimits *)(const void *)p:NULL,
            kind==2?(const MixerVmCapabilityLimitsV1 *)(const void *)p:NULL,out);
        assert(result==3 && memcmp(arena,before,sizeof(arena))==0); checks++;
    }
    MixerVmLimits vm={32,1,1000000,64,4096,64,1024};
    MixerVmCapabilityLimitsV1 cap={32,1,8,30000,50,0,8388608};
    memcpy(arena+1,&vm,sizeof(vm));memcpy(arena+65,&cap,sizeof(cap));
    uint32_t status=mixer_vm_capability_guest_ui_validate_v1(b.p,b.n,
        (const MixerVmLimits *)(const void *)(arena+1),
        (const MixerVmCapabilityLimitsV1 *)(const void *)(arena+65),out);
    memcpy(&r,out,sizeof(r));report_check(status,0,&r);
    assert(arena[0]==0xa9 && arena[33]==0xa9 && arena[64]==0xa9 && arena[97]==0xa9 && arena[1024]==0xa9 && arena[1377]==0xa9);
    uint64_t handles[16];
    for(unsigned i=0;i<16;i++) assert(mixer_vm_capability_session_create_v1(b.p,b.n,
        (const uint8_t *)labels[0],strlen(labels[0]),NULL,NULL,&handles[i],&r)==0);
    uint64_t rejected=99;
    assert(mixer_vm_capability_session_create_v1(b.p,b.n,(const uint8_t *)labels[0],strlen(labels[0]),NULL,NULL,&rejected,&r)==3 && rejected==0);
    for(unsigned i=0;i<64;i++) check_shape(ordinary(),0,NULL);
    s=ordinary();s.missing=1;check_shape(s,1,"capability_export");
    for(unsigned i=0;i<16;i++) assert(mixer_vm_capability_session_close_v1(handles[i],&r)==0);
    printf("independent public C guest-UI review: %u checks passed; exact signatures, defined exports, complete validation precedence, unaligned/alias storage and full capability registry\n",checks);
    return 0;
}
