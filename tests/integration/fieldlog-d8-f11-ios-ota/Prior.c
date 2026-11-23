#include <stdint.h>

static const char frame[] =
    "{\"schemaVersion\":1,\"revision\":1,\"root\":{\"id\":\"entry-editor\",\"kind\":\"vStack\","
    "\"properties\":{},\"actions\":[],\"children\":[{\"id\":\"f11-prior\",\"kind\":\"text\","
    "\"properties\":{\"text\":\"Read-only Note release\"},\"actions\":[],\"children\":[]}]}}";
static struct {
    uint32_t magic, header_size, document, document_size, event, event_capacity, reserved[2];
    char event_bytes[4096];
} ui;

uint32_t mixer_guest_ui_start_v1(void) {
    ui.magic = 0x3155494d;
    ui.header_size = 32;
    ui.event = (uint32_t)(uintptr_t)ui.event_bytes;
    ui.event_capacity = sizeof(ui.event_bytes);
    ui.document = (uint32_t)(uintptr_t)frame;
    ui.document_size = sizeof(frame) - 1;
    return (uint32_t)(uintptr_t)&ui;
}

uint32_t mixer_guest_ui_hydrate_v1(void) { return 1; }

void mixer_guest_capability_ready_v1(void) {}

uint32_t mixer_guest_ui_event_v1(uint32_t length) {
    (void)length;
    return 1;
}
