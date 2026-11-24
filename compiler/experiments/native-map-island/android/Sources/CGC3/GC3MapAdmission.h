#ifndef GC3_MAP_ADMISSION_H
#define GC3_MAP_ADMISSION_H

#include <stddef.h>
#include <stdint.h>

#define GC3_MAX_MANIFEST 65536
#define GC3_MAX_PAYLOAD 4096

enum { GC3_ABOVE_DETAILS = 1, GC3_BELOW_DETAILS = 2 };
enum { GC3_STANDARD = 1, GC3_SATELLITE = 2 };

typedef struct {
    int32_t slot;
    int32_t style;
    double latitude;
    double longitude;
    int64_t node_generation;
    const char *node_id;
    const char *island_id;
    const char *installed_runtime;
    const char *installed_schema;
    const char *release_grant_schema;
    const char *release_id;
    const char *artifact_sha256;
    const char *signed_manifest_sha256;
    const char *payload_sha256;
    const char *root_sha256;
} GC3MapPlacement;

typedef void (*GC3Accept)(void *, const GC3MapPlacement *);
typedef void (*GC3Refuse)(void *, const char *);

// One synchronous callback. Values and strings are valid during that callback.
void gc3_map_admit(const uint8_t *manifest, size_t manifest_size,
                   const uint8_t *payload, size_t payload_size,
                   void *context, GC3Accept accept, GC3Refuse refuse);

#endif
