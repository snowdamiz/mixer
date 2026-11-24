#include "GC3MapAdmission.h"
#include <jni.h>

typedef struct {
    JNIEnv *env;
    jobject sink;
    jmethodID record;
    jstring refusal;
} Invocation;

static void reject(void *context, const char *code) {
    Invocation *call = context;
    call->refusal = (*call->env)->NewStringUTF(call->env, code);
}

static void accept(void *context, const GC3MapPlacement *placement) {
    Invocation *call = context;
    JNIEnv *env = call->env;
    const char *strings[] = {
        placement->node_id, placement->island_id, placement->installed_runtime,
        placement->installed_schema, placement->release_grant_schema, placement->release_id,
        placement->artifact_sha256, placement->signed_manifest_sha256, placement->payload_sha256,
        placement->root_sha256,
    };
    jvalue args[5 + sizeof(strings) / sizeof(*strings)] = {
        {.i = placement->slot}, {.i = placement->style}, {.d = placement->latitude},
        {.d = placement->longitude}, {.j = placement->node_generation},
    };
    for (size_t i = 0; i < sizeof(strings) / sizeof(*strings); ++i) {
        args[5 + i].l = (*env)->NewStringUTF(env, strings[i]);
        if (!args[5 + i].l) return;
    }
    (*env)->CallVoidMethodA(env, call->sink, call->record, args);
}

JNIEXPORT jstring JNICALL
Java_dev_mixer_gc3_NativeMap_admit(JNIEnv *env, jclass owner, jbyteArray manifest,
                                   jbyteArray payload, jobject sink) {
    (void)owner;
    const jsize manifest_size = (*env)->GetArrayLength(env, manifest);
    const jsize payload_size = (*env)->GetArrayLength(env, payload);
    if (manifest_size < 1 || manifest_size > GC3_MAX_MANIFEST)
        return (*env)->NewStringUTF(env, "v3.document.size");
    if (payload_size < 1 || payload_size > GC3_MAX_PAYLOAD)
        return (*env)->NewStringUTF(env, "placement.malformed");

    const jclass sink_class = (*env)->GetObjectClass(env, sink);
    const jmethodID record = (*env)->GetMethodID(env, sink_class, "record",
        "(IIDDJLjava/lang/String;Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;"
        "Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;"
        "Ljava/lang/String;Ljava/lang/String;)V");
    if (!record) return NULL;
    // Own the bytes passed into Swift. Also release JVM arrays before Swift
    // performs signature verification and before the result callback into Java.
    uint8_t manifest_bytes[GC3_MAX_MANIFEST];
    uint8_t payload_bytes[GC3_MAX_PAYLOAD];
    (*env)->GetByteArrayRegion(env, manifest, 0, manifest_size, (jbyte *)manifest_bytes);
    if ((*env)->ExceptionCheck(env)) return NULL;
    (*env)->GetByteArrayRegion(env, payload, 0, payload_size, (jbyte *)payload_bytes);
    if ((*env)->ExceptionCheck(env)) return NULL;

    Invocation call = {.env = env, .sink = sink, .record = record};
    gc3_map_admit(manifest_bytes, (size_t)manifest_size, payload_bytes, (size_t)payload_size,
                  &call, accept, reject);
    return call.refusal;
}
