#include <stddef.h>
#include <stdint.h>

void mixer_s2b_checkpoint(const char *stage, size_t length, uint64_t elapsed_micros);
_Noreturn void mixer_s2b_finish(int status);
void mixer_s2b_start_native(void);
