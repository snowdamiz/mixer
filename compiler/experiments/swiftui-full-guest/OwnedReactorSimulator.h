#include <stddef.h>
#include <stdint.h>

void mixer_s2a_checkpoint(const char *stage, size_t length, uint64_t elapsedMicros);
_Noreturn void mixer_s2a_finish(int status);
void mixer_s2a_start_native(void);
