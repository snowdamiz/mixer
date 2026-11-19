#include "mixer_vm_guest_ui_deferred.h"
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static MixerVmReport report;
static uint64_t handle;
static uint32_t header_offset;

static void require(bool condition, const char *step) {
    if (condition) return;
    fprintf(stderr, "%s: status=%u code=%s message=%s\n", step, report.status, report.code, report.message);
    exit(1);
}

static void invoke(const char *name, const MixerVmValue *value) {
    require(mixer_vm_capability_session_invoke_v1(handle, (const uint8_t *)name,
            strlen(name), value, value != NULL, &report) == 0, name);
    require(report.value_type == 1 && report.value == 0, name);
}

static void header(uint32_t words[8]) {
    require(mixer_vm_capability_session_read_v1(handle, header_offset,
            (uint8_t *)words, 32, &report) == 0, "read header");
    require(words[0] == 0x3155494d && words[1] == 32 && words[5] == 4096, "header ABI");
}

static void expect_frame(const char *status, const char *action) {
    uint32_t words[8];
    header(words);
    char document[2048];
    require(words[3] > 0 && words[3] < sizeof(document), "bounded document");
    require(mixer_vm_capability_session_read_v1(handle, words[2],
            (uint8_t *)document, words[3], &report) == 0, "read frame");
    document[words[3]] = 0;
    require(strstr(document, "\"id\":\"fieldlog-task\"") && strstr(document, "\"id\":\"task.action\"")
            && strstr(document, status) && strstr(document, action), "frame readback");
    puts(document);
}

static void event(unsigned revision, unsigned sequence) {
    uint32_t words[8];
    header(words);
    char bytes[180];
    int length = snprintf(bytes, sizeof(bytes), "{\"actionID\":\"task.action\",\"event\":\"activate\","
            "\"nodeID\":\"toggle\",\"revision\":%u,\"schemaVersion\":1,\"sequence\":%u,\"value\":null}",
            revision, sequence);
    require(length > 0 && (size_t)length < sizeof(bytes), "event encoding");
    require(mixer_vm_capability_session_write_v1(handle, words[4],
            (const uint8_t *)bytes, (size_t)length, &report) == 0, "write event");
    MixerVmValue arg = {1, 0, length};
    invoke("mixer_guest_ui_event_v1", &arg);
}

static void answer(uint32_t operation, const char *arguments, const char *completion) {
    MixerVmCapabilityMessageV1 message;
    MixerVmCapabilityResultV1 result;
    uint8_t bytes[192];
    require(mixer_vm_capability_take_v1(handle, &message, bytes, sizeof(bytes), &report) == 0, "take");
    require(message.kind == 1 && message.operation == operation &&
            message.payload_length == strlen(arguments) &&
            memcmp(bytes, arguments, message.payload_length) == 0, "exact scoped request");
    require(mixer_vm_capability_post_v1(handle, message.token, operation,
            (const uint8_t *)completion, strlen(completion), &result, &report) == 0 &&
            result.kind == 0, "post");
    require(mixer_vm_capability_ack_exit_v1(handle, message.token, operation,
            &result, &report) == 0 && result.kind == 0, "ack");
    uint32_t did_invoke = 0;
    require(mixer_vm_capability_session_wake_v1(handle, &did_invoke, &report) == 0 &&
            did_invoke == 1, "wake");
}

static const char get[] = "{\"key\":\"selected-task\",\"namespace\":\"fieldlog-task-v1\"}";
#define GET(value) "{\"abi\":1,\"capability\":\"storage.keyValue.v1\",\"operation\":\"get\"," \
    "\"outcome\":{\"kind\":\"success\",\"value\":{\"found\":true,\"valueBase64\":\"" value "\"}}," \
    "\"schemaHash\":\"4a311222c978ddd0982e8dfbcf3d4864b856a80bcc1efb3b725adede7f8e22fd\"}"

int main(int argc, char **argv) {
    if (argc != 3 || (strcmp(argv[2], "old") && strcmp(argv[2], "new"))) return 2;
    FILE *file = fopen(argv[1], "rb");
    if (!file) return 2;
    uint8_t wasm[8193];
    size_t bytes = fread(wasm, 1, sizeof(wasm), file);
    bool failed = ferror(file);
    if (fclose(file) || failed || !bytes || bytes >= sizeof(wasm)) return 2;
    const uint8_t startup[] = "mixer_guest_ui_start_v1";
    MixerVmLimits vm = {sizeof(vm), 1, 1000000, 1, 4096, 64, 1024};
    MixerVmCapabilityLimitsV1 caps = {sizeof(caps), 1, 8, 30000, 50, 0, 8388608};
    require(mixer_vm_capability_guest_ui_validate_deferred_v1(wasm, bytes, &vm, &caps, &report) == 0, "validate");
    require(mixer_vm_capability_session_create_v1(wasm, bytes, startup, sizeof(startup)-1,
            &vm, &caps, &handle, &report) == 0, "create");
    require(mixer_vm_capability_session_startup_v1(handle, &report) == 0 && report.value_type == 1 &&
            report.value > 0, "startup");
    header_offset = (uint32_t)report.value;
    uint32_t words[8];
    header(words);
    require(!words[2] && !words[3] && !report.host_calls_used, "deferred first frame");
    require(mixer_vm_capability_session_enable_v1(handle, &report) == 0, "enable");
    invoke("mixer_guest_ui_hydrate_v1", NULL);
    answer(2, get, GET("AAAAAAAAACoA")); // revision 42, open
    expect_frame("\"text\":\"Open\"", "\"label\":\"Complete task\"");
    event(1, 1);
    if (!strcmp(argv[2], "new")) {
        MixerVmCapabilityMessageV1 message;
        uint8_t bytes[192];
        require(mixer_vm_capability_take_v1(handle, &message, bytes, sizeof(bytes), &report) == 0 &&
                message.kind == 0, "review has no write");
        expect_frame("\"text\":\"Review required\"", "\"label\":\"Confirm completion\"");
        event(2, 2);
    }
    answer(3, "{\"key\":\"selected-task\",\"namespace\":\"fieldlog-task-v1\",\"valueBase64\":\"AAAAAAAAACoB\"}",
            "{\"abi\":1,\"capability\":\"storage.keyValue.v1\",\"operation\":\"put\","
            "\"outcome\":{\"kind\":\"success\",\"value\":{\"committed\":true}},"
            "\"schemaHash\":\"4a311222c978ddd0982e8dfbcf3d4864b856a80bcc1efb3b725adede7f8e22fd\"}");
    answer(2, get, GET("AAAAAAAAACsB")); // revision 43, complete
    expect_frame("\"text\":\"Completed\"", "\"label\":\"Reopen task\"");
    require(mixer_vm_capability_session_close_v1(handle, &report) == 0, "close");
    puts("deferred hydration, action, capability acknowledgement, completion readback, and close passed");
}
