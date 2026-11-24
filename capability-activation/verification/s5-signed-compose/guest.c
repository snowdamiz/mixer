#include <stdint.h>

#ifdef PRIOR
#define INITIAL_TITLE "Prior editor"
#else
#define INITIAL_TITLE "Candidate editor"
#endif

static const char document_start[] =
    ",\"root\":{\"id\":\"editor\",\"kind\":\"vStack\",\"properties\":{},\"actions\":[],\"children\":["
    "{\"id\":\"title\",\"kind\":\"textField\",\"properties\":{\"axis\":\"horizontal\",\"label\":\"Title\",\"value\":\"";
static const char document_middle[] =
    "\"},\"children\":[],\"actions\":[{\"id\":\"draft\",\"event\":\"textChange\"}]},"
    "{\"id\":\"save\",\"kind\":\"button\",\"properties\":{\"label\":\"Save\"},\"children\":[],"
    "\"actions\":[{\"id\":\"commit\",\"event\":\"activate\"}]},"
    "{\"id\":\"readback\",\"kind\":\"text\",\"properties\":{\"text\":\"";
static const char document_end[] = "\"},\"children\":[],\"actions\":[]}]}}";
static const char success[] =
    "{\"abi\":1,\"capability\":\"storage.keyValue.v1\",\"operation\":\"put\",\"outcome\":{\"kind\":\"success\",\"value\":{\"committed\":true}},"
    "\"schemaHash\":\"4a311222c978ddd0982e8dfbcf3d4864b856a80bcc1efb3b725adede7f8e22fd\"}";

static char input[1048576];
static char document[3072];
static char title[512];
static char escaped[1024];
static char completion[256];
static char put[768];
static uint32_t title_length;
static uint32_t escaped_length;
static uint32_t completion_size;
static uint64_t request;
static uint32_t header[8];
static uint32_t delivered;
static uint32_t revision = 1;
static uint32_t saves;

__attribute__((import_module("mixer.capability.v1"), import_name("storage_put")))
extern uint32_t storage_put(const char *, uint32_t, uint64_t *);
__attribute__((import_module("mixer.capability.v1"), import_name("poll")))
extern uint32_t poll(uint64_t, char *, uint32_t, uint32_t *);

static uint32_t append(char *out, uint32_t start, const char *source, uint32_t count) {
    uint32_t i = 0;
    for (; count - i >= 4; i += 4) {
        __builtin_memcpy_inline(out + start + i, source + i, 4);
    }
    for (; i < count; ++i) out[start + i] = source[i];
    return start + count;
}

static int equal(const char *left, const char *right, uint32_t count) {
    uint32_t i = 0;
    for (; count - i >= 4; i += 4) {
        uint32_t a, b;
        __builtin_memcpy_inline(&a, left + i, 4);
        __builtin_memcpy_inline(&b, right + i, 4);
        if (a != b) return 0;
    }
    for (; i < count; ++i) if (left[i] != right[i]) return 0;
    return 1;
}

static uint32_t append_number(char *out, uint32_t at, uint32_t number) {
    char digits[10];
    uint32_t count = 0;
    do {
        digits[count++] = '0' + number % 10;
        number /= 10;
    } while (number);
    while (count) out[at++] = digits[--count];
    return at;
}

static void publish(void) {
    const char initial[] = INITIAL_TITLE;
    const char *value = saves ? escaped : initial;
    uint32_t length = saves ? escaped_length : sizeof(initial) - 1;
    const char prefix[] = "{\"schemaVersion\":1,\"revision\":";
    uint32_t at = append(document, 0, prefix, sizeof(prefix) - 1);
    at = append_number(document, at, revision);
    at = append(document, at, document_start, sizeof(document_start) - 1);
    at = append(document, at, value, length);
    at = append(document, at, document_middle, sizeof(document_middle) - 1);
    at = append_number(document, at, saves);
    at = append(document, at, ": ", 2);
    at = append(document, at, value, length);
    header[2] = (uintptr_t)document;
    header[3] = append(document, at, document_end, sizeof(document_end) - 1);
}

static void take_title(uint32_t length, uint32_t prefix) {
    if (length < prefix + 3 || length > prefix + sizeof(escaped) + 2 ||
        input[length - 2] != '"' || input[length - 1] != '}') {
        __builtin_trap();
    }
    escaped_length = length - prefix - 2;
    append(escaped, 0, input + prefix, escaped_length);
    title_length = 0;
    for (uint32_t i = 0; i < escaped_length; ++i) {
        unsigned char byte = escaped[i];
        if (byte == '\\') {
            if (++i == escaped_length) __builtin_trap();
            byte = escaped[i];
            if (byte != '\\' && byte != '"' && byte != '/') __builtin_trap();
        } else if (byte == '"' || byte < 32) {
            __builtin_trap();
        }
        if (title_length == sizeof(title)) __builtin_trap();
        title[title_length++] = (char)byte;
    }
}

static void save_title(void) {
    static const char alphabet[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    static const char prefix[] = "{\"namespace\":\"material_test\",\"key\":\"s5-title\",\"valueBase64\":\"";
    uint32_t at = append(put, 0, prefix, sizeof(prefix) - 1);
    for (uint32_t i = 0; i < title_length; i += 3) {
        uint32_t bytes = (uint32_t)(unsigned char)title[i] << 16;
        if (i + 1 < title_length) bytes |= (uint32_t)(unsigned char)title[i + 1] << 8;
        if (i + 2 < title_length) bytes |= (unsigned char)title[i + 2];
        put[at++] = alphabet[bytes >> 18];
        put[at++] = alphabet[(bytes >> 12) & 63];
        put[at++] = i + 1 < title_length ? alphabet[(bytes >> 6) & 63] : '=';
        put[at++] = i + 2 < title_length ? alphabet[bytes & 63] : '=';
    }
    at = append(put, at, "\"}", 2);
    if (storage_put(put, at, &request) != 0) __builtin_trap();
}

uint32_t mixer_guest_ui_start_v2(void) {
    header[0] = 0x3249554d;
    header[1] = sizeof(header);
    header[4] = (uintptr_t)input;
    header[5] = sizeof(input);
    publish();
    return (uintptr_t)header;
}

uint32_t mixer_guest_ui_event_v2(uint32_t length) {
    static const char draft_prefix[] =
        "{\"actionID\":\"draft\",\"event\":\"textChange\",\"nodeID\":\"title\",\"revision\":";
    static const char save_prefix[] =
        "{\"actionID\":\"commit\",\"event\":\"activate\",\"nodeID\":\"save\",\"revision\":";
    static const char sequence_field[] = ",\"schemaVersion\":1,\"sequence\":";
    static const char draft_value[] = ",\"value\":\"";
    static const char save_value[] = ",\"value\":null}";
    char expected[160];
    if (request || delivered == UINT32_MAX) __builtin_trap();
    int saving = delivered % 2;
    uint32_t at = saving ? append(expected, 0, save_prefix, sizeof(save_prefix) - 1)
                         : append(expected, 0, draft_prefix, sizeof(draft_prefix) - 1);
    at = append_number(expected, at, revision);
    at = append(expected, at, sequence_field, sizeof(sequence_field) - 1);
    at = append_number(expected, at, delivered + 1);
    if (saving) {
        at = append(expected, at, save_value, sizeof(save_value) - 1);
        if (length != at || !equal(input, expected, at)) __builtin_trap();
        save_title();
    } else {
        at = append(expected, at, draft_value, sizeof(draft_value) - 1);
        if (length < at || !equal(input, expected, at)) __builtin_trap();
        take_title(length, at);
    }
    ++delivered;
    return 0;
}

void mixer_guest_capability_ready_v1(void) {
    if (!request || poll(request, completion, sizeof(completion), &completion_size) != 0) return;
    request = 0;
    if (completion_size != sizeof(success) - 1 || !equal(completion, success, completion_size)) __builtin_trap();
    ++saves;
    ++revision;
    publish();
}
