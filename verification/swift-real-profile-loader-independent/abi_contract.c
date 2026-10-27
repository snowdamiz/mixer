#include <CommonCrypto/CommonDigest.h>
#include <crt_externs.h>
#include <mach-o/dyld.h>
#include <unistd.h>
#include <stdint.h>
#include <stddef.h>
#define SAME(value, type) _Generic((value), type: 1, default: 0)
_Static_assert(sizeof(CC_LONG) == 4, "CommonCrypto input length is 32 bits");
_Static_assert(CC_SHA256_DIGEST_LENGTH == 32, "SHA256 result extent");
_Static_assert(SAME(&CC_SHA256, unsigned char *(*)(const void *, uint32_t, unsigned char *)), "SHA256 ABI");
_Static_assert(SAME(&_NSGetArgc, int *(*)(void)), "argc ABI");
_Static_assert(SAME(&_NSGetArgv, char ***(*)(void)), "argv ABI");
_Static_assert(SAME(&_NSGetEnviron, char ***(*)(void)), "environment ABI");
_Static_assert(SAME(&_NSGetExecutablePath, int (*)(char *, uint32_t *)), "executable path ABI");
_Static_assert(SAME(&getcwd, char *(*)(char *, size_t)), "working directory ABI");
