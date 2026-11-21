/* Original C consumer of Guest UI V1 admission and the native session ABI. */
#include "mixer_vm_guest_ui.h"
#include <assert.h>
#include <inttypes.h>
#include <stdio.h>
#include <string.h>

_Static_assert(MIXER_VM_GUEST_UI_ABI_VERSION==1u,"guest UI ABI");
typedef struct { uint8_t data[2048];size_t size; } Wasm;
static void byte(Wasm *w,uint8_t b) { assert(w->size<sizeof(w->data));w->data[w->size++]=b; }
static void count(Wasm *w,unsigned n) { do {byte(w,(uint8_t)((n&127)|(n>127?128:0)));n>>=7;}while(n); }
static void text(Wasm *w,const char *s) { count(w,(unsigned)strlen(s));while(*s)byte(w,(uint8_t)*s++); }
static void append(Wasm *w, const void *bytes, size_t size) {
    assert(size <= sizeof(w->data) - w->size);
    memcpy(w->data + w->size, bytes, size);
    w->size += size;
}
static void section(Wasm *w,uint8_t id,const Wasm *s) {
    byte(w,id);
    count(w,(unsigned)s->size);
    append(w,s->data,s->size);
}
static Wasm program(unsigned wrong_event, const Wasm *event, const Wasm *data) {
    Wasm w={{0,97,115,109,1,0,0,0},8},s={{0},0};
    /* () -> i32; (i32) -> i32; () -> (). No imports or start section. */
    const uint8_t types[]={3,0x60,0,1,0x7f,0x60,1,0x7f,1,0x7f,0x60,0,0};
    for(size_t i=0;i<sizeof(types);i++) {
        byte(&s,types[i]);
    }
    section(&w,1,&s);
    s.size=0;byte(&s,3);byte(&s,0);byte(&s,1);byte(&s,2);section(&w,3,&s);
    s.size=0;byte(&s,1);byte(&s,1);byte(&s,1);byte(&s,1);section(&w,5,&s);
    s.size=0;byte(&s,3);
    text(&s,"mixer_guest_ui_start_v1");byte(&s,0);byte(&s,0);
    text(&s,"mixer_guest_ui_event_v1");byte(&s,0);byte(&s,wrong_event?0:1);
    text(&s,"mixer_guest_capability_ready_v1");byte(&s,0);byte(&s,2);section(&w,7,&s);
    /* Startup returns zero and ready does nothing. */
    const uint8_t startup[]={3,4,0,0x41,0,0x0b};
    const uint8_t echo[]={0,0x20,0,0x0b};
    const uint8_t ready[]={2,0,0x0b};
    s.size=0;
    append(&s,startup,sizeof(startup));
    count(&s,event ? (unsigned)event->size : sizeof(echo));
    append(&s,event ? event->data : echo,event ? event->size : sizeof(echo));
    append(&s,ready,sizeof(ready));
    section(&w,10,&s);
    if (data) section(&w,11,data);
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
enum {
    PAGE_SIZE = 65536,
    EVENT_OFFSET = 8192,
    EVENT_CAPACITY = 4096,
    INITIAL_FRAME_OFFSET = 512,
    ZERO_FRAME_OFFSET = 0x0823,
    ONE_FRAME_OFFSET = 0x0c45,
    OTHER_FRAME_OFFSET = 0x1067,
    POINTERS_OFFSET = PAGE_SIZE - 9,
    TURN_FUEL = 64
};

#define BUTTON(digit) \
    "{\"id\":\"pick" digit "\",\"kind\":\"button\",\"properties\":{\"label\":\"" digit "\"}," \
    "\"children\":[],\"actions\":[{\"id\":\"pick." digit "\",\"event\":\"activate\"}]}"
#define EVENT_PREFIX "{\"actionID\":\"pick."
#define EVENT(digit) EVENT_PREFIX digit "\",\"event\":\"activate\",\"nodeID\":\"pick" digit \
    "\",\"revision\":1,\"schemaVersion\":1,\"sequence\":1,\"value\":null}"
#define RESULT_FRAME(label) \
    "{\"schemaVersion\":1,\"revision\":2,\"root\":{\"id\":\"status\",\"kind\":\"text\"," \
    "\"properties\":{\"text\":\"" label "\"},\"children\":[],\"actions\":[]}}"

static const char initial_frame[] =
    "{\"schemaVersion\":1,\"revision\":1,\"root\":{\"id\":\"root\",\"kind\":\"vStack\","
    "\"properties\":{},\"children\":[" BUTTON("0") "," BUTTON("1") "," BUTTON("9") "],\"actions\":[]}}";
static const char zero_frame[] = RESULT_FRAME("Zero");
static const char one_frame[] = RESULT_FRAME("One!");
static const char other_frame[] = RESULT_FRAME("Else");

/* Encode a nonnegative i32.const with signed LEB128. */
static void constant(Wasm *w, unsigned value) {
    byte(w, 0x41);
    while (value >= 64) {
        byte(w, (uint8_t)((value & 127) | 128));
        value >>= 7;
    }
    byte(w, (uint8_t)value);
}

static void segment(Wasm *w, unsigned offset, const void *bytes, unsigned size) {
    byte(w, 0); /* active, memory zero */
    constant(w, offset);
    byte(w, 0x0b);
    count(w, size);
    append(w, bytes, size);
}

static Wasm selection_program(void) {
    Wasm event = {{0}, 1}; /* no locals */
    const uint8_t length_arg[] = {0x20, 0};
    append(&event, length_arg, sizeof(length_arg));
    constant(&event, sizeof(EVENT("0")) - 1);
    const uint8_t length_check[] = {0x47, 0x04, 0x40, 0x00, 0x0b}; /* if !=, trap */
    append(&event, length_check, sizeof(length_check));

    constant(&event, 8); /* header.document_offset store destination */
    const uint8_t blocks[] = {0x02, 0x7f, 0x02, 0x40, 0x02, 0x40, 0x02, 0x40};
    append(&event, blocks, sizeof(blocks));
    constant(&event, EVENT_OFFSET + sizeof(EVENT_PREFIX) - 1);
    const uint8_t load_selector[] = {0x2d, 0, 0}; /* i32.load8_u */
    append(&event, load_selector, sizeof(load_selector));
    constant(&event, '0');
    const uint8_t dispatch[] = {0x6b, 0x0e, 2, 0, 1, 2, 0x0b}; /* sub; br_table 0 1 2; end */
    append(&event, dispatch, sizeof(dispatch));
    constant(&event, POINTERS_OFFSET - 1);
    const uint8_t zero_exit[] = {0x0c, 2, 0x0b}; /* branch with value to result block */
    append(&event, zero_exit, sizeof(zero_exit));
    constant(&event, POINTERS_OFFSET + 2);
    const uint8_t one_exit[] = {0x0c, 1, 0x0b};
    append(&event, one_exit, sizeof(one_exit));
    constant(&event, POINTERS_OFFSET + 6);
    const uint8_t load_and_store[] = {0x0b, 0x2f, 0, 1, 0x36, 2, 0};
    append(&event, load_and_store, sizeof(load_and_store)); /* end; unaligned load16_u offset=1; store */
    constant(&event, 12); /* header.document_length */
    constant(&event, sizeof(zero_frame) - 1);
    const uint8_t store_and_return[] = {0x36, 2, 0, 0x41, 0, 0x0b};
    append(&event, store_and_return, sizeof(store_and_return));

    uint8_t header[32] = {0};
    const uint32_t words[] = {0x3155494d, 32, INITIAL_FRAME_OFFSET, sizeof(initial_frame) - 1,
                              EVENT_OFFSET, EVENT_CAPACITY};
    for (size_t word = 0; word < sizeof(words) / sizeof(words[0]); ++word) {
        for (unsigned b = 0; b < 4; ++b)
            header[4 * word + b] = (uint8_t)(words[word] >> (8 * b));
    }
    /* At offsets 65527, 65530 and 65534. The default's load ends at 65536.
     * Both bytes of each pointer are nonzero and distinct. */
    const uint8_t pointers[] = {0x23, 0x08, 0xa5, 0x45, 0x0c, 0xa5, 0xa5, 0x67, 0x10};
    Wasm data = {{6}, 1};
    segment(&data, 0, header, sizeof(header));
    segment(&data, INITIAL_FRAME_OFFSET, initial_frame, sizeof(initial_frame) - 1);
    segment(&data, ZERO_FRAME_OFFSET, zero_frame, sizeof(zero_frame) - 1);
    segment(&data, ONE_FRAME_OFFSET, one_frame, sizeof(one_frame) - 1);
    segment(&data, OTHER_FRAME_OFFSET, other_frame, sizeof(other_frame) - 1);
    segment(&data, POINTERS_OFFSET, pointers, sizeof(pointers));
    return program(0, &event, &data);
}

static uint32_t word(const uint8_t *p) {
    return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}

static void read_frame(uint64_t h, uint32_t offset, const char *expected, int print_frame) {
    MixerVmReport report;
    uint8_t header[32], frame[sizeof(initial_frame)];
    assert(mixer_vm_capability_session_read_v1(h, 0, header, sizeof(header), &report) == 0);
    assert(word(header) == 0x3155494d && word(header + 4) == sizeof(header));
    assert(word(header + 8) == offset && word(header + 12) == strlen(expected));
    assert(word(header + 16) == EVENT_OFFSET && word(header + 20) == EVENT_CAPACITY);
    assert(word(header + 24) == 0 && word(header + 28) == 0);
    const uint32_t length = word(header + 12);
    assert(length <= sizeof(frame));
    assert(mixer_vm_capability_session_read_v1(h, word(header + 8), frame, length, &report) == 0);
    assert(memcmp(frame, expected, length) == 0);
    if (print_frame) printf("Guest UI V1 frame: %.*s\n", (int)length, (const char *)frame);
}

static void selection_execution(const char *fixture_path) {
    const Wasm w = selection_program();
    if (fixture_path) {
        FILE *output = fopen(fixture_path, "wbx");
        assert(output);
        assert(fwrite(w.data, 1, w.size, output) == w.size);
        assert(fclose(output) == 0);
    }
    const MixerVmLimits vm = {sizeof(vm), MIXER_VM_ABI_VERSION, TURN_FUEL, 1, 16, 1, 0};
    MixerVmReport report;
    const uint8_t startup[] = "mixer_guest_ui_start_v1";
    const uint8_t event[] = "mixer_guest_ui_event_v1";
    const uint32_t status = mixer_vm_capability_guest_ui_validate_v1(w.data, w.size, &vm, NULL, &report);
    if (status != 0)
        fprintf(stderr, "Selection guest validation: status=%u code=%s function=%u offset=%u %s\n",
                status, report.code, report.function, report.offset, report.message);
    assert(status == 0);
    assert(report.status == 0 && report.fuel_used == 0 && report.host_calls_used == 0);

    /* Host oracle: route each literal event to its expected document, without
     * evaluating the guest's branch depths or reading its pointer table. */
    const struct {
        const char *input;
        uint32_t offset;
        const char *frame;
    } cases[] = {
        {EVENT("0"), ZERO_FRAME_OFFSET, zero_frame},
        {EVENT("1"), ONE_FRAME_OFFSET, one_frame},
        {EVENT("9"), OTHER_FRAME_OFFSET, other_frame}
    };
    for (size_t index = 0; index < sizeof(cases) / sizeof(cases[0]); ++index) {
        uint64_t h = 0;
        assert(mixer_vm_capability_session_create_v1(w.data, w.size, startup, sizeof(startup) - 1,
                                                    &vm, NULL, &h, &report) == 0 && h != 0);
        assert(mixer_vm_capability_session_startup_v1(h, &report) == 0);
        assert(report.status == 0 && report.value_type == 1 && report.value == 0);
        assert(report.fuel_used > 0 && report.fuel_used <= TURN_FUEL && report.host_calls_used == 0);
        const uint64_t startup_fuel = report.fuel_used;
        read_frame(h, INITIAL_FRAME_OFFSET, initial_frame, 0);
        assert(mixer_vm_capability_session_enable_v1(h, &report) == 0);

        const size_t length = strlen(cases[index].input);
        const MixerVmValue arg = {1, 0, (int64_t)length};
        assert(mixer_vm_capability_session_write_v1(h, EVENT_OFFSET, (const uint8_t *)cases[index].input,
                                                   length, &report) == 0);
        assert(mixer_vm_capability_session_invoke_v1(h, event, sizeof(event) - 1, &arg, 1, &report) == 0);
        assert(report.status == 0 && report.value_type == 1 && report.value == 0);
        assert(report.fuel_used > 0 && report.fuel_used <= TURN_FUEL && report.host_calls_used == 0);
        printf("Guest UI V1 selection: digit=%c bytes=%zu offset=%" PRIu32
               " startup_fuel=%" PRIu64 " event_fuel=%" PRIu64 " host_calls=%" PRIu64 "\n",
               cases[index].input[sizeof(EVENT_PREFIX) - 1], length, cases[index].offset,
               startup_fuel, report.fuel_used, report.host_calls_used);
        read_frame(h, cases[index].offset, cases[index].frame, 1);
        assert(mixer_vm_capability_session_close_v1(h, &report) == 0);
        uint8_t retired;
        assert(mixer_vm_capability_session_read_v1(h, 0, &retired, 1, &report) == 3);
        assert(report.status == 3 && strcmp((const char *)report.code, "invalid_arguments") == 0);
    }
    printf("Guest UI V1 execution: %zu bytes, 3 sessions closed and stale reads rejected\n", w.size);
}

int main(int argc, char **argv) {
    assert(argc == 1 || argc == 2);
    Wasm w=program(0,NULL,NULL),wrong=program(1,NULL,NULL);MixerVmReport r;
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
    selection_execution(argc == 2 ? argv[1] : NULL);
    /* Validation and the retired executions leave all sixteen mixed slots free. */
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
