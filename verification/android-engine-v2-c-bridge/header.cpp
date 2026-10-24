#include "mixer_android_v2.h"
#include <type_traits>
static_assert(std::is_same_v<decltype(&mixer_android_commit_v2), int32_t (*)(uint64_t, uint64_t)>);
static_assert(std::is_same_v<decltype(&mixer_android_abort_v2), int32_t (*)(uint64_t, uint64_t)>);
int main() {
    return mixer_android_commit_v2(0, 0) == MIXER_ANDROID_V2_CLOSED &&
        mixer_android_abort_v2(0, 0) == MIXER_ANDROID_V2_CLOSED ? 0 : 1;
}
