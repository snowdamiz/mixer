#include "DraftPressTrace.h"
#include <assert.h>
#include <pthread.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>

static char line[256];
static unsigned lines;
int __android_log_print(int level, const char *tag, const char *format, ...) {
    assert(level == 4 && strcmp(tag, "FieldLogDraftPress") == 0);
    va_list arguments;
    va_start(arguments, format);
    int count = vsnprintf(line, sizeof line, format, arguments);
    va_end(arguments);
    assert(count > 0 && (size_t)count < sizeof line);
    ++lines;
    return count;
}

static void *other_thread(void *ctx) {
    assert(fieldlog_press_current() == 0);
    assert(fieldlog_press_bind(8) == 0);
    assert(fieldlog_press_current() == 8);
    return ctx;
}

int main(void) {
    unsigned char live[17] = {0};
    assert(fieldlog_press_scope(&live[0], 0) == 0);
    for (unsigned i = 0; i < 16; ++i) {
        assert(fieldlog_press_scope(&live[i], 1) == i + 1);
        assert(fieldlog_press_scope(&live[i], 0) == i + 1);
    }
    assert(fieldlog_press_scope(&live[16], 1) == 0);
    fieldlog_press_unset_scope(&live[0]);
    assert(fieldlog_press_scope(&live[0], 0) == 0);
    assert(fieldlog_press_scope(&live[16], 1) == 17);

    assert(fieldlog_press_bind(7) == 0);
    pthread_t thread;
    assert(pthread_create(&thread, NULL, other_thread, NULL) == 0);
    assert(pthread_join(thread, NULL) == 0);
    assert(fieldlog_press_current() == 7);
    assert(fieldlog_press_bind(0) == 7 && fieldlog_press_current() == 0);

    fieldlog_press_trace(FIELDLOG_TRACE_OFFER, 17, 7, 1, 2, 0, 0, 0);
    assert(lines == 1 && strstr(line, " stage=offer scope=17 press=7 event=1 rev=2 code=0 elapsed_ns=0 detail=0"));
    fieldlog_press_trace(FIELDLOG_TRACE_GUEST, 17, 0, 1, 2, 4, 12, 1);
    assert(lines == 2 && strstr(line, " stage=guest scope=17 press=0 event=1 rev=2 code=4 elapsed_ns=12 detail=1"));
    fieldlog_press_trace(FIELDLOG_TRACE_FRAME, 0, 0, 0, 1, 0, 0, 0);
    fieldlog_press_trace(0, 17, 7, 0, 0, 0, 0, 0);
    assert(lines == 2);
    puts("PASS trace scope capacity and retirement, press TLS isolation, scalar log format and suppression");
}
