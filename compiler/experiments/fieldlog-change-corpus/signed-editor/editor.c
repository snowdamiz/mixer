#include <stdint.h>
#include <stddef.h>

#define IMPORT(name) __attribute__((import_module("mixer.capability.v1"), import_name(name)))
IMPORT("storage_put") int32_t storage_put(const char *, uint32_t, uint64_t *);
IMPORT("poll") int32_t poll(uint64_t, char *, uint32_t, uint32_t *);
extern const char editor_frame[];

enum phase { editing, saving, refused, saved, cancelled };
struct text { char encoded[1442]; uint32_t length; };
struct buffer { char *bytes; uint32_t length, capacity; };
static uint32_t header[8], revision = 1, sequence = 1;
static uint64_t token;
static enum phase phase;
static struct text title = {"\"\"", 2}, responsible = {"\"\"", 2};
static char events[4096], document[8192], detail[3072], arguments[4224], completion[1024];

static uint32_t length(const char *value) {
    uint32_t count = 0;
    while (value[count]) ++count;
    return count;
}
static void append(struct buffer *out, const char *bytes, uint32_t count) {
    if (count > out->capacity - out->length) __builtin_trap();
    for (uint32_t i = 0; i < count; ++i) out->bytes[out->length++] = bytes[i];
}
static void literal(struct buffer *out, const char *value) { append(out, value, length(value)); }
static void decimal(struct buffer *out, uint32_t value) {
    char digits[10];
    uint32_t count = 0;
    do {
        digits[count++] = '0' + value % 10;
        value /= 10;
    } while (value);
    while (count) append(out, digits + --count, 1);
}
static int take_bytes(const char **begin, const char *end, const char *value, uint32_t count) {
    if ((size_t)(end - *begin) < count) return 0;
    for (uint32_t i = 0; i < count; ++i) if ((*begin)[i] != value[i]) return 0;
    *begin += count;
    return 1;
}
static int take(const char **begin, const char *end, const char *value) {
    return take_bytes(begin, end, value, length(value));
}
static int number(const char **begin, const char *end, uint32_t expected) {
    char digits[11];
    struct buffer out = {digits, 0, sizeof digits - 1};
    decimal(&out, expected);
    digits[out.length] = 0;
    return take(begin, end, digits);
}

static void replace(struct buffer *out, const char **cursor, const char *end, const char *anchor,
                    const char *old_value, const char *new_value, uint32_t count) {
    uint32_t anchor_length = length(anchor);
    const char *match = *cursor;
    while (match < end) {
        const char *next = match;
        if (*match == *anchor && take_bytes(&next, end, anchor, anchor_length)) {
            append(out, *cursor, (uint32_t)(next - *cursor));
            if (!take(&next, end, old_value)) __builtin_trap();
            append(out, new_value, count);
            *cursor = next;
            return;
        }
        ++match;
    }
    __builtin_trap();
}
static int title_has_content(void) {
    // Match the single-byte whitespace and JSON escapes used for newlines.
    // The repository applies the full Unicode validation before writing.
    for (uint32_t i = 1; i + 1 < title.length; ++i) {
        char byte = title.encoded[i];
        if (byte == ' ') continue;
        if (byte == '\\' && (title.encoded[i+1] == 'n' || title.encoded[i+1] == 'r' ||
                             title.encoded[i+1] == 't')) {
            ++i;
            continue;
        }
        return 1;
    }
    return 0;
}
static void render(void) {
    struct buffer out = {document, 0, sizeof document};
    const char *cursor = editor_frame;
    const char *end = cursor + length(cursor);
    literal(&out, "{\"featureSchemaVersion\":3,\"document\":");
    if (revision == 1) {
        append(&out, cursor, (uint32_t)(end - cursor));
    } else {
        if (!take(&cursor, end, "{\"revision\":1")) __builtin_trap();
        literal(&out, "{\"revision\":");
        decimal(&out, revision);
        if (phase == saved || phase == cancelled) {
            literal(&out, ",\"root\":{\"actions\":[],\"children\":[],\"id\":\"task.result\","
                          "\"kind\":\"text\",\"properties\":{\"text\":");
            literal(&out, phase == saved ? "\"Task added\"" : "\"Task cancelled\"");
            literal(&out, "}},\"schemaVersion\":1}");
        } else {
            if (phase == saving) {
                replace(&out, &cursor, end, "\"disabled\":",
                        "false", "true", 4);
            }
            replace(&out, &cursor, end, "\"value\":", "\"\"", title.encoded, title.length);
            if (phase == saving) replace(&out, &cursor, end, "\"disabled\":", "false", "true", 4);
            replace(&out, &cursor, end, "\"value\":", "\"\"", responsible.encoded, responsible.length);
            if (phase == refused) {
                replace(&out, &cursor, end, "\"id\":\"task.fields\",\"kind\":\"section\","
                        "\"properties\":{\"title\":\"Task\"}},", "",
                        "{\"actions\":[],\"children\":[],\"id\":\"task.failure\",\"kind\":\"text\","
                        "\"properties\":{\"text\":\"Task could not be saved\"}},",
                        sizeof("{\"actions\":[],\"children\":[],\"id\":\"task.failure\",\"kind\":\"text\","
                               "\"properties\":{\"text\":\"Task could not be saved\"}},") - 1);
            }
            if (phase == saving) {
                replace(&out, &cursor, end, "\"disabled\":", "false", "true", 4);
                replace(&out, &cursor, end, "\"id\":\"task.save\",\"kind\":\"button\",\"properties\":{\"disabled\":true,\"label\":",
                        "\"Add\"", "\"Saving…\"", sizeof("\"Saving…\"") - 1);
            } else if (title_has_content()) {
                replace(&out, &cursor, end, "\"id\":\"task.save\",\"kind\":\"button\",\"properties\":{\"disabled\":",
                        "true", "false", 5);
            }
            append(&out, cursor, (uint32_t)(end - cursor));
        }
    }
    literal(&out, "}");
    header[3] = out.length;
}

static int read_text(struct text *value, const char *start, const char *end) {
    const char *cursor = start;
    if (!take(&cursor, end, "\"")) return 0;
    while (cursor < end) {
        unsigned char byte = *cursor++;
        if (byte == '"') {
            uint32_t count = (uint32_t)(cursor - start);
            if (!take(&cursor, end, "}") || cursor != end || count > sizeof value->encoded) return 0;
            for (uint32_t i = 0; i < count; ++i) value->encoded[i] = start[i];
            value->length = count;
            return 1;
        }
        if (byte < 32) return 0;
        if (byte == '\\') {
            // Only the host's checked scalar encoder can supply a value. Skip
            // its escape introducer so an escaped quote cannot end the token.
            if (cursor == end) return 0;
            ++cursor;
        }
    }
    return 0;
}
static void base64(struct buffer *out, struct buffer raw) {
    const char *alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    for (uint32_t i = 0; i < raw.length; i += 3) {
        uint32_t left = raw.length - i;
        uint32_t word = (uint32_t)(uint8_t)raw.bytes[i] << 16;
        if (left > 1) word |= (uint32_t)(uint8_t)raw.bytes[i+1] << 8;
        if (left > 2) word |= (uint8_t)raw.bytes[i+2];
        char group[4] = {alphabet[word >> 18], alphabet[(word >> 12) & 63],
                         left > 1 ? alphabet[(word >> 6) & 63] : '=',
                         left > 2 ? alphabet[word & 63] : '='};
        append(out, group, 4);
    }
}
static int begin_save(void) {
    struct buffer record = {detail, 0, sizeof detail};
    literal(&record, "{\"title\":");
    append(&record, title.encoded, title.length);
    literal(&record, ",\"responsible\":");
    append(&record, responsible.encoded, responsible.length);
    literal(&record, "}");
    struct buffer call = {arguments, 0, sizeof arguments};
    literal(&call, "{\"key\":\"new-task\",\"namespace\":\"fieldlog-editor\",\"valueBase64\":\"");
    base64(&call, record);
    literal(&call, "\"}");
    return storage_put(arguments, call.length, &token) == 0;
}

int32_t mixer_guest_ui_start_v1(void) {
    header[0] = 0x3155494d;
    header[1] = sizeof header;
    header[2] = (uint32_t)(uintptr_t)document;
    header[4] = (uint32_t)(uintptr_t)events;
    header[5] = sizeof events;
    render();
    return (int32_t)(uintptr_t)header;
}
int32_t mixer_guest_ui_event_v1(uint32_t count) {
    if ((phase != editing && phase != refused) || count > sizeof events ||
        revision >= UINT32_MAX - 1 || sequence == UINT32_MAX) return 1;
    const char *cursor = events, *end = events + count;
    enum { edit_title, edit_responsible, save, cancel } action;
    if (take(&cursor, end, "{\"actionID\":\"task.title.change\",\"event\":\"textChange\",\"nodeID\":\"task.title\""))
        action = edit_title;
    else if (take(&cursor, end, "{\"actionID\":\"task.responsible.change\",\"event\":\"textChange\",\"nodeID\":\"task.responsible\""))
        action = edit_responsible;
    else if (take(&cursor, end, "{\"actionID\":\"task.save\",\"event\":\"activate\",\"nodeID\":\"task.save\""))
        action = save;
    else if (take(&cursor, end, "{\"actionID\":\"task.cancel\",\"event\":\"activate\",\"nodeID\":\"task.cancel\""))
        action = cancel;
    else return 1;
    if (!take(&cursor, end, ",\"revision\":") || !number(&cursor, end, revision) ||
        !take(&cursor, end, ",\"schemaVersion\":3,\"sequence\":") || !number(&cursor, end, sequence) ||
        !take(&cursor, end, ",\"value\":")) return 1;
    if (action == edit_title || action == edit_responsible) {
        if (!read_text(action == edit_title ? &title : &responsible, cursor, end)) return 1;
        phase = editing;
    } else {
        if (!take(&cursor, end, "null}") || cursor != end) return 1;
        if (action == cancel) phase = cancelled;
        else {
            if (!title_has_content()) return 1;
            phase = begin_save() ? saving : refused;
        }
    }
    ++revision;
    ++sequence;
    render();
    return 0;
}
void mixer_guest_capability_ready_v1(void) {
    if (phase != saving) __builtin_trap();
    uint32_t count = 0;
    if (poll(token, completion, sizeof completion, &count) != 0 || count > sizeof completion)
        __builtin_trap();
    const char *cursor = completion, *end = completion + count;
    phase = take(&cursor, end, "{\"abi\":1,\"capability\":\"storage.keyValue.v1\",\"operation\":\"put\","
                 "\"outcome\":{\"kind\":\"success\",\"value\":{\"committed\":true}},"
                 "\"schemaHash\":\"4a311222c978ddd0982e8dfbcf3d4864b856a80bcc1efb3b725adede7f8e22fd\"}")
            && cursor == end ? saved : refused;
    ++revision;
    render();
}
